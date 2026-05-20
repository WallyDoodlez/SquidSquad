"""Tests for the #9481 harness HTTP-wedge fix.

The cycle-1500 forensic dump showed the harness HTTP layer wedging on
every boot: process alive, port LISTEN, CloseWait connections piled up,
HTTP requests timed out indefinitely (HTTP 000).

The original issue body attributed the cause to
``WindowsProactorEventLoopPolicy`` running on a uvicorn daemon thread
(IOCP delivery on non-main-thread). A minimal repro with the same
shape — uvicorn in a daemon thread on Windows under the default
Proactor policy — returns 200 in milliseconds, falsifying that
hypothesis.

The actual cause: four read-only async handlers (``/status``,
``/agents``, ``/agents/{role}``, ``/agents/{role}/health``) called
``state.update_health()`` **synchronously on the asyncio event loop**.
On Windows, ``update_health()`` shells out to ``tasklist`` per agent
under ``state._lock`` — a 10-20s blocking call. While it ran, the
event loop could dispatch nothing else, producing the wedge symptoms.

The fix has two parts:

1. ``/status`` (the documented AC endpoint) no longer calls
   ``update_health()`` at all. The background health poller already
   refreshes state every ``HEALTH_POLL_INTERVAL`` seconds; ``/status``
   returns cached state in milliseconds.

2. The other three read-only handlers wrapped ``update_health()`` in
   ``await asyncio.to_thread(...)`` so the slow probe ran in a worker
   thread instead of freezing the loop.

   **Superseded by #9665.** On warm Windows runs the probe exceeds
   30s even off the event loop, which timed out the #9398
   real-subprocess integration tests. #9665 removed the inline call
   from those three handlers as well — same treatment ``/status``
   already got. The positive assertion for that new invariant lives
   in ``test_9665_no_inline_update_health_on_agents_endpoints.py``.
"""

import importlib.util
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
HARNESS_PATH = SCRIPTS / "harness.py"


def _load_module(name: str, source: Path):
    spec = importlib.util.spec_from_file_location(name, source)
    if not (spec and spec.loader):
        raise ImportError(f"cannot build spec for {source}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


try:
    _harness = _load_module("_harness_for_9481", HARNESS_PATH)
    HARNESS_AVAILABLE = True
except Exception as _e:
    print(
        f"[test_9481] harness import failed: {type(_e).__name__}: {_e}",
        file=sys.stderr,
    )
    HARNESS_AVAILABLE = False
    _harness = None  # type: ignore


def _extract_handler_body(source: str, handler_signature: str) -> str:
    """Return the source between ``handler_signature`` and the next
    ``@app.``, ``def``, ``async def``, or ``class`` boundary."""
    idx = source.find(handler_signature)
    if idx < 0:
        raise AssertionError(
            f"handler '{handler_signature}' not found in harness.py — "
            f"if it was renamed, update this test too."
        )
    sig_end = source.find("\n", idx) + 1
    candidates = [
        source.find("\n@app.", sig_end),
        source.find("\nasync def ", sig_end),
        source.find("\ndef ", sig_end),
        source.find("\nclass ", sig_end),
    ]
    candidates = [c for c in candidates if c > 0]
    end = min(candidates) if candidates else len(source)
    return source[sig_end:end]


class TestStatusEndpointNoInlineUpdateHealth(unittest.TestCase):
    """``/status`` is the AC-bound endpoint (operator-facing probe,
    must return 200 within 5 seconds). It MUST NOT call
    ``state.update_health()`` inline — that's a ~10s subprocess storm
    on Windows that wedged the loop in cycle 1500."""

    def setUp(self):
        self.source = HARNESS_PATH.read_text(encoding="utf-8")

    def test_get_status_does_not_call_update_health(self):
        body = _extract_handler_body(self.source, "async def get_status")
        # Match real call sites only — skip comments and docstring code
        # references (backtick-quoted spans). A real call has the form
        # `state.update_health(` with a literal open-paren.
        offending = []
        for line in body.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            cleaned = re.sub(r"``[^`]*``", "", line)
            if "state.update_health(" in cleaned:
                offending.append(line)
        self.assertEqual(
            offending, [],
            msg=(
                "/status must NOT call state.update_health() (neither bare "
                "nor wrapped). The background health poller already refreshes "
                "state every HEALTH_POLL_INTERVAL seconds; calling it inline "
                "shells out to `tasklist` per agent on Windows and freezes "
                "the loop (#9481, cycle-1500 wedge). Offending lines:\n"
                + "\n".join(offending)
            ),
        )


# NOTE: ``TestReadOnlyHandlersUpdateHealthOffEventLoop`` lived here in
# the original #9481 commit and asserted that ``list_agents``,
# ``get_agent``, and ``get_agent_health`` wrapped ``update_health`` in
# ``asyncio.to_thread``. #9665 superseded that — those handlers no
# longer call ``update_health`` at all (same treatment ``/status`` got
# above). See ``test_9665_no_inline_update_health_on_agents_endpoints.py``
# for the new invariant.


class TestUpdateHealthStillCalledFromPoller(unittest.TestCase):
    """The background health poller is now the *only* path that calls
    ``update_health`` on a hot loop. If someone deletes the poller, the
    inline-probe removal in ``/status`` would silently regress agent
    health freshness. Pin the poller-thread invariant."""

    def setUp(self):
        self.source = HARNESS_PATH.read_text(encoding="utf-8")

    def test_poll_loop_calls_update_health(self):
        body = _extract_handler_body(self.source, "def _poll_loop")
        self.assertIn(
            "update_health", body,
            msg=(
                "_poll_loop must call self.update_health() — it is the "
                "background freshness path that /status relies on after "
                "#9481 removed the inline probe."
            ),
        )

    def test_start_poller_invoked_in_lifespan(self):
        body = _extract_handler_body(self.source, "async def lifespan")
        self.assertIn(
            "state.start_poller()", body,
            msg=(
                "Lifespan must call state.start_poller() before yield. "
                "If it doesn't, /status returns stale state forever after "
                "#9481 (no other code path refreshes agent health)."
            ),
        )


if __name__ == "__main__":
    unittest.main()
