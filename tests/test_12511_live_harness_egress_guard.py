"""#12511 — unit tests must not POST to the LIVE harness event bus.

Root cause: `tracker.transition(...)` / `tracker.add_comment(...)` call
`event_bus.emit(...)`, which discovers the dev box's running harness port
(`.harness-port`, default 7373) and fires a real `POST /events`. On a
self-hosting box this leaked illegal `status-transition` events for fixture
issues (#999) onto the production bus, spuriously waking every agent.

The fix is the autouse `_block_live_harness_egress` guard in tests/conftest.py.
These tests assert the guard's contract: live-harness egress is suppressed,
other egress passes through, and a forced in-process transition (the #12511
repro) does not reach the live bus.
"""

import sys
import urllib.error
import urllib.request
from pathlib import Path

import pytest

import conftest  # the guard + its record live here

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _live_url(path="/events"):
    return f"http://127.0.0.1:{conftest._live_harness_port()}{path}"


class TestEgressGuard:
    def test_post_to_live_harness_is_suppressed_and_recorded(self, request):
        req = urllib.request.Request(
            _live_url(), data=b"{}",
            headers={"Content-Type": "application/json"}, method="POST",
        )
        # The autouse guard intercepts this — no real connection, returns None.
        result = urllib.request.urlopen(req, timeout=2)
        assert result is None, "guard must suppress (no live POST escapes)"
        assert request.node.nodeid in conftest._SUPPRESSED_LIVE_EGRESS
        assert any("/events" in u for u in conftest._SUPPRESSED_LIVE_EGRESS[request.node.nodeid])

    def test_guard_does_not_overblock_other_ports(self):
        # A different port is NOT the live harness — the guard must delegate to
        # the real urlopen, which (nothing listening) raises a URLError. The
        # point is it is NOT silently suppressed (would return None instead).
        other = "http://127.0.0.1:7999/events"
        with pytest.raises(urllib.error.URLError):
            urllib.request.urlopen(other, timeout=2)


class TestForcedTransitionDoesNotLeak:
    """The #12511 repro: a forced transition emits a status-transition event;
    under the guard it must not reach the live bus."""

    def test_emit_status_transition_is_suppressed(self, request):
        import event_bus
        # event_bus.emit only POSTs if it discovers a .harness-port. Point its
        # discovery at the live .squidsquad so it resolves the live port, then
        # assert the guard suppressed the resulting POST rather than letting it
        # hit the production bus.
        live_port_file = REPO_ROOT / ".squidsquad" / ".harness-port"
        if not live_port_file.exists():
            pytest.skip("no live .harness-port on this box — emit no-ops before the wire")
        before = len(conftest._SUPPRESSED_LIVE_EGRESS.get(request.node.nodeid, []))
        event_bus.emit("status-transition", "skill",
                       payload={"issue_number": "999", "from": "shipped", "to": "in-progress"})
        after = len(conftest._SUPPRESSED_LIVE_EGRESS.get(request.node.nodeid, []))
        assert after == before + 1, "emit's live POST must be intercepted by the guard"
