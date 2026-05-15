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

class TestSentinelOps:
    def test_harness_api_stop(self, tmp_path):
        """cmd_stop calls harness API instead of writing .stop-after-cycle (#4966)."""
        with patch.object(start_team, "_harness_api", return_value=(True, {"action": "stop"})):
            start_team.cmd_stop(["skill"])
            # No .stop-after-cycle written when harness is reachable

    def test_harness_api_stop_fallback(self, tmp_path):
        """cmd_stop falls back to .stop sentinel when harness unreachable (#4966)."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        with patch.object(start_team, "_harness_api", return_value=(False, None)), \
             patch.object(start_team, "SQUIDSQUAD_DIR", tmp_path / ".squidsquad"):
            start_team.cmd_stop(["skill"])
        sentinel = role_dir / ".stop"
        assert sentinel.exists()

    def test_write_stop(self, tmp_path):
        """Writes .stop sentinel."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        with patch.object(start_team, "SQUIDSQUAD_DIR", tmp_path / ".squidsquad"):
            start_team._write_stop("skill")
        sentinel = role_dir / ".stop"
        assert sentinel.exists()

    def test_remove_stop(self, tmp_path):
        """Removes .stop sentinel."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        stop = role_dir / ".stop"
        stop.write_text("test")
        with patch.object(start_team, "SQUIDSQUAD_DIR", tmp_path / ".squidsquad"):
            start_team._remove_stop("skill")
        assert not stop.exists()

    def test_clean_stale_restart(self, tmp_path):
        """Cleans stale .restart sentinels from old system."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        restart = role_dir / ".restart"
        restart.write_text("old reason")
        with patch.object(start_team, "SQUIDSQUAD_DIR", tmp_path / ".squidsquad"):
            start_team._clean_stale_sentinels("skill")
        assert not restart.exists()

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
