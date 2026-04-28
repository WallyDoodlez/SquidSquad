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
    def test_write_stop_after_cycle(self, tmp_path):
        """Writes .stop-after-cycle sentinel."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        with patch.object(start_team, "SQUIDSQUAD_DIR", tmp_path / ".squidsquad"):
            start_team._write_stop_after_cycle("skill", "test reboot")
        sentinel = role_dir / ".stop-after-cycle"
        assert sentinel.exists()
        assert "test reboot" in sentinel.read_text(encoding="utf-8")

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
