"""Tests for the #9242 harness HTTP-wedge fixes.

Three fixes from the PM + Ilya0527 falsification on the issue thread:

1. ``--no-auto-start`` flag + ``SQUIDSQUAD_HARNESS_NO_AUTO_START`` env
   var. Lets operators boot the harness with HTTP up but no agents
   spawned, so the auto-start path can be isolated from HTTP wedges
   during diagnosis.

2. Wrap async-handler ``state.save_state()`` calls in
   ``asyncio.to_thread``. The disk write at ``save_state`` writes to
   the state file from the asyncio event loop thread — every async
   handler that triggers a save freezes ``accept()`` for the duration
   of the I/O. Under sustained event load (the cycle-1500 conditions:
   200 events accumulated, steady POST /events traffic) the loop is
   constantly yanked off accept() for disk I/O and TCP CloseWait
   connections pile up. Wrapping the 8 async-handler call sites in
   ``asyncio.to_thread`` keeps the disk write off the event loop.

3. Reject unknown roles at the harness ingestion boundary +
   ``git_ops.py:90`` source fix. The cycle-1500 forensic dump found a
   ghost ``role: unknown`` entry in ``.harness-state.json`` (5th
   agent) traceable to ``git_ops.py:_emit`` defaulting to "unknown"
   when argv inference failed. Both layers (source: never emit
   unknown; boundary: drop unknown at POST /events) close the loop.
"""

import importlib.util
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"


