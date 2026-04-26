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


class TestGetAllRoles:
    @patch("boot_remote._parse_dev_agents", return_value=["skill", "qa"])
    @patch("boot_remote._parse_local_config", return_value={"skill": Path("/tmp")})
    def test_excludes_pm(self, mock_local, mock_devs):
        with patch.object(boot_remote, "SQUIDSQUAD_DIR", Path("/nonexistent")):
            roles = boot_remote._get_all_roles()
            assert "pm" not in roles
            assert "skill" in roles
            assert "qa" in roles
