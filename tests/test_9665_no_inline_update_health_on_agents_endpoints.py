"""Tests for the #9665 follow-on to #9481.

#9481 moved ``state.update_health()`` off the asyncio event loop in
four read-only handlers — ``/status`` lost the call entirely, while
``/agents``, ``/agents/{role}``, and ``/agents/{role}/health`` wrapped
it in ``await asyncio.to_thread(...)``. That fixed the event-loop
wedge.

QA's re-verification of #9398 surfaced a deeper symptom: on warm
back-to-back Windows runs the wrapped call still exceeds the 30s
client-side timeout the #9398 helper bumped to (originally 10s →
30s in cycle 1198). Root cause: ``state.update_health()`` shells
out to ``tasklist`` per registered agent under ``state._lock``,
and on a hot machine with TIME_WAIT pressure from a prior test
suite the per-call latency can sustain 30s+ even off the event
loop. Bumping the test-helper timeout again would just escalate
the duct tape.

#9665 fix: extend the ``/status`` treatment to the other three
handlers. None of them may call ``state.update_health()`` inline
on the request path — neither bare nor wrapped. Freshness is the
background health poller's job (``HEALTH_POLL_INTERVAL = 5s``);
that contract was already documented in the #9481 commit and the
poller-invariant test in ``test_9481_update_health_off_event_loop.py``
still pins it.

What the #9398 test that surfaced this needs: the AgentState
record exists with ``bootup_complete=True`` after the agent
subprocess emits the event. That flag is set by the ``/events``
POST handler at receipt — not by ``update_health`` — so removing
the inline probe from ``/agents/{role}`` cannot affect the
assertion.
"""

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_PATH = REPO_ROOT / "references" / "scripts" / "harness.py"


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


class TestAgentsEndpointsNoInlineUpdateHealth(unittest.TestCase):
    """``/agents``, ``/agents/{role}``, and ``/agents/{role}/health``
    must NOT call ``state.update_health()`` on the request path —
    neither bare nor wrapped in ``asyncio.to_thread``. On warm Windows
    runs the call exceeds 30s, which is the documented client-side
    budget the #9398 helper bumped to. The background health poller
    is the only authoritative freshness path."""

    HANDLERS = [
        "async def list_agents",          # GET /agents
        "async def get_agent",            # GET /agents/{role}
        "async def get_agent_health",     # GET /agents/{role}/health
    ]

    def setUp(self):
        self.source = HARNESS_PATH.read_text(encoding="utf-8")

    def test_no_update_health_call_in_each_handler(self):
        """A real call has the form ``state.update_health(`` with a
        literal open-paren. Comments and backtick-quoted docstring
        references are ignored — they're documentation, not call
        sites."""
        for handler in self.HANDLERS:
            with self.subTest(handler=handler):
                body = _extract_handler_body(self.source, handler)
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
                        f"{handler}: must NOT call state.update_health() "
                        "(neither bare nor wrapped in asyncio.to_thread). "
                        "The background poller refreshes state every "
                        "HEALTH_POLL_INTERVAL seconds; on warm Windows "
                        "runs the inline call exceeds 30s and times out "
                        "callers (#9665, surfaced by #9398). Offending "
                        "lines:\n" + "\n".join(offending)
                    ),
                )


if __name__ == "__main__":
    unittest.main()
