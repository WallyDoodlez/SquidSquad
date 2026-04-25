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


class TestParseLocalConfigPriority:
    """Regression tests for #2750 — .local-config must win over ~/.squidsquad/clones/."""

    def test_local_config_wins_over_global_clones(self, tmp_path):
        """When both sources exist, .local-config (project-scoped) takes priority."""
        correct_path = tmp_path / "correct" / "project" / "skill"
        wrong_path = tmp_path / "wrong" / "project" / "skill"

        config = tmp_path / ".local-config"
        config.write_text(f"- **skill**: {correct_path}\n")

        global_clones = tmp_path / "fakehome" / ".squidsquad" / "clones"
        global_clones.mkdir(parents=True)
        (global_clones / "skill").write_text(f"{wrong_path}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config), \
             patch.object(boot_remote.Path, "home", return_value=tmp_path / "fakehome"):
            result = boot_remote._parse_local_config()

        assert result["skill"] == correct_path

    def test_global_clones_used_as_fallback(self, tmp_path):
        """When .local-config is missing, fall back to ~/.squidsquad/clones/."""
        fallback_path = tmp_path / "fallback" / "path"

        global_clones = tmp_path / "fakehome" / ".squidsquad" / "clones"
        global_clones.mkdir(parents=True)
        (global_clones / "skill").write_text(f"{fallback_path}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", tmp_path / "missing"), \
             patch.object(boot_remote.Path, "home", return_value=tmp_path / "fakehome"):
            result = boot_remote._parse_local_config()

        assert result["skill"] == fallback_path

    def test_empty_local_config_falls_through(self, tmp_path):
        """When .local-config exists but has no valid entries, use global."""
        config = tmp_path / ".local-config"
        config.write_text("# comment only\n")

        global_qa = tmp_path / "global" / "qa"
        global_clones = tmp_path / "fakehome" / ".squidsquad" / "clones"
        global_clones.mkdir(parents=True)
        (global_clones / "qa").write_text(f"{global_qa}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config), \
             patch.object(boot_remote.Path, "home", return_value=tmp_path / "fakehome"):
            result = boot_remote._parse_local_config()

        assert result["qa"] == global_qa

    def test_cross_project_isolation(self, tmp_path):
        """Core regression: global clones from project B don't leak into project A."""
        projectA_skill = tmp_path / "projectA" / "skill"
        projectB_main = tmp_path / "projectB" / "main"
        projectB_designer = tmp_path / "projectB" / "designer"
        projectB_skill = tmp_path / "projectB" / "skill"

        config = tmp_path / ".local-config"
        config.write_text(f"- **skill**: {projectA_skill}\n")

        global_clones = tmp_path / "fakehome" / ".squidsquad" / "clones"
        global_clones.mkdir(parents=True)
        (global_clones / "pm").write_text(f"{projectB_main}\n")
        (global_clones / "designer").write_text(f"{projectB_designer}\n")
        (global_clones / "skill").write_text(f"{projectB_skill}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config), \
             patch.object(boot_remote.Path, "home", return_value=tmp_path / "fakehome"):
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


class TestGetAllRoles:
    @patch("boot_remote._parse_dev_agents", return_value=["skill", "qa"])
    @patch("boot_remote._parse_local_config", return_value={"skill": Path("/tmp")})
    def test_excludes_pm(self, mock_local, mock_devs):
        with patch.object(boot_remote, "SQUIDSQUAD_DIR", Path("/nonexistent")):
            roles = boot_remote._get_all_roles()
            assert "pm" not in roles
            assert "skill" in roles
            assert "qa" in roles
