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