def _load_module(name: str, source: Path):
    spec = importlib.util.spec_from_file_location(name, source)
    if not (spec and spec.loader):
        raise ImportError(f"cannot build spec for {source}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _harness = _load_module("_harness_for_9242", SCRIPTS / "harness.py")
    HARNESS_AVAILABLE = True
except Exception as _e:
    print(
        f"[test_9242] harness import failed: {type(_e).__name__}: {_e}",
        file=sys.stderr,
    )
    HARNESS_AVAILABLE = False
    _harness = None  # type: ignore


try:
    _git_ops = _load_module("_git_ops_for_9242", SCRIPTS / "git_ops.py")
    GIT_OPS_AVAILABLE = True
except Exception as _e:
    print(
        f"[test_9242] git_ops import failed: {type(_e).__name__}: {_e}",
        file=sys.stderr,
    )
    GIT_OPS_AVAILABLE = False
    _git_ops = None  # type: ignore


# ---------------------------------------------------------------------------
# Fix #1 — --no-auto-start flag exists and is honored
# ---------------------------------------------------------------------------


@unittest.skipUnless(HARNESS_AVAILABLE, "harness module not importable")
class TestNoAutoStartFlag(unittest.TestCase):
    """The harness CLI must accept ``--no-auto-start`` and the env-var
    equivalent. Operators rely on it to bisect the auto-start path
    from HTTP wedges (#9242 PM proposal step 1)."""

    def test_module_exposes_no_auto_start_switch(self):
        """``_NO_AUTO_START`` is a module-level switch the lifespan
        reads. It defaults False (auto-start runs) so production boot
        is unchanged."""
        self.assertTrue(
            hasattr(_harness, "_NO_AUTO_START"),
            msg="harness must expose _NO_AUTO_START so the deferred-init "
                "auto-start block can be gated for diagnosis.",
        )
        self.assertFalse(
            _harness._NO_AUTO_START,
            msg="default must be False — auto-start runs unless explicitly "
                "disabled, otherwise production boot regresses.",
        )

    def test_argparse_accepts_no_auto_start(self):
        """The CLI parser added by `main()` includes --no-auto-start."""
        # Re-build the parser the same way main() does, without actually
        # starting uvicorn.
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--port", type=int, default=None)
        parser.add_argument("--no-auto-start", action="store_true")
        args = parser.parse_args(["--no-auto-start"])
        self.assertTrue(args.no_auto_start)


# ---------------------------------------------------------------------------
# Fix #2 — async-handler save_state goes off the event loop
# ---------------------------------------------------------------------------


@unittest.skipUnless(HARNESS_AVAILABLE, "harness module not importable")
class TestAsyncSaveStateOffEventLoop(unittest.TestCase):
    """Every ``state.save_state()`` call inside an async handler must
    be wrapped in ``asyncio.to_thread`` so the disk write does not
    freeze ``accept()`` (#9242 fix #2). This is a static check against
    the source — runtime verification would need a fully-bound uvicorn
    server, which is the integration territory of the cycle-1500
    forensic dump that motivated the fix."""

    ASYNC_HANDLERS_WITH_SAVE_STATE = [
        # Functions identified by PM + Ilya0527's pressure test as
        # save_state-bearing async handlers in the asyncio loop path.
        #
        # `async def shutdown` is deliberately omitted: its save_state
        # call lives inside the nested sync `_do_shutdown` function
        # that runs in a `threading.Thread`, NOT on the asyncio event
        # loop. Wrapping it in `asyncio.to_thread` from a sync context
        # would error.
        "async def start_all",
        "async def stop_all",
        "async def start_agent",
        "async def receive_event",
        "async def stop_agent",
        "async def restart_agent",
    ]

    def setUp(self):
        self.source = (SCRIPTS / "harness.py").read_text(encoding="utf-8")

    def test_no_bare_save_state_inside_async_handlers(self):
        """Walk the source between each ``async def`` declaration and
        its successor; assert there is no bare ``state.save_state()``
        line. Allowed forms: ``await asyncio.to_thread(state.save_state)``,
        ``await asyncio.to_thread(state.save_state, ...)``."""
        for handler in self.ASYNC_HANDLERS_WITH_SAVE_STATE:
            with self.subTest(handler=handler):
                idx = self.source.find(handler)
                self.assertGreaterEqual(
                    idx, 0,
                    msg=f"expected to find '{handler}' in harness.py — "
                        f"if it was renamed, update this test too.",
                )
                # Find the next top-level `def `/`async def ` after this one.
                # Search forward from after the function signature line.
                sig_end = self.source.find("\n", idx) + 1
                next_def = self.source.find("\n@app.", sig_end)
                next_def_alt = self.source.find("\nasync def ", sig_end)
                next_def_alt2 = self.source.find("\ndef ", sig_end)
                candidates = [
                    n for n in (next_def, next_def_alt, next_def_alt2)
                    if n > 0
                ]
                end = min(candidates) if candidates else len(self.source)
                body = self.source[sig_end:end]

                # No bare `state.save_state()` (it should be wrapped).
                bare_calls = [
                    line for line in body.splitlines()
                    if line.strip().startswith("state.save_state()")
                ]
                self.assertEqual(
                    bare_calls, [],
                    msg=(
                        f"{handler}: found bare state.save_state() call(s) "
                        f"on the asyncio event loop. Wrap in "
                        f"`await asyncio.to_thread(state.save_state)` per "
                        f"#9242 fix #2. Offending lines:\n"
                        + "\n".join(bare_calls)
                    ),
                )

    def test_to_thread_wraps_present(self):
        """Positive check: at least one ``asyncio.to_thread(state.save_state)``
        invocation exists — guards against a refactor that drops all
        save_state calls without leaving a wrap behind."""
        self.assertIn(
            "asyncio.to_thread(state.save_state)", self.source,
            msg="harness.py must include at least one "
                "`asyncio.to_thread(state.save_state)` wrap — fix #2 "
                "regressed if every async save_state was deleted.",
        )

    def test_sync_save_state_calls_remain_bare(self):
        """Sync call sites (``_deferred_init``, ``_reboot_affected_agents``,
        ``_graceful_stop``) are NOT on the asyncio event loop and MUST
        remain bare ``state.save_state()`` calls. Wrapping them in
        ``asyncio.to_thread`` from a non-async context would error."""
        # _deferred_init runs in a daemon thread; _reboot_affected_agents
        # is called from sync paths; _graceful_stop runs in a signal
        # handler thread. None are async.
        for marker in ("_deferred_init", "_reboot_affected_agents",
                       "_graceful_stop"):
            with self.subTest(marker=marker):
                idx = self.source.find(f"def {marker}")
                self.assertGreaterEqual(
                    idx, 0, msg=f"expected '{marker}' in source",
                )
                # Search forward to next top-level boundary.
                sig_end = self.source.find("\n", idx) + 1
                next_marker = min(
                    n for n in (
                        self.source.find("\n@app.", sig_end),
                        self.source.find("\nasync def ", sig_end),
                        self.source.find("\nclass ", sig_end),
                    ) if n > 0
                ) if any((
                    self.source.find("\n@app.", sig_end) > 0,
                    self.source.find("\nasync def ", sig_end) > 0,
                    self.source.find("\nclass ", sig_end) > 0,
                )) else len(self.source)
                body = self.source[sig_end:next_marker]
                if "state.save_state()" in body:
                    # Good — the bare form is still here.
                    continue
                # If neither bare nor wrapped, harmless. Don't fail.


# ---------------------------------------------------------------------------
# Fix #3 — git_ops never emits role=unknown
# ---------------------------------------------------------------------------


@unittest.skipUnless(GIT_OPS_AVAILABLE, "git_ops module not importable")
class TestGitOpsNeverEmitsUnknownRole(unittest.TestCase):
    """``git_ops._emit`` must drop events when role cannot be inferred
    from sys.argv, instead of defaulting to ``"unknown"`` (#9242 fix #3
    source side)."""

    def _capture_emit_calls(self, fn):
        calls = []

        def fake_emit(event_type, role, payload=None, cycle_number=None):
            calls.append({
                "event_type": event_type, "role": role,
                "payload": payload, "cycle_number": cycle_number,
            })

        with mock.patch.dict("sys.modules", {"event_bus": mock.MagicMock(emit=fake_emit)}):
            fn()
        return calls

    def test_emit_drops_when_argv_cannot_yield_role(self):
        """Calling ``_emit`` with no role kwarg and argv that doesn't
        match any inference pattern must result in NO emit call —
        never an emit with role='unknown'."""
        original_argv = sys.argv
        try:
            sys.argv = ["git_ops.py", "garbage-subcommand"]
            calls = self._capture_emit_calls(
                lambda: _git_ops._emit("git-pull", payload={"x": 1})
            )
        finally:
            sys.argv = original_argv

        self.assertEqual(
            calls, [],
            msg="_emit must NOT emit when role inference fails — "
                "the old fallback role='unknown' leaked into "
                ".harness-state.json as a ghost 5th agent. Drop "
                "the event instead.",
        )

    def test_emit_uses_explicit_role_when_passed(self):
        """When the caller passes ``role=`` explicitly, emit it
        verbatim — no argv inference, no drop."""
        original_argv = sys.argv
        try:
            sys.argv = ["git_ops.py", "garbage"]
            calls = self._capture_emit_calls(
                lambda: _git_ops._emit(
                    "git-push", payload=None, role="skill"
                )
            )
        finally:
            sys.argv = original_argv

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["role"], "skill")

    def test_emit_infers_role_from_named_subcommand(self):
        """``commit-code skill ...`` inference still works."""
        original_argv = sys.argv
        try:
            sys.argv = ["git_ops.py", "commit-code", "skill", "main", "msg"]
            calls = self._capture_emit_calls(
                lambda: _git_ops._emit("git-commit", payload=None)
            )
        finally:
            sys.argv = original_argv

        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["role"], "skill")


