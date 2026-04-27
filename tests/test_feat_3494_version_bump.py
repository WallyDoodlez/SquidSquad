"""Tests for #3494 — version bump uses explicit file paths, not git add -A.

Verifies that _do_version_bump stages only specific files instead of
the entire working tree.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import cycle_post


class TestVersionBumpStaging:
    """Version bump must not use git add -A."""

    def test_source_code_no_git_add_dash_A(self):
        """The _do_version_bump function must not contain 'git add -A'."""
        import inspect
        source = inspect.getsource(cycle_post._do_version_bump)
        assert "add\", \"-A\"" not in source, \
            "_do_version_bump still uses git add -A (should use explicit file paths)"

    def test_stages_explicit_files(self, tmp_path, monkeypatch):
        """Version bump stages only config.md, CHANGELOG.md, and SKILL.md."""
        monkeypatch.setattr(cycle_post, "REPO_ROOT", tmp_path)

        # Create minimal files
        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        config_md = squid / "config.md"
        config_md.write_text("- **SquidSquad Version**: 0.27.0\n", encoding="utf-8")
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n", encoding="utf-8")
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text("---\nversion: 0.27.0\n---\n", encoding="utf-8")

        # Track all _run calls
        run_calls = []
        def fake_run(cmd, check=False):
            run_calls.append(cmd)
            result = MagicMock()
            result.stdout = ""
            result.returncode = 0
            return result
        monkeypatch.setattr(cycle_post, "_run", fake_run)

        # Stub _run_script (config.py set)
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a: None)

        data = {
            "version_bump": {
                "new_version": "0.28.0",
                "items_included": [3495, 3493],
            }
        }

        cycle_post._do_version_bump(data, "dm")

        # Find the git add call
        add_calls = [c for c in run_calls if c[0] == "git" and c[1] == "add"]
        assert len(add_calls) == 1, f"Expected 1 git add call, got {len(add_calls)}: {add_calls}"

        add_cmd = add_calls[0]
        # Must NOT contain -A
        assert "-A" not in add_cmd, f"git add -A found: {add_cmd}"
        # Must contain explicit files
        assert ".squidsquad/config.md" in add_cmd
        assert "CHANGELOG.md" in add_cmd
        assert "SKILL.md" in add_cmd

    def test_no_skill_md_omits_it(self, tmp_path, monkeypatch):
        """If SKILL.md doesn't exist, it's not staged."""
        monkeypatch.setattr(cycle_post, "REPO_ROOT", tmp_path)

        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        config_md = squid / "config.md"
        config_md.write_text("- **SquidSquad Version**: 0.27.0\n", encoding="utf-8")
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n", encoding="utf-8")
        # No SKILL.md

        run_calls = []
        def fake_run(cmd, check=False):
            run_calls.append(cmd)
            result = MagicMock()
            result.stdout = ""
            result.returncode = 0
            return result
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a: None)

        data = {"version_bump": {"new_version": "0.28.0", "items_included": []}}
        cycle_post._do_version_bump(data, "dm")

        add_calls = [c for c in run_calls if c[0] == "git" and c[1] == "add"]
        assert len(add_calls) == 1
        add_cmd = add_calls[0]
        assert "SKILL.md" not in add_cmd
