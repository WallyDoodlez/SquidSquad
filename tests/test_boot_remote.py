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


class TestParseLocalConfigMandatory:
    """Tests for #3100 — .local-config is mandatory, no global fallback."""

    def test_valid_local_config_parses(self, tmp_path):
        """When .local-config exists with valid entries, parse them."""
        skill_path = tmp_path / "project" / "skill"
        config = tmp_path / ".local-config"
        config.write_text(f"- **skill**: {skill_path}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config):
            result = boot_remote._parse_local_config()

        assert result["skill"] == skill_path

    def test_missing_local_config_exits(self, tmp_path):
        """When .local-config is missing, exit with code 2 and clear error."""
        with patch.object(boot_remote, "LOCAL_CONFIG", tmp_path / "missing"):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_empty_local_config_exits(self, tmp_path):
        """When .local-config exists but has no valid entries, exit with code 2."""
        config = tmp_path / ".local-config"
        config.write_text("# comment only\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_no_global_clones_fallback(self, tmp_path):
        """Global ~/.squidsquad/clones/ is never used, even if it exists (#3100)."""
        global_clones = tmp_path / "fakehome" / ".squidsquad" / "clones"
        global_clones.mkdir(parents=True)
        (global_clones / "skill").write_text(f"{tmp_path / 'fallback'}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", tmp_path / "missing"):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_cross_project_isolation(self, tmp_path):
        """Only .local-config entries are returned — no global leakage (#2750, #3100)."""
        projectA_skill = tmp_path / "projectA" / "skill"

        config = tmp_path / ".local-config"
        config.write_text(f"- **skill**: {projectA_skill}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config):
            result = boot_remote._parse_local_config()

        assert result["skill"] == projectA_skill
        assert "pm" not in result
        assert "designer" not in result


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


class TestBootAgentSkip:
    @patch("boot_remote._needs_boot", return_value=(False, "alive (PID 123)", "/tmp"))
    def test_alive_agent_skipped(self, mock_needs):
        result = boot_remote.boot_agent("skill")
        assert result["action"] == "skip"
        assert result["success"] is True


# ---------------------------------------------------------------------------
# #3348 regression: heartbeat epoch parsing + UTF-16 PID file
# ---------------------------------------------------------------------------

class TestReadHealthFileHeartbeat:
    def test_detects_epoch_as_heartbeat(self, tmp_path):
        """Numeric-only .health content is detected as heartbeat epoch."""
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("1777205526", encoding="utf-8")
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status == "heartbeat"
        assert detail == "1777205526"

    def test_legacy_status_still_works(self, tmp_path):
        """Legacy status|detail format still parses correctly."""
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("alive|PID 1234", encoding="utf-8")
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status == "alive"
        assert detail == "PID 1234"

    def test_short_number_not_epoch(self, tmp_path):
        """Short numeric strings (< 10 digits) are not treated as epochs."""
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("12345", encoding="utf-8")
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status == "12345"  # Treated as legacy status, not heartbeat

    def test_empty_file_returns_none(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".health").write_text("", encoding="utf-8")
        status, detail = boot_remote._read_health_file(tmp_path, "skill")
        assert status is None


class TestNeedsBootHeartbeat:
    @patch("boot_remote._get_clone_path")
    def test_recent_heartbeat_is_alive(self, mock_clone, tmp_path):
        """Recent heartbeat epoch (within 15s) means agent is alive."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        # Write current epoch
        (squid / ".health").write_text(str(int(time.time())), encoding="utf-8")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "alive" in reason

    @patch("boot_remote._get_clone_path")
    def test_stale_heartbeat_needs_boot(self, mock_clone, tmp_path):
        """Stale heartbeat epoch (older than 15s) means agent is dead."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        # Write epoch from 60s ago
        (squid / ".health").write_text(str(int(time.time()) - 60), encoding="utf-8")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "stale" in reason


class TestReadPidFileUtf16:
    def test_reads_utf16_le_pid(self, tmp_path):
        """PID file written by PowerShell (UTF-16 LE with BOM) is parsed correctly."""
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        # Write PID as UTF-16 LE with BOM (PowerShell default)
        pid_content = "12345\r\n"
        (squid / ".pid").write_bytes(b"\xff\xfe" + pid_content.encode("utf-16-le"))
        result = boot_remote._read_pid_file(tmp_path, "skill")
        assert result == 12345

    def test_reads_utf8_pid(self, tmp_path):
        """PID file written as plain UTF-8 still works."""
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".pid").write_text("67890\n", encoding="utf-8")
        result = boot_remote._read_pid_file(tmp_path, "skill")
        assert result == 67890


# ---------------------------------------------------------------------------
# #3347 regression: inter-process boot lock (.booting sentinel)
# ---------------------------------------------------------------------------

class TestBootingSentinel:
    def test_no_sentinel_returns_false(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        assert boot_remote._has_booting_sentinel(tmp_path, "skill") is False

    def test_recent_sentinel_returns_true(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".booting").write_text(str(os.getpid()), encoding="utf-8")
        assert boot_remote._has_booting_sentinel(tmp_path, "skill") is True

    def test_stale_sentinel_returns_false(self, tmp_path):
        """Sentinel older than TTL is treated as stale and cleaned up."""
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        booting = squid / ".booting"
        booting.write_text("99999", encoding="utf-8")
        # Backdate mtime
        old_time = time.time() - boot_remote.BOOTING_SENTINEL_TTL - 10
        os.utime(booting, (old_time, old_time))
        assert boot_remote._has_booting_sentinel(tmp_path, "skill") is False
        assert not booting.exists()  # Stale sentinel was cleaned up

    def test_write_sentinel_succeeds(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        assert boot_remote._write_booting_sentinel(tmp_path, "skill") is True
        assert (squid / ".booting").exists()

    def test_write_sentinel_blocked_by_existing(self, tmp_path):
        """Second write fails if recent sentinel exists."""
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".booting").write_text(str(os.getpid()), encoding="utf-8")
        assert boot_remote._write_booting_sentinel(tmp_path, "skill") is False

    def test_clear_sentinel(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".booting").write_text("123", encoding="utf-8")
        boot_remote._clear_booting_sentinel(tmp_path, "skill")
        assert not (squid / ".booting").exists()


class TestNeedsBootWithSentinel:
    @patch("boot_remote._get_clone_path")
    def test_booting_sentinel_prevents_boot(self, mock_clone, tmp_path):
        """Active .booting sentinel means boot already in progress — skip."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".booting").write_text(str(os.getpid()), encoding="utf-8")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "boot already in progress" in reason


class TestBootAgentLock:
    @patch("boot_remote._spawn_terminal", return_value=(True, "spawned"))
    @patch("boot_remote._find_boot_script", return_value=(Path("/tmp/start.sh"), "sh"))
    @patch("boot_remote._needs_boot", return_value=(True, "dead", "/tmp/clone"))
    def test_writes_sentinel_before_spawn(self, mock_needs, mock_script, mock_spawn, tmp_path):
        """boot_agent writes .booting sentinel before spawning."""
        with patch("boot_remote._write_booting_sentinel", return_value=True) as mock_write, \
             patch("boot_remote._clear_booting_sentinel") as mock_clear:
            result = boot_remote.boot_agent("skill")
        assert result["action"] == "spawn"
        assert result["success"] is True
        mock_write.assert_called_once()
        mock_clear.assert_not_called()  # Cleared by wrapper, not boot_remote on success

    @patch("boot_remote._spawn_terminal", return_value=(False, "failed"))
    @patch("boot_remote._find_boot_script", return_value=(Path("/tmp/start.sh"), "sh"))
    @patch("boot_remote._needs_boot", return_value=(True, "dead", "/tmp/clone"))
    def test_clears_sentinel_on_spawn_failure(self, mock_needs, mock_script, mock_spawn, tmp_path):
        """boot_agent clears .booting sentinel when spawn fails."""
        with patch("boot_remote._write_booting_sentinel", return_value=True) as mock_write, \
             patch("boot_remote._clear_booting_sentinel") as mock_clear:
            result = boot_remote.boot_agent("skill")
        assert result["success"] is False
        mock_clear.assert_called_once()

    @patch("boot_remote._find_boot_script", return_value=(Path("/tmp/start.sh"), "sh"))
    @patch("boot_remote._needs_boot", return_value=(True, "dead", "/tmp/clone"))
    def test_skips_if_sentinel_blocked(self, mock_needs, mock_script):
        """boot_agent skips if another boot is in progress."""
        with patch("boot_remote._write_booting_sentinel", return_value=False):
            result = boot_remote.boot_agent("skill")
        assert result["action"] == "skip"
        assert "another boot in progress" in result["message"]


# ---------------------------------------------------------------------------
# #3349 regression: stale .restart sentinel cleanup
# ---------------------------------------------------------------------------

class TestCleanStaleRestart:
    def test_removes_existing_restart(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        restart = squid / ".restart"
        restart.write_text("reboot requested by reboot_agent.py", encoding="utf-8")
        boot_remote._clean_stale_restart(tmp_path, "skill")
        assert not restart.exists()

    def test_no_restart_is_noop(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        boot_remote._clean_stale_restart(tmp_path, "skill")  # Should not raise


class TestBootAgentCleansRestart:
    @patch("boot_remote._spawn_terminal", return_value=(True, "spawned"))
    @patch("boot_remote._find_boot_script", return_value=(Path("/tmp/start.sh"), "sh"))
    @patch("boot_remote._needs_boot", return_value=(True, "dead", "/tmp/clone"))
    @patch("boot_remote._write_booting_sentinel", return_value=True)
    def test_cleans_restart_before_spawn(self, mock_sentinel, mock_needs, mock_script, mock_spawn):
        """boot_agent cleans stale .restart before spawning."""
        with patch("boot_remote._clean_stale_restart") as mock_clean:
            result = boot_remote.boot_agent("skill")
        assert result["action"] == "spawn"
        mock_clean.assert_called_once_with("/tmp/clone", "skill")


class TestGetAllRoles:
    @patch("boot_remote._parse_dev_agents", return_value=["skill", "qa"])
    @patch("boot_remote._parse_local_config", return_value={"skill": Path("/tmp")})
    def test_includes_pm_from_config(self, mock_local, mock_devs, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("- **PM**: always present\n- **DM**: present\n")
        squid_dir = tmp_path
        with patch.object(boot_remote, "SQUIDSQUAD_DIR", squid_dir), \
             patch.object(boot_remote, "CONFIG_MD", config):
            roles = boot_remote._get_all_roles()
            assert "pm" in roles
            assert "skill" in roles
            assert "qa" in roles
            assert "dm" in roles

    @patch("boot_remote._parse_dev_agents", return_value=["skill", "qa"])
    @patch("boot_remote._parse_local_config", return_value={"skill": Path("/tmp")})
    def test_excludes_pm_when_not_in_config(self, mock_local, mock_devs):
        with patch.object(boot_remote, "SQUIDSQUAD_DIR", Path("/nonexistent")):
            roles = boot_remote._get_all_roles()
            assert "pm" not in roles
            assert "skill" in roles
            assert "qa" in roles
