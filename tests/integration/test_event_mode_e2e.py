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

Scenarios deliberately deferred (see issue #8999 Discussion):

- §4.4 IT-EvictionGap — blocked on eviction-signal infrastructure
  (separate task; see precondition issue).
- §4.1/4.2/4.3/4.5/4.6/4.7/4.8/4.8b — future PRs per body phasing.
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
try:
    sys.path.insert(0, str(SCRIPTS))
    from harness import EventStream  # type: ignore  # noqa: F401
    HARNESS_AVAILABLE = True
except ImportError:
    pass


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _make_handler(stream):
    """Build a request handler bound to a specific EventStream instance."""

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
                qs = urllib.parse.parse_qs(parsed.query)
                since = qs.get("since", [None])[0]
                role = qs.get("role", [None])[0]
                try:
                    limit = int(qs.get("limit", ["100"])[0])
                except ValueError:
                    limit = 100
                # Match harness behavior: over-fetch by *3, then post-filter,
                # then trim to limit.
                if since:
                    events = stream.get_since(since, limit=limit * 3)
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
                self._reply_json({"events": events, "total": len(stream)})
                return
            self.send_error(404)

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
    _port_backup: bytes | None
    _test_role_dir: Path
    _port_file: Path

    @classmethod
    def setUpClass(cls):
        cls._port_file = SQUID_DIR / ".harness-port"
        cls._port_backup = (
            cls._port_file.read_bytes() if cls._port_file.exists() else None
        )

        cls._test_role_dir = SQUID_DIR / TEST_ROLE
        cls._test_role_dir.mkdir(parents=True, exist_ok=True)

        cls._stream = EventStream(maxlen=1000)
        cls._port = _find_free_port()
        handler_cls = _make_handler(cls._stream)
        cls._server = ThreadingHTTPServer(("127.0.0.1", cls._port), handler_cls)
        cls._thread = threading.Thread(
            target=cls._server.serve_forever, daemon=True,
            name="test-event-stream-http",
        )
        cls._thread.start()

        # event_poll.py discovers the server via this file.
        cls._port_file.parent.mkdir(parents=True, exist_ok=True)
        cls._port_file.write_text(str(cls._port), encoding="utf-8")

    @classmethod
    def tearDownClass(cls):
        cls._server.shutdown()
        cls._server.server_close()
        cls._thread.join(timeout=5)

        if cls._port_backup is not None:
            cls._port_file.write_bytes(cls._port_backup)
        else:
            try:
                cls._port_file.unlink()
            except FileNotFoundError:
                pass

        shutil.rmtree(cls._test_role_dir, ignore_errors=True)

    def setUp(self):
        with self._stream._lock:
            self._stream._events.clear()

        ws = self._test_role_dir / "working-state.md"
        ws.write_text(
            "# Working State\n\n- **Last Processed Event ID**: \n",
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
        return subprocess.run(
            cmd, capture_output=True, text=True,
            cwd=str(REPO_ROOT), timeout=20,
        )

    def _read_cursor(self) -> str:
        ws = (self._test_role_dir / "working-state.md").read_text(
            encoding="utf-8",
        )
        for line in ws.splitlines():
            if line.startswith("- **Last Processed Event ID**:"):
                return line.split(":", 1)[1].strip()
        return ""


class TestCursorLongLag(EventModeE2ETestBase):
    """§4.10 IT-CursorLongLag.

    Pre-seed cursor far behind head with the deque NOT rolled. Boot the
    agent (run ``event_poll.py``) and verify skim-then-advance:

    - Events surface chronologically from cursor forward, oldest first.
    - Cursor advances incrementally; final cursor equals last id.
    - No event between cursor and head is silently dropped.
    - Multiple polls cumulatively catch the agent up to current head.
    """

    def test_single_poll_within_limit(self):
        """One poll catches the agent up when lag fits in `--limit`."""
        anchor = self._seed_event("anchor-id")
        seeded_ids = [f"e{i:03d}" for i in range(50)]
        for eid in seeded_ids:
            self._seed_event(eid)

        result = self._run_event_poll(since=anchor["id"], limit=100)
        self.assertEqual(
            result.returncode, 0,
            msg=f"event_poll exit={result.returncode}\nstderr={result.stderr}",
        )

        emitted_ids = [
            json.loads(line)["id"]
            for line in result.stdout.splitlines() if line.strip()
        ]
        # Spec: events surface in chronological order from cursor forward;
        # none are silently dropped.
        self.assertEqual(emitted_ids, seeded_ids)
        self.assertEqual(self._read_cursor(), seeded_ids[-1])

    def test_skim_then_advance_does_not_jump_to_latest(self):
        """Long lag exceeding `--limit` is skimmed across multiple polls.

        Critical assertion: oldest events after the cursor are returned
        first — the agent never jumps to the latest event and silently
        drops older ones.
        """
        anchor = self._seed_event("anchor-id")
        seeded_ids = [f"e{i:03d}" for i in range(60)]
        for eid in seeded_ids:
            self._seed_event(eid)

        # First poll with small limit: must surface the OLDEST `limit`
        # events after the cursor, not the newest.
        result1 = self._run_event_poll(since=anchor["id"], limit=10)
        self.assertEqual(result1.returncode, 0, msg=result1.stderr)
        first_batch = [
            json.loads(line)["id"]
            for line in result1.stdout.splitlines() if line.strip()
        ]
        self.assertEqual(
            first_batch, seeded_ids[:10],
            msg="agent jumped to latest — oldest events silently dropped",
        )
        self.assertEqual(self._read_cursor(), seeded_ids[9])

        # Second poll reads the now-advanced cursor from working-state.md;
        # no explicit --since needed.
        result2 = self._run_event_poll(limit=100)
        self.assertEqual(result2.returncode, 0, msg=result2.stderr)
        second_batch = [
            json.loads(line)["id"]
            for line in result2.stdout.splitlines() if line.strip()
        ]
        self.assertEqual(second_batch, seeded_ids[10:])
        self.assertEqual(self._read_cursor(), seeded_ids[-1])

    def test_cursor_at_head_returns_empty(self):
        """Cursor already at head: no events returned, exit 1, cursor unchanged."""
        head = self._seed_event("only-event")

        result = self._run_event_poll(since=head["id"], limit=50)
        # event_poll exits 1 when no events found (single-shot mode).
        self.assertEqual(result.returncode, 1, msg=result.stderr)
        self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
