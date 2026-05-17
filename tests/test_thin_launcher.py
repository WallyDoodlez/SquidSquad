"""Tests for references/scripts/thin_launcher.py (#4966)."""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import thin_launcher


class TestPIDManagement:
    """Thin launcher PID file operations."""

    def test_write_pid(self, tmp_path):
        """Writes PID file atomically."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        thin_launcher._write_pid(str(tmp_path), "skill", 12345)
        pid_file = role_dir / ".claude-pid"
        assert pid_file.exists()
        assert pid_file.read_text(encoding="utf-8") == "12345"
        # .tmp should not remain
        assert not pid_file.with_suffix(".tmp").exists()

    def test_clear_pid(self, tmp_path):
        """Removes PID file on exit."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        pid_file = role_dir / ".claude-pid"
        pid_file.write_text("12345", encoding="utf-8")
        thin_launcher._clear_pid(str(tmp_path), "skill")
        assert not pid_file.exists()

    def test_clear_pid_missing(self, tmp_path):
        """No error when PID file doesn't exist."""
        thin_launcher._clear_pid(str(tmp_path), "skill")  # should not raise


class TestEffortLevel:
    """#5573: per-agent effort level from config."""

    def test_reads_effort_from_config(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="max"):
            result = thin_launcher._get_effort_level("pm")
            assert result == "max"

    def test_defaults_to_high(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value=None):
            result = thin_launcher._get_effort_level("skill")
            assert result == "high"

    def test_rejects_invalid_level(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="turbo"):
            result = thin_launcher._get_effort_level("pm")
            assert result == "high"

    def test_handles_config_failure(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=Exception("no config")):
            result = thin_launcher._get_effort_level("pm")
            assert result == "high"


class TestClaudeInvocation:
    """Verify claude CLI flags passed by thin launcher."""

    def test_strict_mcp_config_flag(self, tmp_path):
        """#8308: --strict-mcp-config prevents MCP plugins from crowding out built-in tools."""
        sqdir = tmp_path / ".squidsquad" / "skill"
        sqdir.mkdir(parents=True)
        captured_cmd = []

        def mock_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            proc = MagicMock()
            proc.pid = 99999
            proc.wait.return_value = 0
            return proc

        with patch("thin_launcher.subprocess.Popen", side_effect=mock_popen), \
             patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            thin_launcher.main()

        assert "--strict-mcp-config" in captured_cmd
        # Flag must appear before the prompt argument (positional)
        prompt_idx = captured_cmd.index("Boot. Begin your first Ralph Loop cycle now.")
        flag_idx = captured_cmd.index("--strict-mcp-config")
        assert flag_idx < prompt_idx

    def test_append_system_prompt_includes_role(self, tmp_path):
        """Agent role is passed via --append-system-prompt."""
        sqdir = tmp_path / ".squidsquad" / "skill"
        sqdir.mkdir(parents=True)
        captured_cmd = []

        def mock_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            proc = MagicMock()
            proc.pid = 99999
            proc.wait.return_value = 0
            return proc

        with patch("thin_launcher.subprocess.Popen", side_effect=mock_popen), \
             patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            thin_launcher.main()

        idx = captured_cmd.index("--append-system-prompt")
        assert captured_cmd[idx + 1] == "SQUIDSQUAD_ROLE=skill"


class TestThinLauncherBoot:
    """Thin launcher boot_remote integration."""

    def test_find_boot_script_prefers_thin_launcher(self, tmp_path):
        """boot_remote prefers thin launcher over wrapper scripts (#4966)."""
        import boot_remote

        # Create thin launcher
        scripts_dir = tmp_path / "references" / "scripts"
        scripts_dir.mkdir(parents=True)
        launcher = scripts_dir / "thin_launcher.py"
        launcher.write_text("# thin launcher")

        # Also create legacy wrapper
        sqdir = tmp_path / ".squidsquad"
        sqdir.mkdir()
        (sqdir / "start-skill.ps1").write_text("# legacy wrapper")

        path, script_type = boot_remote._find_boot_script(str(tmp_path), "skill")
        assert script_type == "thin"
        assert "thin_launcher" in str(path)
