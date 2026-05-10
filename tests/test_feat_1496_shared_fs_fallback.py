"""Regression tests for #1496 — boot_remote.py shared filesystem fallback.

Originally verified that _parse_local_config reads clone paths from the shared
filesystem (~/.squidsquad/clones/) as a fallback. The global fallback was removed
in #3100 — .local-config is now mandatory. Tests updated to reflect the new
behavior: missing .local-config exits with code 2.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import boot_remote


class TestSharedFsFallback:
    """#1496/#3100: _parse_local_config reads .local-config (mandatory, no global fallback)."""

    def test_missing_local_config_exits_not_fallback(self, tmp_path):
        """#3100: When .local-config is missing, exit with code 2 — no global fallback."""
        clones_dir = tmp_path / ".squidsquad" / "clones"
        clones_dir.mkdir(parents=True)
        (clones_dir / "skill").write_text("/home/user/skill-clone", encoding="utf-8")

        with patch.object(boot_remote, "LOCAL_CONFIG", tmp_path / "nonexistent"):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_parses_absolute_paths_from_local_config(self, tmp_path):
        """#3100: .local-config with absolute paths returns correct role→Path mapping."""
        skill_path = tmp_path / "clones" / "skill"
        qa_path = tmp_path / "clones" / "qa"
        skill_path.mkdir(parents=True)
        qa_path.mkdir(parents=True)
        local_config = tmp_path / "local-config"
        local_config_content = (
            f"- **skill**: {skill_path}\n"
            f"- **qa**: {qa_path}\n"
        )
        local_config.write_text(local_config_content, encoding="utf-8")

        with patch.object(boot_remote, "LOCAL_CONFIG", local_config):
            result = boot_remote._parse_local_config()

        assert result["skill"] == skill_path
        assert result["qa"] == qa_path

    def test_empty_local_config_exits(self, tmp_path):
        """#3100: .local-config with no valid entries exits with code 2."""
        local_config = tmp_path / "local-config"
        local_config.write_text("# just a comment, no entries\n", encoding="utf-8")

        with patch.object(boot_remote, "LOCAL_CONFIG", local_config):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_relative_paths_resolve_against_repo_root(self, tmp_path):
        """#3100: Relative paths in .local-config resolve against REPO_ROOT."""
        local_config = tmp_path / "local-config"
        local_config.write_text("- **skill**: relative/clone/path\n", encoding="utf-8")

        with patch.object(boot_remote, "LOCAL_CONFIG", local_config):
            result = boot_remote._parse_local_config()

        expected = (boot_remote.REPO_ROOT / "relative" / "clone" / "path").resolve()
        assert result["skill"] == expected

    def test_missing_local_config_exits_even_with_clones(self, tmp_path):
        """#3100: Global clones dir is irrelevant — missing .local-config still exits."""
        with patch.object(boot_remote, "LOCAL_CONFIG", tmp_path / "nonexistent"):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_no_config_exits(self, tmp_path):
        """#3100: No .local-config exits with code 2."""
        with patch.object(boot_remote, "LOCAL_CONFIG", tmp_path / "nonexistent"):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_get_clone_path_falls_back_to_repo_root(self):
        """#1496: _get_clone_path returns REPO_ROOT (as str) when role not in config."""
        with patch.object(boot_remote, "_parse_local_config", return_value={}):
            result = boot_remote._get_clone_path("unknown_role")
        assert result == str(boot_remote.REPO_ROOT)
