"""Event-mode integration tests (#8999 — TEST-PLAN-8694.md §4).

Exercises ``event_poll.py`` against a minimal in-process HTTP server
that hosts the real ``EventStream`` from ``harness.py``. The full
harness app is intentionally avoided — its lifespan startup writes
port files into every agent clone and runs other side-effecting
setup that is unsafe during tests. Hosting just ``EventStream``
behind a thin handler gives faithful end-to-end cursor behavior with
zero filesystem mutation outside the isolated test role directory.

Scenarios covered this PR:

- §4.10 IT-CursorLongLag — long cursor lag, skim-then-advance, no
  silently-dropped events.
- §4.6 Transition-on-handoff — `status-transition` events emitted by
  `tracker.transition` surface to the receiving role's targeted feed.
- §4.7 (DM exception, harness layer) — `tracker-comment` events are
  filtered out of `/events/for/dm` so a bare comment cannot wake DM
  during a PR-merge wait.

Scenarios deliberately deferred (see issue #8999 Discussion):

- §4.4 IT-EvictionGap — blocked on eviction-signal infrastructure
  (separate task; see precondition issue).
- §4.7 (Non-DM half) — the rule "agent does NOT wake on bare comment"
  is enforced at the AGENT layer (Monitor subscription + handler),
  not the harness. Provable only by spawning a real event-mode agent;
  deferred to PR3 (agent-subprocess scenarios).
- §4.1/4.2/4.3/4.5/4.8/4.8b — future PRs per body phasing.
"""

import json
import shutil
import socket
import subprocess
import sys
import threading
import time
import unittest
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
SQUID_DIR = REPO_ROOT / ".squidsquad"

# Isolated role name — keeps live agent working-state files untouched.
TEST_ROLE = "test-event-mode-e2e"

HARNESS_AVAILABLE = False
EventStream = None
# Load harness.py under a unique module name. A direct `from harness import
# EventStream` collides in the full test-suite run with
# `tests/integration/harness.py` (a test-cleanup utility), which gets imported
# first and binds `harness` in sys.modules — so the next `import harness`
# returns the cleanup module, hiding EventStream and skipping every test in
# this file. Loading via importlib under a unique name sidesteps the cache.
try:
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "_harness_for_event_mode_e2e", SCRIPTS / "harness.py"
    )
    if _spec and _spec.loader:
        _harness_mod = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_harness_mod)
        EventStream = _harness_mod.EventStream
        HARNESS_AVAILABLE = True
