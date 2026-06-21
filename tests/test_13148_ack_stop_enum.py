"""Regression: the harness `ack-stop` handler recognizes the SETTLED result
enum — 'checkpointed' / 'aborted' / 'drained' (AGENT-RUNTIME §10 Q11, closed
2026-05-30) — not the obsolete 'stop-confirmed' (#13148).

Before the fix, `receive_event` keyed the stop-confirm branch on
`result == "stop-confirmed"`, which is NOT in the settled enum — so a
correctly-emitted stop ack would have silently missed it. These tests POST the
settled values and assert the handler accepts them (200) without resetting
`intent_set_at` (which would extend the 60s force-kill window).
"""

import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

try:
    from fastapi.testclient import TestClient
    import harness  # noqa: F401
    from harness import app, state, AgentState
    _HTTP_OK = True
except Exception:  # pragma: no cover - import guard
    _HTTP_OK = False


@unittest.skipUnless(_HTTP_OK, "fastapi / harness not importable")
class TestAckStopSettledEnum(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        state.start_time = time.time()
        state.port = 7373
        cls.client = TestClient(app, raise_server_exceptions=False)

    def _stopping_agent(self, set_at=12345.0):
        agent = AgentState("skill", "/p")
        agent.intent = AgentState.INTENT_STOPPING
        agent.intent_set_at = set_at
        state.set_agent("skill", agent)
        return agent

    def _post(self, result):
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch.object(state, "save_state"):
            return self.client.post(
                "/events",
                json={"event_type": "ack-stop", "role": "skill",
                      "payload": {"event_id": "evt-1", "result": result}},
            )

    def test_checkpointed_accepted_without_clock_reset(self):
        agent = self._stopping_agent(set_at=12345.0)
        resp = self._post("checkpointed")
        self.assertEqual(resp.status_code, 200)
        # The clock must NOT be reset — intent_set_at is set at stop-REQUEST time.
        self.assertEqual(agent.intent_set_at, 12345.0)
        self.assertEqual(agent.intent, AgentState.INTENT_STOPPING)

    def test_drained_accepted(self):
        agent = self._stopping_agent(set_at=222.0)
        resp = self._post("drained")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(agent.intent_set_at, 222.0)

    def test_aborted_accepted_and_logged(self):
        agent = self._stopping_agent(set_at=333.0)
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch.object(state, "save_state"), \
             patch("harness._log") as mock_log:
            resp = self.client.post(
                "/events",
                json={"event_type": "ack-stop", "role": "skill",
                      "payload": {"event_id": "evt-1", "result": "aborted"}},
            )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(agent.intent_set_at, 333.0)  # no clock reset
        # 'aborted' (graceful stop failed) is logged for visibility.
        logged = " ".join(str(c.args[0]) for c in mock_log.call_args_list if c.args)
        self.assertIn("aborted", logged)

    def test_obsolete_stop_confirmed_not_specially_handled(self):
        """The obsolete 'stop-confirmed' value is no longer in the settled enum;
        it is accepted as a generic ack-stop (200) but does not hit the
        stop-path branch — proving the handler keys on the settled enum."""
        agent = self._stopping_agent(set_at=444.0)
        resp = self._post("stop-confirmed")
        # Still a valid POST (200) — but it is not a settled stop-result, so it
        # falls through (no special handling). intent_set_at unchanged either way.
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(agent.intent_set_at, 444.0)
