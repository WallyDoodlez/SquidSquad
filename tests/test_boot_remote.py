"""Tests for references/scripts/boot_remote.py — PID-based agent boot detection."""

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
    def test_no_pid_needs_boot(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        (tmp_path / ".squidsquad" / "skill").mkdir(parents=True)
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "no PID" in reason

    @patch("boot_remote._is_process_alive", return_value=True)
    @patch("boot_remote._get_clone_path")
    def test_alive_process_skipped(self, mock_clone, mock_alive, tmp_path):
        mock_clone.return_value = tmp_path
        pid_file = tmp_path / ".squidsquad" / "skill" / ".pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("12345")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "alive" in reason

    @patch("boot_remote._is_process_alive", return_value=False)
    @patch("boot_remote._get_clone_path")
    def test_dead_process_needs_boot(self, mock_clone, mock_alive, tmp_path):
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

    @patch("boot_remote._needs_boot", return_value=(False, "alive (PID 123)", "/tmp"))
    def test_alive_agent_skipped(self, mock_needs):
        result = boot_remote.boot_agent("skill")
        assert result["action"] == "skip"
        assert result["success"] is True


class TestGetAllRoles:
    @patch("boot_remote._parse_dev_agents", return_value=["skill", "qa"])
    @patch("boot_remote._parse_local_config", return_value={"skill": Path("/tmp")})
    def test_excludes_pm(self, mock_local, mock_devs):
        with patch.object(boot_remote, "SQUIDSQUAD_DIR", Path("/nonexistent")):
            roles = boot_remote._get_all_roles()
            assert "pm" not in roles
            assert "skill" in roles
            assert "qa" in roles
