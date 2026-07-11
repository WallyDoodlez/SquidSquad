"""QA independent live-chain tests for #13335 (TEST-PLAN-13335 TC-1..TC-6).

Verifier-owned, derived from the issue body's expected behavior — NOT from the
worker's unit tests. Deliberately closes the worker-test mock gap: the worker's
enforcement tests patch `_read_context_threshold` and `_read_agent_pressure`;
these tests run the REAL chain — a real temp clone tree with a real
`.squidsquad/<role>/context-pressure` file, a real config.md parsed by the real
`config.get_field`, and the real `_enforce_context_pressure` — patching only
the process-external seams (role registry, state-file persistence, wall clock,
log sink).
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import config as config_mod  # noqa: E402
import harness  # noqa: E402
from harness import HarnessState, AgentState  # noqa: E402

_NOW = 9000.0

CONFIG_WITH_THRESHOLD = """# SquidSquad Config

## Context Pressure

- **Threshold**: 55
"""

CONFIG_WITHOUT_SECTION = """# SquidSquad Config

## Project

- **Name**: SquidSquad
"""


def _agent(role, clone, *, intent=AgentState.INTENT_RUNNING, status="running",
           booted=True):
    a = AgentState(role, str(clone))
    a.intent = intent
    a.status = status
    a.bootup_complete = booted
    a.intent_set_at = None
    return a


class RealChainEnforcement13335(unittest.TestCase):
    """TC-2/TC-4/TC-5/TC-6: real files, real config, real enforcement."""

    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.tmp = Path(self._td.name)
        self.clone = self.tmp / "clone"

    def tearDown(self):
        self._td.cleanup()

    def _write_pressure(self, role, value):
        d = self.clone / ".squidsquad" / role
        d.mkdir(parents=True, exist_ok=True)
        (d / "context-pressure").write_text(str(value), encoding="utf-8")

    def _write_config(self, content):
        cfg = self.tmp / "config.md"
        cfg.write_text(content, encoding="utf-8")
        return cfg

    def _enforce(self, agents, roles):
        hs = HarnessState()
        for r, a in agents.items():
            hs.set_agent(r, a)
        hs.save_state = MagicMock()
        with patch("harness.boot_remote._get_all_roles", return_value=roles), \
                patch("harness._NO_AUTO_REBOOT", False), \
                patch("harness.time.time", return_value=_NOW), \
                patch("harness._log"):
            hs._enforce_context_pressure()
        return hs

    def test_tc2_real_pressure_file_over_config_threshold_flips(self):
        """Pressure file 72, real config threshold 55 -> intent=restarting."""
        cfg = self._write_config(CONFIG_WITH_THRESHOLD)
        self._write_pressure("skill", "72")
        agent = _agent("skill", self.clone)
        with patch.object(config_mod, "CONFIG_PATH", cfg):
            hs = self._enforce({"skill": agent}, ["skill"])
        self.assertEqual(agent.intent, AgentState.INTENT_RESTARTING)
        self.assertEqual(agent.intent_set_at, _NOW)
        self.assertFalse(agent.bootup_complete)
        hs.save_state.assert_called_once()

    def test_tc3_default_70_when_config_section_absent(self):
        """No Context Pressure section: 69 no-flip, 70 flips (default 70)."""
        cfg = self._write_config(CONFIG_WITHOUT_SECTION)
        self._write_pressure("skill", "69")
        agent = _agent("skill", self.clone)
        with patch.object(config_mod, "CONFIG_PATH", cfg):
            self._enforce({"skill": agent}, ["skill"])
            self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
            self._write_pressure("skill", "70")
            self._enforce({"skill": agent}, ["skill"])
        self.assertEqual(agent.intent, AgentState.INTENT_RESTARTING)

    def test_tc3b_configured_threshold_respected_below(self):
        """Real config threshold 55: pressure 54 -> no flip."""
        cfg = self._write_config(CONFIG_WITH_THRESHOLD)
        self._write_pressure("skill", "54")
        agent = _agent("skill", self.clone)
        with patch.object(config_mod, "CONFIG_PATH", cfg):
            hs = self._enforce({"skill": agent}, ["skill"])
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        self.assertIsNone(agent.intent_set_at)
        hs.save_state.assert_not_called()

    def test_tc6a_already_restarting_timer_not_rearmed_real_files(self):
        cfg = self._write_config(CONFIG_WITH_THRESHOLD)
        self._write_pressure("skill", "99")
        agent = _agent("skill", self.clone,
                       intent=AgentState.INTENT_RESTARTING)
        agent.intent_set_at = 111.0
        with patch.object(config_mod, "CONFIG_PATH", cfg):
            hs = self._enforce({"skill": agent}, ["skill"])
        self.assertEqual(agent.intent_set_at, 111.0)
        hs.save_state.assert_not_called()

    def test_tc6c_unbooted_agent_skipped_real_files(self):
        cfg = self._write_config(CONFIG_WITH_THRESHOLD)
        self._write_pressure("skill", "99")
        agent = _agent("skill", self.clone, booted=False)
        with patch.object(config_mod, "CONFIG_PATH", cfg):
            self._enforce({"skill": agent}, ["skill"])
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)

    def test_tc6d_missing_pressure_file_failopen_real_files(self):
        cfg = self._write_config(CONFIG_WITH_THRESHOLD)
        (self.clone / ".squidsquad" / "skill").mkdir(parents=True)
        agent = _agent("skill", self.clone)
        with patch.object(config_mod, "CONFIG_PATH", cfg):
            hs = self._enforce({"skill": agent}, ["skill"])
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        hs.save_state.assert_not_called()

    def test_tc6d_malformed_pressure_file_failopen_real_files(self):
        cfg = self._write_config(CONFIG_WITH_THRESHOLD)
        self._write_pressure("skill", "seventy-two%")
        agent = _agent("skill", self.clone)
        with patch.object(config_mod, "CONFIG_PATH", cfg):
            hs = self._enforce({"skill": agent}, ["skill"])
        self.assertEqual(agent.intent, AgentState.INTENT_RUNNING)
        hs.save_state.assert_not_called()

    def test_tc2b_statusline_style_content_with_newline(self):
        """The statusline writes 'NN\\n' — real-world file shape parses."""
        cfg = self._write_config(CONFIG_WITH_THRESHOLD)
        self._write_pressure("skill", "72\n")
        agent = _agent("skill", self.clone)
        with patch.object(config_mod, "CONFIG_PATH", cfg):
            self._enforce({"skill": agent}, ["skill"])
        self.assertEqual(agent.intent, AgentState.INTENT_RESTARTING)


class WiringAndDocs13335(unittest.TestCase):
    """TC-1 + TC-7 (mechanical half): wiring + doc-claim grep checks."""

    def test_tc1_enforcement_called_from_poll_loop(self):
        src = (REPO_ROOT / "references" / "scripts" / "harness.py").read_text(
            encoding="utf-8")
        poll = src.split("def _poll_loop", 1)[1].split("\n    def ", 1)[0]
        self.assertIn("self._enforce_context_pressure()", poll)
        self.assertIn("self.update_health()", poll)

    def test_tc1b_own_try_except_failopen_in_poll_loop(self):
        src = (REPO_ROOT / "references" / "scripts" / "harness.py").read_text(
            encoding="utf-8")
        poll = src.split("def _poll_loop", 1)[1].split("\n    def ", 1)[0]
        idx = poll.find("self._enforce_context_pressure()")
        window = poll[max(0, idx - 120):idx + 160]
        self.assertIn("try:", window)
        self.assertIn("except Exception", window)

    def test_tc7_event_mode_contract_names_real_actor(self):
        doc = (REPO_ROOT / "references" / "sub-skills" / "common-events" /
               "event-mode-contract.md").read_text(encoding="utf-8")
        self.assertIn("harness health poller", doc)
        self.assertIn("context-threshold", doc)
        self.assertNotIn(
            "the harness initiates a restart via the `restarting` intent — "
            "the same intent-driven path as `stop-requested` above; **no "
            "`stop-requested` event is emitted**. Honor it at a task "
            "boundary: checkpoint and halt; the 60s force-kill net "
            "terminates the process (you cannot self-`/quit`).", doc,
            msg="old fictional-claim wording should be gone")

    def test_tc7_context_pressure_doc_separates_modes(self):
        doc = (REPO_ROOT / "references" / "sub-skills" / "common" /
               "context-pressure.md").read_text(encoding="utf-8")
        self.assertIn("Loop mode vs event mode", doc)
        self.assertIn("harness health poller", doc)
        self.assertIn("exit-42", doc)

    def test_tc8_regression_suite_exists_and_pins_the_bug(self):
        t = REPO_ROOT / "tests" / "test_13335_context_pressure_enforcement.py"
        self.assertTrue(t.exists())
        src = t.read_text(encoding="utf-8")
        self.assertIn("_enforce_context_pressure", src)
        self.assertIn("INTENT_RESTARTING", src)


if __name__ == "__main__":
    unittest.main()