except Exception as _e:  # pragma: no cover — surface, don't hide
    print(
        f"[test_event_mode_e2e] harness import failed: "
        f"{type(_e).__name__}: {_e}",
        file=sys.stderr,
    )


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_handler(stream, reacts_to=None):
    """Build a request handler bound to a specific EventStream instance.

    ``reacts_to`` is an optional ``{role: set(event_type)}`` map used by
    ``GET /events/for/{role}`` to mirror the harness's role-targeted
    filter logic. Tests inject a fixed map so coverage does not depend
    on the live ``config.md`` Event Reactions section.
    """
    reacts_to = reacts_to or {}

    class _Handler(BaseHTTPRequestHandler):
        # Silence default access-log spam.
        def log_message(self, fmt, *args):  # noqa: D401
            return

        def do_GET(self):  # noqa: N802 — required by BaseHTTPRequestHandler
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/status":
                self._reply_json({"status": "ok"})
                return
            if parsed.path == "/events":
                self._serve_events(parsed)
                return
            if parsed.path.startswith("/events/for/"):
                role = urllib.parse.unquote(
                    parsed.path[len("/events/for/"):]
                )
                self._serve_events_for_role(parsed, role)
                return
            self.send_error(404)

        def do_POST(self):  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/events":
                length = int(self.headers.get("Content-Length", "0") or "0")
                raw = self.rfile.read(length) if length else b""
                try:
                    event = json.loads(raw.decode("utf-8"))
                except (ValueError, UnicodeDecodeError):
                    self.send_error(400, "invalid JSON")
                    return
                # Mirror harness POST /events: trust caller-supplied id +
                # timestamp; this is exactly what event_bus.emit() sends.
                stream.append(event)
                self._reply_json({"status": "ok", "id": event.get("id")})
                return
            self.send_error(404)

        # --- shared helpers ---

        def _serve_events(self, parsed):
            qs = urllib.parse.parse_qs(parsed.query)
            since = qs.get("since", [None])[0]
            role = qs.get("role", [None])[0]
            try:
                limit = int(qs.get("limit", ["100"])[0])
            except ValueError:
                limit = 100
            # Match harness behavior: over-fetch by *3, then post-filter,
            # then trim to limit.
            eviction = None
            if since:
                events, eviction = stream.get_since_with_eviction(
                    since, limit=limit * 3
                )
            else:
                events = stream.get_recent(limit * 3)
            if role:
                events = [e for e in events if e.get("role") == role]
            # Mirror harness GET /events slicing: oldest-first when
            # `since` is set (skim-then-advance), newest-first otherwise.
            if since:
                events = events[:limit] if len(events) > limit else events
            else:
                events = events[-limit:] if len(events) > limit else events
            response = {"events": events, "total": len(stream)}
            if eviction is not None:
                # Eviction signal (#9331) — surface the same three keys
                # production /events does so event_poll.py exercises
                # its detection path end-to-end.
                response["evicted"] = True
                response["oldest_id"] = eviction["oldest_id"]
                response["evicted_count_hint"] = eviction["evicted_count_hint"]
            self._reply_json(response)

        def _serve_events_for_role(self, parsed, role):
            qs = urllib.parse.parse_qs(parsed.query)
            since = qs.get("since", [None])[0]
            try:
                limit = int(qs.get("limit", ["50"])[0])
            except ValueError:
                limit = 50

            eviction = None
            if since:
                events, eviction = stream.get_since_with_eviction(
                    since, limit=limit * 3
                )
            else:
                events = stream.get_recent(limit * 3)

            relevant = reacts_to.get(role, set())
            filtered = []
            for e in events:
                target = e.get("payload", {}).get("target_alias", "")
                etype = e.get("event_type", "")
                if target == role:
                    filtered.append(e)
                elif relevant and etype in relevant:
                    filtered.append(e)

            if since:
                filtered = filtered[:limit] if len(filtered) > limit else filtered
            else:
                filtered = filtered[-limit:] if len(filtered) > limit else filtered

            # Mirror harness `/events/for/{role}` shape: `total` is the
            # post-filter count there (harness.py:1391), unlike `/events`
            # which returns the global stream size.
            response = {"events": filtered, "total": len(filtered)}
            if eviction is not None:
                response["evicted"] = True
                response["oldest_id"] = eviction["oldest_id"]
                response["evicted_count_hint"] = eviction["evicted_count_hint"]
            self._reply_json(response)

        def _reply_json(self, body):
            payload = json.dumps(body).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return _Handler


