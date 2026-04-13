"""Tests for references/scripts/add_role.py — mocked subprocess, no real git."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, mock_open

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import add_role


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


class TestValidateRole:
    @patch("add_role._get_configured_agents", return_value=["skill", "pm"])
    def test_configured_role_is_valid(self, mock_agents):
        assert add_role._validate_role("skill") is True

    @patch("add_role._get_configured_agents", return_value=["skill", "pm"])
    def test_unconfigured_role_with_template(self, mock_agents):
        # dev template exists as fallback
        assert add_role._validate_role("be") is True

    @patch("add_role._get_configured_agents", return_value=["skill", "pm"])
    @patch("add_role.REPO_ROOT", Path("/nonexistent"))
    def test_unknown_role_no_template(self, mock_agents):
        assert add_role._validate_role("nonexistent_role_xyz") is False


class TestParseLocalConfig:
    def test_parses_entries(self, tmp_path):
        config = tmp_path / ".local-config"
        config.write_text(
            "# comment\n\n- **pm**: /path/to/pm\n- **skill**: /path/to/skill\n"
        )
        result = add_role._parse_local_config(config)
        assert result == {"pm": "/path/to/pm", "skill": "/path/to/skill"}

    def test_missing_file_returns_empty(self, tmp_path):
        result = add_role._parse_local_config(tmp_path / "missing")
        assert result == {}


class TestWriteLocalConfig:
    def test_writes_sorted_entries(self, tmp_path):
        config = tmp_path / ".local-config"
        add_role._write_local_config({"skill": "/a", "pm": "/b"}, config)
        text = config.read_text()
        assert "- **pm**: /b" in text
        assert "- **skill**: /a" in text
        # pm should come before skill (sorted)
        assert text.index("pm") < text.index("skill")


class TestDryRun:
    @patch("add_role._validate_role", return_value=True)
    @patch("add_role._get_project_name", return_value="TestProject")
    def test_dry_run_makes_no_changes(self, mock_name, mock_valid, capsys):
        result = add_role.add_role("qa", dry_run=True)
        assert result == 0
        out = capsys.readouterr().out
        assert "[dry-run]" in out
        assert "Would clone" in out


class TestLockFile:
    def test_acquire_and_release(self, tmp_path):
        with patch.object(add_role, "LOCK_FILE", tmp_path / ".lock"):
            assert add_role._acquire_lock() is True
            assert (tmp_path / ".lock").exists()
            # Second acquire should fail
            assert add_role._acquire_lock() is False
            add_role._release_lock()
            assert not (tmp_path / ".lock").exists()


class TestRegisterExisting:
    def test_nonexistent_path_fails(self):
        result = add_role.register_existing("qa", "/nonexistent/path")
        assert result == 1

    def test_no_squidsquad_dir_fails(self, tmp_path):
        result = add_role.register_existing("qa", str(tmp_path))
        assert result == 1

    @patch("add_role._sync_local_config")
    @patch("add_role._parse_local_config", return_value={})
    @patch("add_role._get_configured_agents", return_value=["pm"])
    def test_valid_clone_registers(self, mock_agents, mock_parse, mock_sync, tmp_path):
        (tmp_path / ".squidsquad").mkdir()
        result = add_role.register_existing("qa", str(tmp_path))
        assert result == 0
        mock_sync.assert_called_once()
