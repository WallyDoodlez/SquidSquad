"""Tests for references/scripts/start_team.py — unified agent lifecycle."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import start_team


# ---------------------------------------------------------------------------
# Sentinel operations
# ---------------------------------------------------------------------------

class TestSentinelOpsRemoved:
    """#4792: `.stop` sentinel mechanism removed. cmd_stop now uses harness
    API only; no file-based fallback. _write_stop / _remove_stop /
    _clean_stale_sentinels were deleted from start_team.py."""

    def test_cmd_stop_uses_harness_api(self):
        with patch.object(start_team, "_harness_api", return_value=(True, {"action": "stop"})) as api:
            ok = start_team.cmd_stop(["skill"])
        assert ok is True
        api.assert_called_with("POST", "/agents/skill/stop")

    def test_cmd_stop_returns_false_when_harness_unreachable(self, tmp_path, capsys):
        """No `.stop` fallback — stop fails clean instead of writing a
        sentinel that survives the harness restart and causes split-brain."""
        with patch.object(start_team, "_harness_api", return_value=(False, None)), \
             patch.object(start_team, "SQUIDSQUAD_DIR", tmp_path / ".squidsquad"):
            ok = start_team.cmd_stop(["skill"])
        assert ok is False
        # No `.stop` file written anywhere
        assert not any((tmp_path / ".squidsquad").rglob(".stop"))
        out = capsys.readouterr().out
        assert "Harness unreachable" in out
        assert ".stop" not in out  # no mention of the deprecated mechanism

    def test_deprecated_helpers_are_gone(self):
        for name in ("_write_stop", "_remove_stop", "_clean_stale_sentinels"):
            assert not hasattr(start_team, name), (
                f"start_team.{name} should be removed in #4792"
            )

    def test_is_agent_idle_when_idle(self, tmp_path):
        """Agent is idle when current-state starts with 'idle'."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        (role_dir / "current-state").write_text("idle|")
        with patch.object(start_team, "SQUIDSQUAD_DIR", tmp_path / ".squidsquad"):
            assert start_team._is_agent_idle("skill") is True

    def test_is_agent_not_idle_when_working(self, tmp_path):
        """Agent is not idle when current-state shows work."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        (role_dir / "current-state").write_text("implementing|dev-agent -- #42")
        with patch.object(start_team, "SQUIDSQUAD_DIR", tmp_path / ".squidsquad"):
            assert start_team._is_agent_idle("skill") is False


# ---------------------------------------------------------------------------
# CLI parsing
# ---------------------------------------------------------------------------

class TestCLIParsing:
    def test_all_flag_defaults_to_boot(self):
        """--all without action defaults to boot."""
        with patch.object(sys, "argv", ["start_team.py", "--all"]):
            with patch.object(start_team, "cmd_boot", return_value=True) as mock_boot:
                with patch.object(start_team, "_get_all_roles", return_value=["pm", "skill"]):
                    start_team.main()
                    mock_boot.assert_called_once_with(["pm", "skill"])

    def test_reboot_single_role(self):
        """--reboot skill triggers reboot for skill only."""
        with patch.object(sys, "argv", ["start_team.py", "--reboot", "skill"]):
            with patch.object(start_team, "cmd_reboot", return_value=True) as mock_reboot:
                with patch.object(start_team, "_get_all_roles", return_value=["pm", "skill"]):
                    start_team.main()
                    mock_reboot.assert_called_once_with(["skill"], force=False)

    def test_stop_writes_sentinel(self):
        """--stop skill triggers stop command."""
        with patch.object(sys, "argv", ["start_team.py", "--stop", "skill"]):
            with patch.object(start_team, "cmd_stop", return_value=True) as mock_stop:
                with patch.object(start_team, "_get_all_roles", return_value=["pm", "skill"]):
                    start_team.main()
                    mock_stop.assert_called_once_with(["skill"])


# ---------------------------------------------------------------------------
# Harness API (#4966)
# ---------------------------------------------------------------------------

class TestHarnessAPI:
    def test_discover_port_from_file(self, tmp_path):
        """Reads port from .harness-port file."""
        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        (squid / ".harness-port").write_text("9090", encoding="utf-8")
        with patch.object(start_team, "SQUIDSQUAD_DIR", squid):
            port = start_team._discover_harness_port()
        assert port == 9090

    def test_discover_port_default(self, tmp_path):
        """Falls back to 7373 when no .harness-port."""
        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        with patch.object(start_team, "SQUIDSQUAD_DIR", squid):
            port = start_team._discover_harness_port()
        assert port == 7373

    def test_cmd_reboot_uses_api(self):
        """cmd_reboot calls harness restart API (#4966)."""
        with patch.object(start_team, "_harness_api", return_value=(True, {"action": "restart"})) as mock_api, \
             patch.object(start_team.boot_remote, "_needs_boot", return_value=(False, "running", "/path")):
            start_team.cmd_reboot(["skill"])
            mock_api.assert_called_once_with("POST", "/agents/skill/restart")

    def test_no_bare_exception_in_kill_block(self):
        """#8234 regression: kill block must not catch bare Exception."""
        import inspect
        source = inspect.getsource(start_team.cmd_reboot)
        assert "(ImportError, Exception)" not in source