@unittest.skipUnless(HARNESS_AVAILABLE, "harness module not importable")
class EventModeE2ETestBase(unittest.TestCase):
    """Shared fixture: in-process EventStream server + isolated role."""

    _port: int
    _server: ThreadingHTTPServer
    _thread: threading.Thread
    _stream: "EventStream"
    _test_role_dir: Path
    _port_file: Path
    _squid_tmpdir: str
    _squid_dir: Path

    # Reacts-to fixture for the role-targeted /events/for/{role} endpoint.
    # Subclasses exercising role filtering override this to lock in a
    # known config independent of the live config.md section.
    REACTS_TO: dict = {}

    @classmethod
    def setUpClass(cls):
        # #10265: route this test's port file and per-role state to an
        # isolated SQUIDSQUAD_DIR so a tearDown crash, KeyboardInterrupt,
        # or restored-backup race can never leave the LIVE
        # `.squidsquad/.harness-port` pointing at a test-only random
        # port. event_poll.py (the subprocess under test) was updated
        # in lockstep to honor SQUIDSQUAD_DIR.
        #
        # Snapshot the live file's mtime BEFORE any test setup so the
        # isolation-guard test can assert the live file was never
        # touched, without relying on the test's random port being
        # different from the live port (a coincidence-prone check).
        import tempfile
        live_port_file = REPO_ROOT / ".squidsquad" / ".harness-port"
        cls._live_port_mtime_before_setup = (
            live_port_file.stat().st_mtime_ns if live_port_file.exists()
            else None
        )

        cls._squid_tmpdir = tempfile.mkdtemp(prefix="sq-e2e-")
        # If any step below raises, unittest does NOT call tearDownClass —
        # wrap the rest of setup so a failed mid-setup still cleans up.
        try:
            cls._squid_dir = Path(cls._squid_tmpdir)
            cls._port_file = cls._squid_dir / ".harness-port"

            cls._test_role_dir = cls._squid_dir / TEST_ROLE
            cls._test_role_dir.mkdir(parents=True, exist_ok=True)

            cls._stream = EventStream(maxlen=1000)
            cls._port = _find_free_port()
            handler_cls = _make_handler(cls._stream, reacts_to=cls.REACTS_TO)
            cls._server = ThreadingHTTPServer(("127.0.0.1", cls._port), handler_cls)
            cls._thread = threading.Thread(
                target=cls._server.serve_forever, daemon=True,
                name="test-event-stream-http",
            )
            cls._thread.start()

            # event_poll.py discovers the server via this file.
            cls._port_file.write_text(str(cls._port), encoding="utf-8")
        except BaseException:
            shutil.rmtree(cls._squid_tmpdir, ignore_errors=True)
            raise

    @classmethod
    def tearDownClass(cls):
        cls._server.shutdown()
        cls._server.server_close()
        cls._thread.join(timeout=5)

        # #10265: rmtree the isolated SQUIDSQUAD_DIR — no live file to
        # restore, no backup race window where a crashed test leaves
        # a stale port in the live discovery file.
        shutil.rmtree(cls._squid_tmpdir, ignore_errors=True)

    def setUp(self):
        with self._stream._lock:
            self._stream._events.clear()

        # Model-B (#11329): the cursor is harness-owned in .event-state.json;
        # working-state.md carries no cursor line. event_poll never reads or
        # writes it.
        ws = self._test_role_dir / "working-state.md"
        ws.write_text(
            "# Working State\n\n- **Task**: none\n",
            encoding="utf-8",
        )

    # --- helpers ---

    def _seed_event(self, eid: str, etype: str = "status-transition",
                    role: str = TEST_ROLE) -> dict:
        ev = {
            "id": eid,
            "event_type": etype,
            "role": role,
            "timestamp": time.time(),
            "payload": {},
        }
        self._stream.append(ev)
        return ev

    def _run_event_poll(self, role: str = TEST_ROLE,
                        since: str | None = None,
                        limit: int | None = None) -> subprocess.CompletedProcess:
        cmd = [sys.executable, str(SCRIPTS / "event_poll.py"), role]
        if since is not None:
            cmd += ["--since", since]
        if limit is not None:
            cmd += ["--limit", str(limit)]
        # #10265: route the subprocess to the isolated test SQUIDSQUAD_DIR so
        # event_poll.py reads our port file (not the live one) and writes its
        # working-state under our test role dir.
        import os
        env = os.environ.copy()
        env["SQUIDSQUAD_DIR"] = str(self._squid_dir)
        return subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(REPO_ROOT), timeout=20, env=env,
        )

    def _agent_get(self, since: str | None = None, limit: int = 50) -> dict:
        """Simulate the agent's model-B read path: GET /events/for/{role}.

        In model B the AGENT (not event_poll) walks events past its cursor
        and acks each. The skim-then-advance / oldest-first / eviction
        invariants are properties of this harness endpoint, so we exercise
        it directly. Returns the parsed response dict
        (``events`` + optional ``evicted``/``oldest_id``/...).
        """
        params = {"limit": limit}
        if since is not None:
            params["since"] = since
        url = (
            f"http://127.0.0.1:{self._port}/events/for/"
            f"{urllib.parse.quote(TEST_ROLE)}?{urllib.parse.urlencode(params)}"
        )
        with urllib.request.urlopen(url, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))


