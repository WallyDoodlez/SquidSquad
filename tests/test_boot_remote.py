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

    @patch("boot_remote._is_process_alive", return_value=True)
    @patch("boot_remote._get_clone_path")
    def test_health_alive_with_pid_alive_skips_boot(self, mock_clone, mock_alive, tmp_path):
        """PID is primary — .health=alive is informational. PID alive = skip."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("alive")
        (squid / ".pid").write_text("12345")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "process alive" in reason

    @patch("boot_remote._is_process_alive", return_value=False)
    @patch("boot_remote._get_clone_path")
    def test_health_alive_with_pid_dead_needs_boot(self, mock_clone, mock_alive, tmp_path):
        """PID is primary — .health=alive but PID dead = stale, needs boot."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("alive")
        (squid / ".pid").write_text("12345")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "process dead" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_alive_no_pid_needs_boot(self, mock_clone, tmp_path):
        """.health=alive but no PID file = can't verify, needs boot."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("alive")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "no PID file" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_booting_no_pid_needs_boot(self, mock_clone, tmp_path):
        """.health=booting but no PID file = can't verify, needs boot."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("booting")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "no PID file" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_restarting_no_pid_needs_boot(self, mock_clone, tmp_path):
        """.health=restarting but no PID file = can't verify, needs boot."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("restarting")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "no PID file" in reason

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
    def test_health_dead_no_pid_needs_boot(self, mock_clone, tmp_path):
        """.health=dead with no PID file — needs boot (no PID to verify)."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("dead")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "no PID file" in reason

    @patch("boot_remote._get_clone_path")
    def test_health_error_no_pid_needs_boot(self, mock_clone, tmp_path):
        """.health=error with no PID file — needs boot (no PID to verify)."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("error|gh auth failed")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "no PID file" in reason

    @patch("boot_remote._get_clone_path")
    def test_no_health_no_pid_needs_boot(self, mock_clone, tmp_path):
        """No .health, no .pid — agent not running, needs boot."""
        mock_clone.return_value = tmp_path
        (tmp_path / ".squidsquad" / "skill").mkdir(parents=True)
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "no PID file" in reason

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


# ---------------------------------------------------------------------------
# _acquire_lock / _release_lock
# ---------------------------------------------------------------------------

class TestLocking:
    def test_acquire_lock_creates_file(self, tmp_path):
        lock_file = tmp_path / "boot-lock"
        with patch.object(boot_remote, "BOOT_LOCK", lock_file):
            result = boot_remote._acquire_lock()
        assert result is True
        assert lock_file.exists()
        assert lock_file.read_text(encoding="utf-8") == str(os.getpid())

    def test_acquire_fails_when_locked(self, tmp_path):
        lock_file = tmp_path / "boot-lock"
        lock_file.write_text(str(os.getpid()), encoding="utf-8")
        with patch.object(boot_remote, "BOOT_LOCK", lock_file), \
             patch.object(boot_remote, "LOCK_TTL_SECONDS", 300):
            result = boot_remote._acquire_lock()
        assert result is False

    def test_acquire_cleans_stale_lock(self, tmp_path):
        lock_file = tmp_path / "boot-lock"
        lock_file.write_text("99999", encoding="utf-8")
        # Set mtime to be old
        old_time = time.time() - 600
        os.utime(lock_file, (old_time, old_time))
        with patch.object(boot_remote, "BOOT_LOCK", lock_file), \
             patch.object(boot_remote, "LOCK_TTL_SECONDS", 300):
            result = boot_remote._acquire_lock()
        assert result is True

    def test_release_lock_removes_file(self, tmp_path):
        lock_file = tmp_path / "boot-lock"
        lock_file.write_text("12345", encoding="utf-8")
        with patch.object(boot_remote, "BOOT_LOCK", lock_file):
            boot_remote._release_lock()
        assert not lock_file.exists()

    def test_release_lock_no_file_is_noop(self, tmp_path):
        lock_file = tmp_path / "nonexistent-lock"
        with patch.object(boot_remote, "BOOT_LOCK", lock_file):
            boot_remote._release_lock()  # should not raise


# ---------------------------------------------------------------------------
# _detect_os
# ---------------------------------------------------------------------------

class TestDetectOs:
    @patch("platform.system", return_value="Windows")
    def test_windows(self, mock_sys):
        assert boot_remote._detect_os() == "windows"

    @patch("platform.system", return_value="Darwin")
    def test_macos(self, mock_sys):
        assert boot_remote._detect_os() == "macos"

    @patch("platform.system", return_value="Linux")
    def test_linux(self, mock_sys):
        assert boot_remote._detect_os() == "linux"


# ---------------------------------------------------------------------------
# _find_boot_script
# ---------------------------------------------------------------------------

class TestFindBootScript:
    def test_finds_ps1_on_windows(self, tmp_path):
        sqdir = tmp_path / ".squidsquad"
        sqdir.mkdir()
        ps1 = sqdir / "start-skill.ps1"
        ps1.write_text("$Role = 'skill'")
        with patch.object(boot_remote, "_detect_os", return_value="windows"):
            path, script_type = boot_remote._find_boot_script(tmp_path, "skill")
        assert path == ps1
        assert script_type == "ps1"

    def test_finds_sh_on_linux(self, tmp_path):
        sqdir = tmp_path / ".squidsquad"
        sqdir.mkdir()
        sh = sqdir / "start-skill.sh"
        sh.write_text("#!/bin/bash\nROLE=skill")
        with patch.object(boot_remote, "_detect_os", return_value="linux"):
            path, script_type = boot_remote._find_boot_script(tmp_path, "skill")
        assert path == sh
        assert script_type == "sh"

    def test_returns_none_when_missing(self, tmp_path):
        sqdir = tmp_path / ".squidsquad"
        sqdir.mkdir()
        with patch.object(boot_remote, "_detect_os", return_value="windows"):
            path, script_type = boot_remote._find_boot_script(tmp_path, "skill")
        assert path is None
        assert script_type is None

    def test_fallback_to_sh_on_windows(self, tmp_path):
        sqdir = tmp_path / ".squidsquad"
        sqdir.mkdir()
        sh = sqdir / "start-skill.sh"
        sh.write_text("#!/bin/bash\nROLE=skill")
        with patch.object(boot_remote, "_detect_os", return_value="windows"):
            path, script_type = boot_remote._find_boot_script(tmp_path, "skill")
        assert path == sh
        assert script_type == "sh"


# ---------------------------------------------------------------------------
# _read_boot_log / _append_boot_log / _check_cooldown
# ---------------------------------------------------------------------------

class TestBootLog:
    def test_read_empty_log(self, tmp_path):
        with patch.object(boot_remote, "BOOT_LOG", tmp_path / "nonexistent.log"):
            result = boot_remote._read_boot_log()
        assert result == []

    def test_append_and_read(self, tmp_path):
        log_file = tmp_path / "boot.log"
        entry = {"role": "skill", "action": "spawn", "timestamp": time.time()}
        with patch.object(boot_remote, "BOOT_LOG", log_file):
            boot_remote._append_boot_log(entry)
            result = boot_remote._read_boot_log()
        assert len(result) == 1
        assert result[0]["role"] == "skill"

    def test_read_skips_invalid_json(self, tmp_path):
        log_file = tmp_path / "boot.log"
        log_file.write_text('{"valid": true}\nnot json\n{"also": "valid"}\n')
        with patch.object(boot_remote, "BOOT_LOG", log_file):
            result = boot_remote._read_boot_log()
        assert len(result) == 2

    def test_cooldown_active(self, tmp_path):
        log_file = tmp_path / "boot.log"
        entry = {"role": "skill", "action": "spawn", "timestamp": time.time()}
        log_file.write_text(json.dumps(entry) + "\n")
        with patch.object(boot_remote, "BOOT_LOG", log_file), \
             patch.object(boot_remote, "COOLDOWN_SECONDS", 600):
            in_cool, remaining = boot_remote._check_cooldown("skill")
        assert in_cool is True
        assert remaining > 0

    def test_cooldown_expired(self, tmp_path):
        log_file = tmp_path / "boot.log"
        entry = {"role": "skill", "action": "spawn", "timestamp": time.time() - 1200}
        log_file.write_text(json.dumps(entry) + "\n")
        with patch.object(boot_remote, "BOOT_LOG", log_file), \
             patch.object(boot_remote, "COOLDOWN_SECONDS", 600):
            in_cool, remaining = boot_remote._check_cooldown("skill")
        assert in_cool is False

    def test_cooldown_different_role(self, tmp_path):
        log_file = tmp_path / "boot.log"
        entry = {"role": "pm", "action": "spawn", "timestamp": time.time()}
        log_file.write_text(json.dumps(entry) + "\n")
        with patch.object(boot_remote, "BOOT_LOG", log_file), \
             patch.object(boot_remote, "COOLDOWN_SECONDS", 600):
            in_cool, _ = boot_remote._check_cooldown("skill")
        assert in_cool is False


# ---------------------------------------------------------------------------
# _poll_health_after_spawn
# ---------------------------------------------------------------------------

class TestPollHealthAfterSpawn:
    @patch("boot_remote._read_health_file", return_value=("alive", "ok"))
    @patch("time.sleep")
    def test_returns_true_on_alive(self, mock_sleep, mock_health, tmp_path):
        confirmed, status, msg = boot_remote._poll_health_after_spawn(tmp_path, "skill", timeout=10)
        assert confirmed is True
        assert status == "alive"

    @patch("boot_remote._read_health_file", return_value=("error", "crash on boot"))
    @patch("time.sleep")
    def test_returns_false_on_error(self, mock_sleep, mock_health, tmp_path):
        confirmed, status, msg = boot_remote._poll_health_after_spawn(tmp_path, "skill", timeout=10)
        assert confirmed is False
        assert status == "error"
        assert "crash on boot" in msg

    @patch("boot_remote._read_health_file", return_value=("booting", None))
    @patch("time.sleep")
    def test_timeout_while_booting_returns_true(self, mock_sleep, mock_health, tmp_path):
        confirmed, status, msg = boot_remote._poll_health_after_spawn(tmp_path, "skill", timeout=2)
        assert confirmed is True
        assert status == "booting"

    @patch("boot_remote._read_health_file", return_value=(None, None))
    @patch("time.sleep")
    def test_timeout_unknown_returns_true(self, mock_sleep, mock_health, tmp_path):
        confirmed, status, msg = boot_remote._poll_health_after_spawn(tmp_path, "skill", timeout=2)
        assert confirmed is True
        assert "timed out" in msg


# ---------------------------------------------------------------------------
# _spawn_terminal (mock subprocess)
# ---------------------------------------------------------------------------

class TestSpawnTerminal:
    @patch("boot_remote._detect_os", return_value="windows")
    @patch("boot_remote._spawn_windows", return_value=(True, "spawned"))
    def test_routes_to_windows(self, mock_spawn, mock_os, tmp_path):
        success, msg = boot_remote._spawn_terminal(tmp_path, "skill", tmp_path / "start.ps1", "ps1")
        mock_spawn.assert_called_once()
        assert success is True

    @patch("boot_remote._detect_os", return_value="macos")
    @patch("boot_remote._spawn_macos", return_value=(True, "spawned"))
    def test_routes_to_macos(self, mock_spawn, mock_os, tmp_path):
        success, msg = boot_remote._spawn_terminal(tmp_path, "skill", tmp_path / "start.sh", "sh")
        mock_spawn.assert_called_once()
        assert success is True
