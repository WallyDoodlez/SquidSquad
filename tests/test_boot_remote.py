"""Tests for references/scripts/boot_remote.py — .health-based agent boot detection."""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import boot_remote


class TestReadPidFile:
    def test_reads_valid_pid(self, tmp_path):
        pid_file = tmp_path / ".squidsquad" / "skill" / ".pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("12345")
        result = boot_remote._read_pid_file(tmp_path, "skill")
        assert result == 12345

    def test_missing_file_returns_none(self, tmp_path):
        result = boot_remote._read_pid_file(tmp_path, "skill")
        assert result is None

    def test_empty_file_returns_none(self, tmp_path):
        pid_file = tmp_path / ".squidsquad" / "skill" / ".pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("")
        result = boot_remote._read_pid_file(tmp_path, "skill")
        assert result is None

    def test_invalid_content_returns_none(self, tmp_path):
        pid_file = tmp_path / ".squidsquad" / "skill" / ".pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("not-a-pid")
        result = boot_remote._read_pid_file(tmp_path, "skill")
        assert result is None


class TestIsProcessAlive:
    def test_none_pid_is_not_alive(self):
        assert boot_remote._is_process_alive(None) is False

    def test_current_process_is_alive(self):
        assert boot_remote._is_process_alive(os.getpid()) is True

    def test_nonexistent_pid_is_not_alive(self):
        assert boot_remote._is_process_alive(99999999) is False


class TestReadHealthFile:
    def test_reads_alive(self, tmp_path):
        health_file = tmp_path / ".squidsquad" / "skill" / ".health"
        health_file.parent.mkdir(parents=True)
        health_file.write_text("alive")
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status == "alive"
        assert detail == ""

    def test_reads_error_with_detail(self, tmp_path):
        health_file = tmp_path / ".squidsquad" / "skill" / ".health"
        health_file.parent.mkdir(parents=True)
        health_file.write_text("error|gh auth failed")
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status == "error"
        assert detail == "gh auth failed"

    def test_missing_file_returns_none(self, tmp_path):
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status is None
        assert detail is None

    def test_empty_file_returns_none(self, tmp_path):
        health_file = tmp_path / ".squidsquad" / "skill" / ".health"
        health_file.parent.mkdir(parents=True)
        health_file.write_text("")
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status is None

    def test_reads_dead(self, tmp_path):
        health_file = tmp_path / ".squidsquad" / "skill" / ".health"
        health_file.parent.mkdir(parents=True)
        health_file.write_text("dead")
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status == "dead"

    def test_reads_backoff(self, tmp_path):
        health_file = tmp_path / ".squidsquad" / "skill" / ".health"
        health_file.parent.mkdir(parents=True)
        health_file.write_text("backoff")
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status == "backoff"


class TestNeedsBoot:
    @patch("boot_remote._get_clone_path")
    def test_stopped_agent_skipped(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        stop_file = tmp_path / ".squidsquad" / "skill" / ".stop"
        stop_file.parent.mkdir(parents=True)
        stop_file.write_text("")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert ".stop" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_alive_skips_boot(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("alive")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "alive" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_booting_skips_boot(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("booting")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "booting" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_restarting_skips_boot(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("restarting")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "restarting" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_backoff_skips_boot(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("backoff")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "backoff" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_dead_needs_boot(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("dead")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "dead" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_error_needs_boot(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("error|gh auth failed")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "error" in reason
        assert "gh auth failed" in reason

    @patch("boot_remote._get_clone_path")
    def test_no_health_no_pid_needs_boot(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        (tmp_path / ".squidsquad" / "skill").mkdir(parents=True)
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "no .health file" in reason
        assert "no PID" in reason

    @patch("boot_remote._is_process_alive", return_value=True)
    @patch("boot_remote._get_clone_path")
    def test_no_health_alive_pid_skips_boot(self, mock_clone, mock_alive, tmp_path):
        mock_clone.return_value = tmp_path
        pid_file = tmp_path / ".squidsquad" / "skill" / ".pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("12345")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "process alive" in reason

    @patch("boot_remote._is_process_alive", return_value=False)
    @patch("boot_remote._get_clone_path")
    def test_no_health_dead_pid_needs_boot(self, mock_clone, mock_alive, tmp_path):
        mock_clone.return_value = tmp_path
        pid_file = tmp_path / ".squidsquad" / "skill" / ".pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("99999")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "dead" in reason


class TestBootAgentCooldown:
    @patch("boot_remote._needs_boot", return_value=(True, "dead", "/tmp"))
    @patch("boot_remote._check_cooldown", return_value=(True, 300))
    def test_cooldown_skips_spawn(self, mock_cool, mock_needs):
        result = boot_remote.boot_agent("skill")
        assert result["action"] == "skip"
        assert "cooldown" in result["message"]
        assert result["success"] is True

    @patch("boot_remote._needs_boot", return_value=(False, ".health=alive (agent running)", "/tmp"))
    def test_alive_agent_skipped(self, mock_needs):
        result = boot_remote.boot_agent("skill")
        assert result["action"] == "skip"
        assert result["success"] is True


class TestGetAllRoles:
    @patch("boot_remote._parse_dev_agents", return_value=["skill"])
    def test_reads_from_config_md_only(self, mock_devs):
        """_get_all_roles should only read config.md, not scan directories (#943)."""
        with patch.object(boot_remote, "CONFIG_MD", Path("/nonexistent")):
            roles = boot_remote._get_all_roles()
            assert "pm" not in roles
            assert "skill" in roles

    @patch("boot_remote._parse_dev_agents", return_value=["skill", "wizard"])
    def test_includes_wizard_if_in_config(self, mock_devs):
        """If config.md lists wizard, it should be included (config is truth)."""
        with patch.object(boot_remote, "CONFIG_MD", Path("/nonexistent")):
            roles = boot_remote._get_all_roles()
            assert "wizard" in roles

    @patch("boot_remote._parse_dev_agents", return_value=["skill"])
    def test_does_not_scan_directories(self, mock_devs, tmp_path):
        """Even if qa/ directory exists, don't add it unless config says so."""
        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        (squid / "qa").mkdir()
        config = squid / "config.md"
        config.write_text("# Config\n- **Dev Agents**: skill\n")
        with patch.object(boot_remote, "SQUIDSQUAD_DIR", squid):
            with patch.object(boot_remote, "CONFIG_MD", config):
                roles = boot_remote._get_all_roles()
                # qa should be included because "QA: always present" check
                # but not from directory scanning

    @patch("boot_remote._parse_dev_agents", return_value=["skill"])
    def test_dm_included_if_config_says_present(self, mock_devs, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("- **DM**: present\n- **QA**: always present\n")
        with patch.object(boot_remote, "CONFIG_MD", config):
            roles = boot_remote._get_all_roles()
            assert "dm" in roles
            assert "qa" in roles