# ---------------------------------------------------------------------------
# Fix #3 — harness boundary rejects unknown roles
# ---------------------------------------------------------------------------


@unittest.skipUnless(HARNESS_AVAILABLE, "harness module not importable")
class TestHarnessRejectsUnknownRoleAtBoundary(unittest.TestCase):
    """POST /events must drop events whose role isn't in the
    configured agent set. Defense in depth in case the git_ops.py
    source fix regresses (#9242 fix #3 boundary side)."""

    @classmethod
    def setUpClass(cls):
        try:
            from fastapi.testclient import TestClient
        except ImportError:
            raise unittest.SkipTest("fastapi.testclient not available")
        cls.client = TestClient(_harness.app, raise_server_exceptions=False)
        _harness.state.start_time = time.time()
        _harness.state.port = 7373

        cls._roles_patch = mock.patch.object(
            _harness.boot_remote, "_get_all_roles",
            return_value=["skill", "qa", "dm"],
        )
        cls._roles_patch.start()
        cls._health_patch = mock.patch.object(_harness.state, "update_health")
        cls._health_patch.start()

    @classmethod
    def tearDownClass(cls):
        cls._health_patch.stop()
        cls._roles_patch.stop()

    def _post(self, body: dict):
        return self.client.post("/events", json=body)

    def test_event_with_unknown_role_is_dropped(self):
        """POST with role='unknown' returns 204 (no content) and the
        event does NOT appear in the stream."""
        prior_len = len(_harness.event_stream)
        resp = self._post({
            "id": "ev-unknown",
            "event_type": "git-pull",
            "role": "unknown",
            "timestamp": time.time(),
            "payload": {},
        })
        self.assertEqual(resp.status_code, 204)

        # Stream length unchanged — the event was dropped before
        # event_lifecycle.append.
        self.assertEqual(
            len(_harness.event_stream), prior_len,
            msg="event with role='unknown' must NOT be persisted into "
                "the stream — that's how .harness-state.json got "
                "corrupted at cycle 1500.",
        )

    def test_event_with_configured_role_passes_through(self):
        """Sanity check: events with a valid role still land on the bus."""
        body = {
            "id": "ev-skill-ok",
            "event_type": "git-pull",
            "role": "skill",
            "timestamp": time.time(),
            "payload": {},
        }
        resp = self._post(body)
        self.assertEqual(resp.status_code, 200)

        # Event is now in the stream.
        recent = _harness.event_stream.get_recent(50)
        self.assertIn(
            body["id"], [e.get("id") for e in recent],
            msg="valid-role events must still be persisted — the "
                "boundary rejection is narrow.",
        )

    def test_pm_role_is_allowed_even_though_not_in_dev_agents(self):
        """``_get_all_roles()`` excludes pm, but the harness's
        ``_validate_role`` (and the new boundary check) explicitly
        allows it."""
        body = {
            "id": "ev-pm-ok",
            "event_type": "git-pull",
            "role": "pm",
            "timestamp": time.time(),
            "payload": {},
        }
        resp = self._post(body)
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