class TestLiveHarnessPortNotTouched(EventModeE2ETestBase):
    """#10265: this test class must NOT modify the live
    `.squidsquad/.harness-port` file. Prior to #10265 the e2e test
    base wrote its random server port directly to the live file,
    relying on a tearDownClass restore — a teardown crash or
    KeyboardInterrupt would leak the test port into the live
    discovery surface and other SquidSquad processes (DM cycles,
    statusline, event poll from agents) would mis-route. Now the
    test uses an isolated SQUIDSQUAD_DIR + event_poll.py honors
    that env var, so the live file is untouched."""

    def test_live_squidsquad_harness_port_untouched(self):
        live_port = REPO_ROOT / ".squidsquad" / ".harness-port"
        if self._live_port_mtime_before_setup is None:
            self.skipTest("no live .harness-port to guard against")
        # Assert the live file's mtime is unchanged since before
        # setUpClass. This catches the clobber without false-positives
        # on the rare port collision between _find_free_port() and the
        # live harness's bound port (which the value-based check would
        # have flagged as "isolation broken").
        if not live_port.exists():
            self.fail(
                "Live .squidsquad/.harness-port existed before setUpClass "
                "but is gone now — the test deleted it (a stronger "
                "clobber than the value-mismatch case). Root cause #10265."
            )
        live_mtime_now = live_port.stat().st_mtime_ns
        self.assertEqual(
            self._live_port_mtime_before_setup, live_mtime_now,
            msg=(
                "Live .squidsquad/.harness-port mtime changed during the "
                "e2e fixture lifetime. This means SQUIDSQUAD_DIR isolation "
                "is broken: setUpClass touched the live discovery file "
                "and any concurrent SquidSquad process reading it will "
                "route to a dead test server. Root cause #10265."
            ),
        )

    def test_test_port_file_is_in_isolated_tmpdir(self):
        """The test's own port file must live under the isolated
        SQUIDSQUAD_DIR, NOT under the live `.squidsquad/`."""
        self.assertEqual(
            self._port_file.parent.resolve(),
            self._squid_dir.resolve(),
            msg="test port file must be inside the isolated SQUIDSQUAD_DIR",
        )
        live_squid = (REPO_ROOT / ".squidsquad").resolve()
        self.assertNotEqual(
            self._port_file.parent.resolve(), live_squid,
            msg="test port file must NOT be under the live .squidsquad/",
        )


