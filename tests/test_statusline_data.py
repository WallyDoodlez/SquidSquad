"""Tests for references/scripts/statusline_data.py (#8700)."""

import sys
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import statusline_data


class TestGetWakeMode:
    """#9745: statusline_data._get_wake_mode delegates to config.get_wake_mode.

    Resolution semantics are covered exhaustively in
    tests/test_feat_9745_wake_mode_canonical.py::TestGetWakeMode. These tests
    only verify the statusline wrapper delegates correctly.
    """

    def test_delegates_to_canonical_helper(self):
        with patch("config.get_wake_mode", return_value="event-driven") as m:
            assert statusline_data._get_wake_mode("pm") == "event-driven"
            m.assert_called_once_with("pm")

    def test_falls_back_to_polling_on_import_failure(self):
        import sys as _sys
        with patch.dict(_sys.modules, {"config": None}):
            assert statusline_data._get_wake_mode("skill") == "polling"


class TestReadCurrentStateFile:
    def test_returns_first_line(self, tmp_path):
        (tmp_path / "skill").mkdir()
        (tmp_path / "skill" / "current-state").write_text(
            "triaging|tracker-protocol — Fixing #42\nsecond line ignored\n",
            encoding="utf-8",
        )
        with patch.object(statusline_data, "SQUID_DIR", tmp_path):
            assert statusline_data._read_current_state_file("skill") == \
                "triaging|tracker-protocol — Fixing #42"

    def test_missing_file_returns_empty(self, tmp_path):
        with patch.object(statusline_data, "SQUID_DIR", tmp_path):
            assert statusline_data._read_current_state_file("skill") == ""


class TestCmdPhasePolling:
    def test_returns_file_contents_in_polling_mode(self, tmp_path, capsys):
        (tmp_path / "skill").mkdir()
        (tmp_path / "skill" / "current-state").write_text(
            "implementing|dev-agent — #99", encoding="utf-8"
        )
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="polling"), \
             patch.object(statusline_data, "_harness_get") as mock_get:
            rc = statusline_data.cmd_phase("skill")
        assert rc == 0
        assert capsys.readouterr().out.strip() == "implementing|dev-agent — #99"
        # Polling mode must NOT call the harness API
        mock_get.assert_not_called()


class TestCmdPhaseEventDriven:
    def test_queries_agents_endpoint_not_health(self, tmp_path, capsys):
        """#8700 review fix R1+R2: pull phase from /agents/<role> (in-memory
        AgentState updated by phase-change events), not /agents/<role>/health
        which just re-reads the on-disk current-state file."""
        called = {}

        def fake_get(path):
            called["path"] = path
            return {"current_phase": "implementing", "intent": "running"}

        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get", side_effect=fake_get):
            statusline_data.cmd_phase("skill")
        assert called["path"] == "/agents/skill"
        assert capsys.readouterr().out.strip() == "implementing|"

    def test_surfaces_non_running_intent_when_phase_empty(self, tmp_path, capsys):
        """If the agent is stopping/restarting and has no phase, surface the intent."""
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get",
                          return_value={"current_phase": None, "intent": "stopping"}):
            statusline_data.cmd_phase("skill")
        assert capsys.readouterr().out.strip() == "stopping|"

    def test_phase_wins_over_intent(self, tmp_path, capsys):
        """When both phase and a non-running intent exist, phase is shown."""
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get",
                          return_value={"current_phase": "implementing",
                                        "intent": "restarting"}):
            statusline_data.cmd_phase("skill")
        assert capsys.readouterr().out.strip() == "implementing|"

    def test_running_intent_with_no_phase_does_not_surface(self, tmp_path, capsys):
        """The default running intent should not appear as a badge."""
        (tmp_path / "skill").mkdir()
        (tmp_path / "skill" / "current-state").write_text("idle|", encoding="utf-8")
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get",
                          return_value={"current_phase": None, "intent": "running"}):
            statusline_data.cmd_phase("skill")
        # No phase + intent=running → no harness phase emitted → falls
        # through to file.
        assert capsys.readouterr().out.strip() == "idle|"

    def test_falls_back_to_file_when_harness_unreachable(self, tmp_path, capsys):
        """Harness down → fall back to current-state file so the line doesn't go blank."""
        (tmp_path / "skill").mkdir()
        (tmp_path / "skill" / "current-state").write_text(
            "idle|", encoding="utf-8"
        )
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get", return_value=None):
            statusline_data.cmd_phase("skill")
        assert capsys.readouterr().out.strip() == "idle|"

    def test_no_state_anywhere_prints_nothing(self, tmp_path, capsys):
        with patch.object(statusline_data, "SQUID_DIR", tmp_path), \
             patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"), \
             patch.object(statusline_data, "_harness_get", return_value=None):
            statusline_data.cmd_phase("skill")
        assert capsys.readouterr().out == ""


class TestCmdMode:
    def test_prints_wake_mode(self, capsys):
        with patch.object(statusline_data, "_get_wake_mode", return_value="event-driven"):
            statusline_data.cmd_mode("skill")
        assert capsys.readouterr().out.strip() == "event-driven"


class TestHarnessPort:
    def test_reads_port_file(self, tmp_path):
        (tmp_path / ".harness-port").write_text("9090", encoding="utf-8")
        with patch.object(statusline_data, "PORT_FILE", tmp_path / ".harness-port"):
            assert statusline_data._harness_port() == 9090

    def test_falls_back_to_default(self, tmp_path):
        with patch.object(statusline_data, "PORT_FILE", tmp_path / "nope"):
            assert statusline_data._harness_port() == 7373

    def test_corrupt_port_file_falls_back(self, tmp_path):
        (tmp_path / ".harness-port").write_text("not-a-number", encoding="utf-8")
        with patch.object(statusline_data, "PORT_FILE", tmp_path / ".harness-port"):
            assert statusline_data._harness_port() == 7373


class TestCLI:
    def test_usage_error_on_missing_args(self, capsys):
        with patch.object(sys, "argv", ["statusline_data.py"]):
            rc = statusline_data.main()
        assert rc == 2

    def test_unknown_command(self, capsys):
        with patch.object(sys, "argv", ["statusline_data.py", "bogus", "skill"]):
            rc = statusline_data.main()
        assert rc == 2

    def test_phase_dispatches_to_cmd_phase(self, capsys):
        with patch.object(sys, "argv", ["statusline_data.py", "phase", "skill"]), \
             patch.object(statusline_data, "cmd_phase", return_value=0) as mock_cmd:
            rc = statusline_data.main()
        assert rc == 0
        mock_cmd.assert_called_once_with("skill")
