"""Regression tests for #1496 — boot_remote.py shared filesystem fallback.

Verifies that _parse_local_config reads clone paths from the shared filesystem
(~/.squidsquad/clones/) first, and falls back to .local-config (legacy format)
when the shared filesystem is not available or empty.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import boot_remote


class TestSharedFsFallback:
    """#1496: _parse_local_config must prefer shared FS, fall back to .local-config."""

    def test_shared_fs_takes_priority(self, tmp_path):
        """#1496: When ~/.squidsquad/clones/ has files, use those paths."""
        clones_dir = tmp_path / ".squidsquad" / "clones"
        clones_dir.mkdir(parents=True)
        (clones_dir / "skill").write_text("/home/user/skill-clone", encoding="utf-8")
        (clones_dir / "qa").write_text("/home/user/qa-clone", encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = boot_remote._parse_local_config()

        assert result["skill"] == Path("/home/user/skill-clone")
        assert result["qa"] == Path("/home/user/qa-clone")

    def test_falls_back_to_local_config(self, tmp_path):
        """#1496: When shared FS is absent, fall back to .local-config."""
        # No clones dir under home
        local_config = tmp_path / "local-config"
        local_config_content = (
            "- **skill**: /opt/squidsquad/skill\n"
            "- **qa**: /opt/squidsquad/qa\n"
        )
        local_config.write_text(local_config_content, encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path / "empty_home"), \
             patch.object(boot_remote, "LOCAL_CONFIG", local_config):
            result = boot_remote._parse_local_config()

        assert result["skill"] == Path("/opt/squidsquad/skill")
        assert result["qa"] == Path("/opt/squidsquad/qa")

    def test_empty_shared_fs_falls_back(self, tmp_path):
        """#1496: Empty clones dir (no files) should fall back to .local-config."""
        clones_dir = tmp_path / ".squidsquad" / "clones"
        clones_dir.mkdir(parents=True)
        # clones_dir exists but is empty

        local_config = tmp_path / "local-config"
        local_config.write_text("- **skill**: /fallback/path\n", encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path), \
             patch.object(boot_remote, "LOCAL_CONFIG", local_config):
            result = boot_remote._parse_local_config()

        assert result.get("skill") == Path("/fallback/path")

    def test_shared_fs_ignores_dotfiles(self, tmp_path):
        """#1496: Hidden files in clones/ should be ignored."""
        clones_dir = tmp_path / ".squidsquad" / "clones"
        clones_dir.mkdir(parents=True)
        (clones_dir / ".gitkeep").write_text("", encoding="utf-8")
        (clones_dir / "skill").write_text("/home/user/skill", encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = boot_remote._parse_local_config()

        assert ".gitkeep" not in result
        assert "skill" in result

    def test_shared_fs_skips_empty_content(self, tmp_path):
        """#1496: Clone files with empty content should be skipped."""
        clones_dir = tmp_path / ".squidsquad" / "clones"
        clones_dir.mkdir(parents=True)
        (clones_dir / "skill").write_text("", encoding="utf-8")
        (clones_dir / "qa").write_text("/valid/path", encoding="utf-8")

        with patch("pathlib.Path.home", return_value=tmp_path):
            result = boot_remote._parse_local_config()

        # skill has empty content, should be skipped
        assert "skill" not in result
        assert result["qa"] == Path("/valid/path")

    def test_no_config_returns_empty(self, tmp_path):
        """#1496: No shared FS and no .local-config returns empty dict."""
        with patch("pathlib.Path.home", return_value=tmp_path / "nowhere"), \
             patch.object(boot_remote, "LOCAL_CONFIG", tmp_path / "nonexistent"):
            result = boot_remote._parse_local_config()

        assert result == {}

    def test_get_clone_path_falls_back_to_repo_root(self):
        """#1496: _get_clone_path returns REPO_ROOT when role not in config."""
        with patch.object(boot_remote, "_parse_local_config", return_value={}):
            result = boot_remote._get_clone_path("unknown_role")
        assert result == boot_remote.REPO_ROOT