class TestCursorLongLag(EventModeE2ETestBase):
    """§4.10 IT-CursorLongLag (model B, #11329).

    The skim-then-advance / oldest-first invariant is a property of the
    harness ``GET /events/for/{role}?since=cursor`` endpoint that the AGENT
    walks (event_poll no longer emits events or owns the cursor). We exercise
    that endpoint directly via ``_agent_get`` and, separately, assert that
    event_poll fires exactly one NUDGE when work is pending:

    - Events surface chronologically from the cursor forward, oldest first.
    - A small ``limit`` returns the OLDEST window — never a jump-to-latest.
    - Successive GETs (agent acking forward) cumulatively catch up to head.
    """

    # The agent's /events/for path filters by reacts-to; a real role reacts
    # to status-transition, so mirror that for the isolated test role.
    REACTS_TO = {TEST_ROLE: {"status-transition"}}

    def test_single_get_within_limit(self):
        """One GET catches the agent up when lag fits in `limit`."""
        anchor = self._seed_event("anchor-id")
        seeded_ids = [f"e{i:03d}" for i in range(50)]
        for eid in seeded_ids:
            self._seed_event(eid)

        resp = self._agent_get(since=anchor["id"], limit=100)
        emitted_ids = [e["id"] for e in resp["events"]]
        # Events surface in chronological order from the cursor forward;
        # none are silently dropped.
        self.assertEqual(emitted_ids, seeded_ids)

    def test_skim_then_advance_does_not_jump_to_latest(self):
        """Long lag exceeding `limit` is skimmed across successive GETs.

        Critical assertion: oldest events after the cursor are returned
        first — the agent never jumps to the latest event and silently
        drops older ones.
        """
        anchor = self._seed_event("anchor-id")
        seeded_ids = [f"e{i:03d}" for i in range(60)]
        for eid in seeded_ids:
            self._seed_event(eid)

        # First GET with small limit: must surface the OLDEST `limit`
        # events after the cursor, not the newest.
        resp1 = self._agent_get(since=anchor["id"], limit=10)
        first_batch = [e["id"] for e in resp1["events"]]
        self.assertEqual(
            first_batch, seeded_ids[:10],
            msg="agent jumped to latest — oldest events silently dropped",
        )

        # The agent acks forward to the last id it processed; the next GET
        # uses that as `since` and surfaces the remainder oldest-first.
        resp2 = self._agent_get(since=seeded_ids[9], limit=100)
        second_batch = [e["id"] for e in resp2["events"]]
        self.assertEqual(second_batch, seeded_ids[10:])

    def test_event_poll_nudges_when_work_pending(self):
        """event_poll's model-B job: emit a single NUDGE (no payload) when
        events exist past its high-water-mark, and exit 0."""
        anchor = self._seed_event("anchor-id")
        for eid in [f"e{i:03d}" for i in range(5)]:
            self._seed_event(eid)

        result = self._run_event_poll(since=anchor["id"], limit=100)
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        self.assertEqual(
            lines, ["NUDGE"],
            msg="event_poll must emit exactly one bare NUDGE — never event "
                f"payloads. stdout={result.stdout!r}",
        )

    def test_cursor_at_head_returns_empty(self):
        """Cursor already at head: GET returns no events; event_poll emits
        no NUDGE and exits 1 (single-shot, nothing pending)."""
        head = self._seed_event("only-event")

        resp = self._agent_get(since=head["id"], limit=50)
        self.assertEqual(resp["events"], [])

        result = self._run_event_poll(since=head["id"], limit=50)
        # event_poll exits 1 when no events found (single-shot mode).
        self.assertEqual(result.returncode, 1, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "")


# Reacts-to fixture mirroring the production contract at the time of
# writing. Locked in tests so they don't break if config.md is edited
# unrelated to this behavior. Smoke-checked against config.md in
# TestReactsToFixtureMatchesConfig below.
_REACTS_TO_FIXTURE = {
    "dm":    {"pr-merged", "status-transition"},
    "pm":    {"agent-health", "pr-create", "pr-merged", "status-transition",
              "tracker-comment", "verification-failed", "verification-passed"},
    "qa":    {"agent-health", "git-commit", "pr-create", "pr-merged",
              "status-transition"},
    "skill": {"pr-merged", "status-transition", "tracker-comment",
              "verification-failed", "verification-passed"},
}


def _emit_event(port: int, event: dict) -> None:
    """POST an event to the test harness — what `event_bus.emit` does."""
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/events",
        data=json.dumps(event).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        resp.read()


