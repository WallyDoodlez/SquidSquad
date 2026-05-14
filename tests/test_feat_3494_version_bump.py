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


class TestVersionBumpNoStagedChanges:
    """#5126 — skip commit/tag/push when nothing was staged."""

    def test_skips_commit_tag_push_when_no_staged_changes(self, tmp_path, monkeypatch):
        """If git diff --cached --quiet returns 0 (no changes), skip commit/tag/push."""
        monkeypatch.setattr(cycle_post, "REPO_ROOT", tmp_path)

        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        config_md = squid / "config.md"
        config_md.write_text("- **SquidSquad Version**: 0.27.0\n", encoding="utf-8")
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n", encoding="utf-8")

        # Commands that must NOT be reached when nothing is staged
        forbidden = {"commit", "push"}
        run_calls = []
        def fake_run(cmd, check=False):
            run_calls.append(cmd)
            result = MagicMock()
            result.stdout = ""
            if cmd[:4] == ["git", "diff", "--cached", "--quiet"]:
                result.returncode = 0  # nothing staged
            elif len(cmd) >= 2 and cmd[0] == "git" and cmd[1] in forbidden:
                raise AssertionError(f"Forbidden git command reached: {cmd}")
            elif len(cmd) >= 2 and cmd[:2] == ["git", "tag"] and "-l" not in cmd:
                raise AssertionError(f"Forbidden git tag command reached: {cmd}")
            else:
                result.returncode = 0
            return result
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a: None)

        data = {"version_bump": {"new_version": "0.28.0", "items_included": []}}
        # If the guard is missing, fake_run raises AssertionError on commit/tag/push
        cycle_post._do_version_bump(data, "dm")

    def test_proceeds_when_staged_changes_exist(self, tmp_path, monkeypatch):
        """If git diff --cached --quiet returns 1 (has changes), proceed normally."""
        monkeypatch.setattr(cycle_post, "REPO_ROOT", tmp_path)

        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        config_md = squid / "config.md"
        config_md.write_text("- **SquidSquad Version**: 0.27.0\n", encoding="utf-8")
        changelog = tmp_path / "CHANGELOG.md"
        changelog.write_text("# Changelog\n", encoding="utf-8")

        run_calls = []
        def fake_run(cmd, check=False):
            run_calls.append(cmd)
            result = MagicMock()
            result.stdout = ""
            # git diff --cached --quiet returns 1 when changes are staged
            if cmd[:4] == ["git", "diff", "--cached", "--quiet"]:
                result.returncode = 1
            else:
                result.returncode = 0
            return result
        monkeypatch.setattr(cycle_post, "_run", fake_run)
        monkeypatch.setattr(cycle_post, "_run_script", lambda *a: None)

        data = {"version_bump": {"new_version": "0.28.0", "items_included": []}}
        cycle_post._do_version_bump(data, "dm")

        # Should have commit and push calls
        commit_calls = [c for c in run_calls if c[:2] == ["git", "commit"]]
        push_calls = [c for c in run_calls if c[:2] == ["git", "push"]]
        assert len(commit_calls) == 1, f"Expected 1 commit, got {commit_calls}"
        assert len(push_calls) >= 1, f"Expected push calls, got {push_calls}"
