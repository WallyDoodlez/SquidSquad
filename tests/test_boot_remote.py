"""Tests for references/scripts/boot_remote.py — PID tracking, grace period, kill-before-spawn."""

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
        # PID 99999999 is very unlikely to exist
        assert boot_remote._is_process_alive(99999999) is False


class TestCheckGracePeriod:
    @patch("boot_remote._read_boot_log")
    def test_no_entries_no_grace(self, mock_log):
        mock_log.return_value = []
        in_grace, remaining = boot_remote._check_grace_period("skill")
        assert in_grace is False

    @patch("boot_remote._read_boot_log")
    def test_recent_spawn_in_grace(self, mock_log):
        mock_log.return_value = [
            {"role": "skill", "action": "spawn", "success": True,
             "timestamp": time.time() - 30}  # 30s ago
        ]
        in_grace, remaining = boot_remote._check_grace_period("skill")
        assert in_grace is True
        assert remaining > 0

    @patch("boot_remote._read_boot_log")
    def test_old_spawn_not_in_grace(self, mock_log):
        mock_log.return_value = [
            {"role": "skill", "action": "spawn", "success": True,
             "timestamp": time.time() - 300}  # 5 min ago
        ]
        in_grace, remaining = boot_remote._check_grace_period("skill")
        assert in_grace is False

    @patch("boot_remote._read_boot_log")
    def test_failed_spawn_not_in_grace(self, mock_log):
        mock_log.return_value = [
            {"role": "skill", "action": "spawn", "success": False,
             "timestamp": time.time() - 30}  # 30s ago but failed
        ]
        in_grace, remaining = boot_remote._check_grace_period("skill")
        assert in_grace is False

    @patch("boot_remote._read_boot_log")
    def test_different_role_not_in_grace(self, mock_log):
        mock_log.return_value = [
            {"role": "pm", "action": "spawn", "success": True,
             "timestamp": time.time() - 30}
        ]
        in_grace, remaining = boot_remote._check_grace_period("skill")
        assert in_grace is False


class TestCheckAndKillExisting:
    def test_no_pid_file(self, tmp_path):
        killed, msg = boot_remote._check_and_kill_existing(tmp_path, "skill")
        assert killed is False
        assert "no PID file" in msg

    def test_stale_pid_cleaned_up(self, tmp_path):
        pid_file = tmp_path / ".squidsquad" / "skill" / ".pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("99999999")  # non-existent PID
        killed, msg = boot_remote._check_and_kill_existing(tmp_path, "skill")
        assert killed is False
        assert "stale PID" in msg
        assert not pid_file.exists()

    @patch("boot_remote._is_process_alive", return_value=True)
    @patch("boot_remote._kill_process", return_value=(True, "killed PID 123"))
    def test_alive_process_killed(self, mock_kill, mock_alive, tmp_path):
        pid_file = tmp_path / ".squidsquad" / "skill" / ".pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("123")
        killed, msg = boot_remote._check_and_kill_existing(tmp_path, "skill")
        assert killed is True
        assert "killed" in msg
        mock_kill.assert_called_once_with(123)


class TestBootAgentGracePeriod:
    """Integration: boot_agent skips when grace period is active."""

    @patch("boot_remote._run_health_check")
    @patch("boot_remote._check_grace_period", return_value=(True, 90))
    def test_grace_period_skips_spawn(self, mock_grace, mock_health):
        mock_health.return_value = {
            "agents": [{"role": "skill", "health": "stalled", "reason": "no update"}]
        }
        result = boot_remote.boot_agent("skill")
        assert result["action"] == "skip"
        assert "grace period" in result["message"]
        assert result["success"] is True