def _fetch_events_for_role(port: int, role: str,
                           since: str | None = None,
                           limit: int = 50) -> list[dict]:
    """GET /events/for/{role}, returning the events list."""
    params = {"limit": limit}
    if since:
        params["since"] = since
    url = (
        f"http://127.0.0.1:{port}/events/for/"
        f"{urllib.parse.quote(role)}?{urllib.parse.urlencode(params)}"
    )
    with urllib.request.urlopen(url, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8")).get("events", [])


class TestTransitionOnHandoff(EventModeE2ETestBase):
    """§4.6 — Transition-on-handoff (status-transition routes by role).

    The handoff contract: when an agent transitions an issue (assigning
    work to a different role), the resulting ``status-transition`` event
    surfaces on the event stream and is observable by
    ``event_poll.py`` on the receiving role's targeted feed.

    These tests exercise the harness contract directly via
    ``POST /events`` — the exact call path ``event_bus.emit`` follows
    from ``tracker.transition`` (tracker.py:1008-1018).
    """

    REACTS_TO = _REACTS_TO_FIXTURE

    def _build_transition_event(self, eid: str, emit_role: str,
                                issue: str, from_status: str,
                                to_status: str) -> dict:
        return {
            "id": eid,
            "event_type": "status-transition",
            "role": emit_role,
            "timestamp": time.time(),
            "payload": {
                "issue_number": issue,
                "from": from_status,
                "to": to_status,
            },
        }

    def test_skill_to_qa_handoff_visible_via_target_feed(self):
        """skill transitions in-progress → pending-test; QA's feed sees it.

        Reproduces a routing handoff: skill marks #42 ready for QA. QA's
        ``event_poll.py --target`` must surface the transition so QA can
        pick the item up.
        """
        ev = self._build_transition_event(
            eid="ev-skill-handoff",
            emit_role="skill",
            issue="42",
            from_status="in-progress",
            to_status="pending-test",
        )
        _emit_event(self._port, ev)

        delivered = _fetch_events_for_role(self._port, "qa")
        self.assertEqual(
            [e["id"] for e in delivered], [ev["id"]],
            msg="QA's targeted feed did not receive the status-transition",
        )
        got = delivered[0]
        self.assertEqual(got["event_type"], "status-transition")
        self.assertEqual(got["payload"]["issue_number"], "42")
        self.assertEqual(got["payload"]["from"], "in-progress")
        self.assertEqual(got["payload"]["to"], "pending-test")

    def test_filter_is_by_consumer_reacts_to_not_emitter_role(self):
        """Filter is keyed on the consumer's reacts-to list, NOT on the
        event's emitting ``role`` field.

        Proof by contrast: emit one event of a type that EVERY role
        reacts to (status-transition), and another event of a type
        that ONLY some roles react to (tracker-comment). The first
        reaches everyone; the second reaches PM/skill but NOT DM/QA.
        If the filter were keyed on the emitter's role, this asymmetry
        would not exist — both events would either reach the role
        (because the emitter is the same) or not (because the consuming
        role differs from the emitting role).
        """
        # Both events emitted with role=pm — same emitter for both.
        broadcast = self._build_transition_event(
            eid="ev-broadcast",
            emit_role="pm",
            issue="7",
            from_status="planning",
            to_status="planned",
        )
        _emit_event(self._port, broadcast)

        comment_ev = {
            "id": "ev-comment-from-pm",
            "event_type": "tracker-comment",
            "role": "pm",
            "timestamp": time.time(),
            "payload": {"issue_number": "7", "commenter_role": "pm"},
        }
        _emit_event(self._port, comment_ev)

        for role in ("dm", "pm", "qa", "skill"):
            ids = [e["id"] for e in _fetch_events_for_role(self._port, role)]
            reacts = _REACTS_TO_FIXTURE[role]
            expected = []
            if "status-transition" in reacts:
                expected.append(broadcast["id"])
            if "tracker-comment" in reacts:
                expected.append(comment_ev["id"])
            self.assertEqual(
                ids, expected,
                msg=f"role={role} delivered={ids} expected={expected} "
                    f"(emitter='pm' in both cases — filter must key on "
                    f"the consuming role's reacts-to list, not on the "
                    f"event's emit role).",
            )


class TestCommentHandlingDMException(EventModeE2ETestBase):
    """§4.7 (DM-exception, harness layer) — comment events filtered for DM.

    The L1 contract (comment-handling.md): DM does NOT enter a sub-loop
    waiting on comments during a PR-merge wait. The harness-layer
    enforcement is that DM's ``reacts-to`` list excludes
    ``tracker-comment``, so a bare comment emitted onto the bus is
    never delivered via ``/events/for/dm``. End-of-task re-read happens
    via forge polling at task pickup — not via the event stream.

    The §4.7 Non-DM half ("agent does NOT wake on bare comment") is an
    AGENT-side rule enforced by the agent's Monitor handler, and is
    not testable at the harness layer without spawning a real agent
    subprocess. Deferred to PR3.
    """

    REACTS_TO = _REACTS_TO_FIXTURE

    def _emit_comment(self, eid: str, emit_role: str,
                      issue: str, mentioned: list[str] | None = None) -> dict:
        ev = {
            "id": eid,
            "event_type": "tracker-comment",
            "role": emit_role,
            "timestamp": time.time(),
            "payload": {
                "issue_number": issue,
                "commenter_role": emit_role,
                "comment_preview": "PM nudge: please pick up.",
                "mentioned_roles": mentioned or [],
            },
        }
        _emit_event(self._port, ev)
        return ev

    def test_bare_comment_not_delivered_to_dm(self):
        """tracker-comment events are filtered out of /events/for/dm."""
        self._emit_comment("ev-pm-comment", "pm", issue="200")

        delivered = _fetch_events_for_role(self._port, "dm")
        self.assertEqual(
            delivered, [],
            msg="DM received a tracker-comment event — sub-loop risk during "
                "PR-merge wait. The DM exception in comment-handling.md "
                "is broken at the harness filter layer.",
        )

    def test_bare_comment_delivered_to_pm_and_skill(self):
        """Positive control: PM and skill (which DO react to tracker-comment)
        receive the event. Prevents a regression where the comment event
        is dropped for everyone."""
        ev = self._emit_comment("ev-pm-comment-2", "pm", issue="201")

        for role in ("pm", "skill"):
            delivered = _fetch_events_for_role(self._port, role)
            self.assertEqual(
                [e["id"] for e in delivered], [ev["id"]],
                msg=f"role={role} did not receive tracker-comment "
                    f"despite reacts-to including it",
            )

        # Negative control: QA does not react to tracker-comment either.
        self.assertEqual(_fetch_events_for_role(self._port, "qa"), [])

    def test_status_transition_still_reaches_dm_during_comment_burst(self):
        """While a burst of bare comments is filtered out, a real status
        transition (e.g. PM bouncing pending-ship → in-progress on a
        merge-conflict) still reaches DM — the exception is comment-only.
        """
        for i in range(5):
            self._emit_comment(f"ev-c{i}", "pm", issue="300")

        transition = {
            "id": "ev-bounce-back",
            "event_type": "status-transition",
            "role": "pm",
            "timestamp": time.time(),
            "payload": {
                "issue_number": "300",
                "from": "pending-ship",
                "to": "in-progress",
            },
        }
        _emit_event(self._port, transition)

        delivered = _fetch_events_for_role(self._port, "dm")
        self.assertEqual(
            [e["id"] for e in delivered], ["ev-bounce-back"],
            msg="DM should receive the status-transition and only that; "
                "comment burst must remain filtered out.",
        )


class TestReactsToFixtureMatchesConfig(unittest.TestCase):
    """Smoke check: the fixture above tracks the live config.md contract.

    If this test fails, either the fixture is out of date (update it)
    or someone legitimately changed the Event Reactions section in
    config.md (review whether §4.6/§4.7 invariants still hold). The
    fixture exists so the routing tests don't silently change behavior
    when config.md is edited.
    """

    def test_fixture_matches_live_config(self):
        # Load config.py via importlib under a unique name to avoid
        # `sys.modules["config"]` collisions with other tests (or any
        # stdlib/3p module that happens to be named ``config``).
        try:
            import importlib.util as _ilu
            spec = _ilu.spec_from_file_location(
                "_config_for_event_mode_e2e", SCRIPTS / "config.py"
            )
            if not (spec and spec.loader):
                self.skipTest("config module spec not buildable")
            config_mod = _ilu.module_from_spec(spec)
            spec.loader.exec_module(config_mod)
            get_event_filters_for_role = config_mod.get_event_filters_for_role
        except Exception as e:
            self.skipTest(f"config module not importable: {e}")

        for role, expected in _REACTS_TO_FIXTURE.items():
            live = get_event_filters_for_role(role) or set()
            self.assertEqual(
                live, expected,
                msg=(
                    f"reacts-to drift for role={role!r}: live={sorted(live)} "
                    f"fixture={sorted(expected)}. Update _REACTS_TO_FIXTURE "
                    f"in this file and re-confirm the §4.6/§4.7 invariants."
                ),
            )


class TestEvictionGap(EventModeE2ETestBase):
    """§4.4 IT-EvictionGap (model B, #11329).

    When the agent's cursor predates the retained deque, the harness
    ``GET /events/for/{role}?since=<stale>`` response carries the eviction
    markers (``evicted``/``oldest_id``/``evicted_count_hint``) and the
    OLDEST retained events (skim-then-advance) — this is the agent's
    recovery surface. Separately, ``event_poll`` must NUDGE (so the agent
    wakes to recover) and log a single eviction diagnostic, but it does NOT
    emit events or advance any cursor (model B).

    Backed by #9331's eviction-signal infrastructure
    (``EventStream.get_since_with_eviction`` + the three response keys); the
    in-process server mirrors the production endpoint shape.
    """

    REACTS_TO = {TEST_ROLE: {"status-transition"}}

    def test_stale_cursor_get_surfaces_eviction_markers_oldest_first(self):
        """The agent's GET past a stale cursor returns eviction markers +
        the OLDEST retained events — never a jump-to-latest."""
        stale_cursor = "evicted-before-the-deque-ever-saw-it"
        # Fill the deque past maxlen=1000: e0000..e1199 emit, e0200..e1199
        # retained.
        seeded_ids = [f"e{i:04d}" for i in range(1200)]
        for eid in seeded_ids:
            self._seed_event(eid)
        retained_ids = seeded_ids[-1000:]

        resp = self._agent_get(since=stale_cursor, limit=8)
        self.assertTrue(resp.get("evicted"),
                        msg="stale cursor must flag evicted=True")
        self.assertEqual(
            resp["oldest_id"], retained_ids[0],
            msg="oldest_id must name the oldest retained event (safe "
                "re-anchor for the agent's ack-cursor recovery).",
        )
        self.assertGreater(resp.get("evicted_count_hint", 0), 0)
        emitted_ids = [e["id"] for e in resp["events"]]
        self.assertEqual(
            emitted_ids, retained_ids[:8],
            msg="agent recovery surface must be oldest-first — never a "
                "jump past the eviction window.",
        )

    def test_event_poll_nudges_and_logs_single_eviction(self):
        """event_poll model-B role on an eviction gap: one NUDGE, one
        eviction diagnostic naming the recovery anchor, exit 0 — no events,
        no cursor write."""
        stale_cursor = "evicted-before-the-deque-ever-saw-it"
        seeded_ids = [f"e{i:04d}" for i in range(1200)]
        for eid in seeded_ids:
            self._seed_event(eid)
        retained_ids = seeded_ids[-1000:]

        result = self._run_event_poll(since=stale_cursor, limit=8)
        self.assertEqual(
            result.returncode, 0,
            msg=f"event_poll exit={result.returncode}\n"
                f"stdout={result.stdout!r}\nstderr={result.stderr!r}",
        )
        lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
        self.assertEqual(
            lines, ["NUDGE"],
            msg="event_poll must emit exactly one bare NUDGE on eviction, "
                f"not event payloads. stdout={result.stdout!r}",
        )
        # New model-B diagnostic text: nudge-to-recover, not advance.
        self.assertIn(
            "[event_poll] EVICTION: cursor predates retained window — "
            f"nudging agent to recover past {retained_ids[0]},",
            result.stderr,
        )
        import re as _re
        m = _re.search(r"~(\d+) events evicted", result.stderr)
        self.assertIsNotNone(m, msg=f"stderr={result.stderr!r}")
        self.assertGreater(int(m.group(1)), 0)
        # Exactly one diagnostic — not one per event.
        self.assertEqual(result.stderr.count("EVICTION"), 1)

    def test_recovered_cursor_get_has_no_eviction(self):
        """Once the agent has acked forward into the retained window, its
        next GET surfaces the remainder oldest-first with no eviction."""
        seeded_ids = [f"e{i:04d}" for i in range(1100)]
        for eid in seeded_ids:
            self._seed_event(eid)
        retained_ids = seeded_ids[-1000:]

        # Agent recovered to the 5th retained id (post-eviction ack-walk).
        resp = self._agent_get(since=retained_ids[4], limit=2000)
        self.assertNotIn("evicted", resp,
                         msg="cursor inside the retained window — no "
                             "eviction marker expected.")
        self.assertEqual(
            [e["id"] for e in resp["events"]], retained_ids[5:],
            msg="remaining retained events must surface oldest-first.",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
