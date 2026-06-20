"""#12912 (deploy-signal recompose model) — S2 intent-sequencing tests.

Covers AC9: the harness sets intent=deploying before the agent halts so a
deploy-halt PID-death is NOT misread as a crash + auto-respawned out of order.

The health poller is an async loop that is impractical to drive directly, so
its deploy-halt handling is asserted via source inspection (the established
pattern in test_harness.py::test_ack_stop_confirmed_guarded_by_stopping_intent).
The load-state reset is exercised behaviorally.
"""

import inspect
import json
import unittest
from pathlib import Path
from unittest.mock import patch

import sys

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from harness import AgentState, HarnessState, receive_event, HarnessState as _HS  # noqa: E402


class TestIntentDeployingConstant(unittest.TestCase):
    def test_constant_exists_and_value(self):
        self.assertTrue(hasattr(AgentState, "INTENT_DEPLOYING"))
        self.assertEqual(AgentState.INTENT_DEPLOYING, "deploying")

    def test_deploying_excluded_from_should_reboot(self):
        """AC9: a deploy-halt death must never satisfy should_reboot. The
        respawn-eligible intent set is RUNNING/RESTARTING only — DEPLOYING is
        not in it, so the health poller cannot auto-respawn a deploy-halt."""
        src = inspect.getsource(_HS)  # health poller lives on HarnessState
        # Locate the should_reboot assignment and assert DEPLOYING is absent.
        idx = src.find("should_reboot = agent.intent in (")
        self.assertNotEqual(idx, -1, "should_reboot intent set not found")
        block = src[idx:idx + 200]
        self.assertIn("INTENT_RUNNING", block)
        self.assertIn("INTENT_RESTARTING", block)
        self.assertNotIn("INTENT_DEPLOYING", block,
                         "DEPLOYING must NOT be respawn-eligible (AC9)")


class TestHealthPollStatusSettling(unittest.TestCase):
    def test_deploying_death_settles_to_deploying_not_stalled(self):
        """A dead agent with intent=DEPLOYING settles to status='deploying'
        (HARNESS-ARCH §7.1.1), keeping it out of the is_dead crash set."""
        src = inspect.getsource(_HS)
        self.assertIn("INTENT_DEPLOYING", src)
        # The settling branch must map DEPLOYING -> "deploying".
        idx = src.find("agent.intent == AgentState.INTENT_DEPLOYING")
        self.assertNotEqual(idx, -1)
        block = src[idx:idx + 700]
        self.assertIn('agent.status = "deploying"', block)


class TestLoadStateResetsDeploying(unittest.TestCase):
    def test_load_state_resets_deploying_to_running(self):
        """#12912: a restored DEPLOYING intent (interrupted deploy across a
        harness restart) resets to RUNNING with the clock cleared, so the agent
        respawns normally on its existing committed CLAUDE.md."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            state_file.write_text(json.dumps({
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {
                    "skill": {"intent": "deploying",
                              "intent_set_at": 100.0,
                              "status": "deploying", "boot_time": None,
                              "clone_path": "", "claude_pid": 4321,
                              "terminal_pid": None},
                },
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file), \
                 patch("harness._log"), \
                 patch("harness.time.time", return_value=9999.0):
                hs = HarnessState()
                hs.load_state()
                loaded = hs.get_agent("skill")
                self.assertEqual(loaded.intent, AgentState.INTENT_RUNNING)
                self.assertIsNone(loaded.intent_set_at)


class TestAckStopDeployHalted(unittest.TestCase):
    def test_deploy_halted_branch_exists(self):
        """The ack-stop handler must branch on result=='deploy-halted',
        distinct from the stop-confirmed branch."""
        src = inspect.getsource(receive_event)
        self.assertIn('ack_payload.get("result") == "deploy-halted"', src)

    def test_deploy_halted_sets_deploying_status_and_intent(self):
        """The deploy-halted branch records the halt: status='deploying' and
        intent=DEPLOYING (defensive if the emit side didn't set it)."""
        src = inspect.getsource(receive_event)
        idx = src.find('"deploy-halted"')
        self.assertNotEqual(idx, -1)
        block = src[idx:idx + 1400]
        self.assertIn('agent.status = "deploying"', block)
        self.assertIn("INTENT_DEPLOYING", block)


class TestRebootAffectedAgentsEmitsDeploySignal(unittest.TestCase):
    """S3 (AC4/AC5, closes #12397): _reboot_affected_agents is the deploy-signal
    emitter — it sets intent=DEPLOYING and emits a deploy-signal to each affected
    alias instead of force-restarting them directly."""

    def _make_agent(self, intent):
        a = AgentState("skill", "")
        a.intent = intent
        return a

    def test_emits_deploy_signal_to_affected_running_agent(self):
        import harness
        agent = self._make_agent(AgentState.INTENT_RUNNING)

        emitted = []

        class _FakeState:
            def get_agent(self, role):
                return agent if role == "skill" else None

            def set_agent(self, role, a):
                pass

            def save_state(self):
                pass

        class _FakeDiff:
            returncode = 0
            stdout = ".squidsquad/skill/CLAUDE.md\n"

        with patch.object(harness, "_NO_AUTO_REBOOT", False), \
             patch.object(harness, "state", _FakeState()), \
             patch.object(harness, "subprocess") as msub, \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append((a, k))), \
             patch.object(harness, "_log"), \
             patch.object(harness, "time") as mtime:
            msub.run.return_value = _FakeDiff()
            mtime.time.return_value = 123.0
            harness._reboot_affected_agents(99, ["references/roles/instructions.md"])

        # Intent moved to DEPLOYING (sequencing), not RESTARTING.
        self.assertEqual(agent.intent, AgentState.INTENT_DEPLOYING)
        # Exactly one deploy-signal emitted, scoped to the affected alias.
        self.assertEqual(len(emitted), 1)
        args, kwargs = emitted[0]
        self.assertEqual(args[0], "deploy-signal")
        self.assertEqual(kwargs["payload"]["target_alias"], "skill")
        self.assertEqual(kwargs["payload"]["event_type"], "deploy-signal")
        self.assertEqual(kwargs["payload"]["event_context"], "deploy-signal")

    def test_no_auto_reboot_suppresses_emit(self):
        """HARNESS-ARCH §7.6: under --no-auto-reboot the emit is skipped."""
        import harness
        emitted = []
        with patch.object(harness, "_NO_AUTO_REBOOT", True), \
             patch.object(harness, "_emit_event",
                          side_effect=lambda *a, **k: emitted.append(a)), \
             patch.object(harness, "_log"):
            harness._reboot_affected_agents(99, ["references/roles/instructions.md"])
        self.assertEqual(emitted, [])

    def test_no_direct_restart_intent_in_emitter(self):
        """The emitter must not set INTENT_RESTARTING (that was the old path)."""
        src = inspect.getsource(receive_event.__globals__["_reboot_affected_agents"])
        self.assertIn("INTENT_DEPLOYING", src)
        self.assertIn("deploy-signal", src)
        self.assertNotIn("INTENT_RESTARTING", src)


if __name__ == "__main__":
    unittest.main()
