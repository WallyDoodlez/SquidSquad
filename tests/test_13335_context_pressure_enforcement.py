"""#13335 — event-mode context-threshold enforcement in the health poller.

In event mode nothing runs ``cycle_post.py`` per event, so the loop-mode
exit-42 pressure path never fires and agents run unbounded past
``context-threshold``. The fix adds the missing ACTOR: the 5s health poller
(`HarnessState._enforce_context_pressure`) reads each running agent's
context-pressure and, at/over threshold, flips ``intent=restarting`` — reusing
the existing graceful-restart machinery (checkpoint at task boundary + 60s
force-kill net + auto-reboot → fresh-context respawn).

These tests pin the deterministic decision logic (the *what happens*), plus the
two file/config readers. They do NOT exercise the downstream restart machinery
(force-kill net / auto-reboot) — that is pre-existing and covered elsewhere;
here we assert only that the correct ``intent`` transition is (or isn't) made.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import harness  # noqa: E402
from harness import HarnessState, AgentState  # noqa: E402

_NOW = 5000.0


def _running_agent(role="skill", clone="/clone"):
    a = AgentState(role, clone)
    a.intent = AgentState.INTENT_RUNNING
    a.status = "running"
    a.bootup_complete = True
    a.intent_set_at = None
    return a


class TestEnforceContextPressure13335(unittest.TestCase):
    def _run(self, agent, *, pressure, threshold=70, no_reboot=False,
             roles=("skill",)):
        hs = HarnessState()
        if agent is not None:
            hs.set_agent(agent.role, agent)
        hs.save_state = MagicMock()  # never touch disk; assert call intent
        with patch("harness.boot_remote._get_all_roles",
                   return_value=list(roles)), \
                patch.object(HarnessState, "_read_context_threshold",
                             return_value=threshold), \
                patch.object(HarnessState, "_read_agent_pressure",
                             return_value=pressure), \
                patch("harness._NO_AUTO_REBOOT", no_reboot), \
                patch("harness.time.time", return_value=_NOW), \
                patch("harness._log"):
            hs._enforce_context_pressure()
        return hs

    # -- the trip ----------------------------------------------------------
    def test_over_threshold_flips_to_restarting(self):
        agent = _running_agent()
        hs = self._run(agent, pressure=85, threshold=70)
        self.assertEqual(agent.intent, AgentState.INTENT_RESTARTING)
        self.assertEqual(agent.intent_set_at, _NOW)
        self.assertFalse(agent.bootup_complete)
        hs.save_state.assert_called_once()

    def test_at_threshold_flips(self):
        """>= is the rule: pressure == threshold trips."""
        agent = _running_agent()
        self._run(agent, pressure=70, threshold=70)
        self.assertEqual(agent.intent, AgentState.INTENT_RESTARTING)

    # -- the no-ops --------------------------------------------------------
    def test_under_threshold_no_change(self):
        agent = _running_agent()
        hs = self._run(agent, pressure=69, threshold=70)
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        self.assertIsNone(agent.intent_set_at)
        hs.save_state.assert_not_called()

    def test_no_signal_is_skipped(self):
        """A missing/unreadable pressure file (None) is never enforced."""
        agent = _running_agent()
        hs = self._run(agent, pressure=None, threshold=70)
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        hs.save_state.assert_not_called()

    def test_already_restarting_not_re_armed(self):
        """An agent mid-restart must not have its 60s force-kill window
        re-stamped by a repeat trip."""
        agent = _running_agent()
        agent.intent = AgentState.INTENT_RESTARTING
        agent.intent_set_at = 123.0  # old timer
        hs = self._run(agent, pressure=99, threshold=70)
        self.assertEqual(agent.intent, AgentState.INTENT_RESTARTING)
        self.assertEqual(agent.intent_set_at, 123.0)  # unchanged
        hs.save_state.assert_not_called()

    def test_stopping_agent_skipped(self):
        agent = _running_agent()
        agent.intent = AgentState.INTENT_STOPPING
        hs = self._run(agent, pressure=99, threshold=70)
        self.assertEqual(agent.intent, AgentState.INTENT_STOPPING)
        hs.save_state.assert_not_called()

    def test_not_booted_skipped(self):
        agent = _running_agent()
        agent.bootup_complete = False
        hs = self._run(agent, pressure=99, threshold=70)
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        hs.save_state.assert_not_called()

    def test_non_running_status_skipped(self):
        agent = _running_agent()
        agent.status = "starting"
        hs = self._run(agent, pressure=99, threshold=70)
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        hs.save_state.assert_not_called()

    def test_no_auto_reboot_disables_enforcement(self):
        """Under _NO_AUTO_REBOOT a restart would only tear down a working agent
        with no respawn — enforcement is skipped entirely."""
        agent = _running_agent()
        hs = self._run(agent, pressure=99, threshold=70, no_reboot=True)
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        hs.save_state.assert_not_called()

    def test_missing_agent_state_is_safe(self):
        """A role in the registry with no AgentState yet must not crash."""
        hs = self._run(None, pressure=99, roles=("skill",))
        hs.save_state.assert_not_called()

    def test_only_over_threshold_agent_flips(self):
        """Multiple agents: only the one at/over threshold flips."""
        hs = HarnessState()
        hot = _running_agent("skill", "/c1")
        cool = _running_agent("pm", "/c2")
        hs.set_agent("skill", hot)
        hs.set_agent("pm", cool)
        hs.save_state = MagicMock()

        def _pressure(role, agent):
            return 90 if role == "skill" else 10

        with patch("harness.boot_remote._get_all_roles",
                   return_value=["skill", "pm"]), \
                patch.object(HarnessState, "_read_context_threshold",
                             return_value=70), \
                patch.object(HarnessState, "_read_agent_pressure",
                             side_effect=_pressure), \
                patch("harness._NO_AUTO_REBOOT", False), \
                patch("harness.time.time", return_value=_NOW), \
                patch("harness._log"):
            hs._enforce_context_pressure()

        self.assertEqual(hot.intent, AgentState.INTENT_RESTARTING)
        self.assertEqual(cool.intent, AgentState.INTENT_RUNNING)
        hs.save_state.assert_called_once()  # one persist for the batch


class TestReadContextThreshold13335(unittest.TestCase):
    def _read(self):
        return HarnessState()._read_context_threshold()

    def test_valid_value(self):
        with patch("config.get_field", return_value="80"):
            self.assertEqual(self._read(), 80)

    def test_absent_field_defaults(self):
        with patch("config.get_field", return_value=None):
            self.assertEqual(self._read(), harness.CONTEXT_THRESHOLD_DEFAULT)

    def test_malformed_defaults(self):
        with patch("config.get_field", return_value="lots"):
            self.assertEqual(self._read(), harness.CONTEXT_THRESHOLD_DEFAULT)

    def test_reader_exception_defaults(self):
        with patch("config.get_field", side_effect=RuntimeError("boom")):
            self.assertEqual(self._read(), harness.CONTEXT_THRESHOLD_DEFAULT)

    # ------------------------------------------------------------------
    # QA TC-3 regression (#13335 verifier bounce): the tests above patch
    # config.get_field — the defect lived below that seam. These run the
    # REAL config.get_field against a real config.md.
    # ------------------------------------------------------------------

    def test_tc3_real_get_field_absent_section_defaults_no_systemexit(self):
        """A config.md with NO `## Context Pressure` section must resolve to
        the registered default 70 via the real get_field — not sys.exit(1)
        (SystemExit escaped except-Exception and silently killed the whole
        health poller on its first tick)."""
        import tempfile
        import config as config_mod
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "config.md"
            cfg.write_text(
                "# SquidSquad Config\n\n## Project\n\n- **Name**: X\n",
                encoding="utf-8",
            )
            with patch.object(config_mod, "CONFIG_PATH", cfg):
                # (a) the real get_field returns the registered default…
                self.assertEqual(config_mod.get_field("context-threshold"), "70")
                # (b) …and the reader resolves it without dying.
                self.assertEqual(self._read(), 70)

    def test_tc3_real_get_field_present_section_wins(self):
        """The registered default must NOT shadow a configured value."""
        import tempfile
        import config as config_mod
        with tempfile.TemporaryDirectory() as td:
            cfg = Path(td) / "config.md"
            cfg.write_text(
                "# SquidSquad Config\n\n## Context Pressure\n\n"
                "- **Threshold**: 55\n",
                encoding="utf-8",
            )
            with patch.object(config_mod, "CONFIG_PATH", cfg):
                self.assertEqual(self._read(), 55)

    def test_tc3_systemexit_defense_in_depth(self):
        """Even if a config.py regression reintroduces an exit path, the
        reader's fail-open must swallow SystemExit (the exact BaseException
        class that escaped except-Exception in the QA repro)."""
        with patch("config.get_field", side_effect=SystemExit(1)):
            self.assertEqual(self._read(), harness.CONTEXT_THRESHOLD_DEFAULT)


class TestReadAgentPressure13335(unittest.TestCase):
    def _write(self, tmp, role, value):
        d = tmp / ".squidsquad" / role
        d.mkdir(parents=True, exist_ok=True)
        (d / "context-pressure").write_text(str(value), encoding="utf-8")

    def test_reads_int_from_clone(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._write(tmp, "skill", "72\n")
            agent = _running_agent("skill", str(tmp))
            hs = HarnessState()
            self.assertEqual(hs._read_agent_pressure("skill", agent), 72)

    def test_missing_file_is_none(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            agent = _running_agent("skill", td)
            hs = HarnessState()
            self.assertIsNone(hs._read_agent_pressure("skill", agent))

    def test_malformed_is_none(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._write(tmp, "skill", "high")
            agent = _running_agent("skill", str(tmp))
            hs = HarnessState()
            self.assertIsNone(hs._read_agent_pressure("skill", agent))

    def test_no_clone_path_falls_back_to_resolver(self):
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            self._write(tmp, "skill", "88")
            agent = _running_agent("skill", None)
            hs = HarnessState()
            with patch("harness.boot_remote._get_clone_path",
                       return_value=str(tmp)):
                self.assertEqual(hs._read_agent_pressure("skill", agent), 88)

    def test_resolver_failure_is_none(self):
        agent = _running_agent("skill", None)
        hs = HarnessState()
        with patch("harness.boot_remote._get_clone_path",
                   side_effect=RuntimeError("no clone")):
            self.assertIsNone(hs._read_agent_pressure("skill", agent))


if __name__ == "__main__":
    unittest.main()
