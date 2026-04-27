"""Tests for #3499 — PM template orphaned sub-skill cleanup.

Verifies that cycle-runner-superseded files are removed and PM template
composes without them.
"""
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
PM_SUBSKILLS = REPO / "references/sub-skills/pm-specific"
PM_INCLUDES = REPO / "references/roles/pm/includes.yml"


class TestOrphanedFilesRemoved:
    """Cycle-runner-superseded PM sub-skills should not exist on disk."""

    def test_git_commit_removed(self):
        assert not (PM_SUBSKILLS / "git-commit.md").exists(), \
            "pm-specific/git-commit.md should be deleted (superseded by cycle-runner)"

    def test_iteration_log_removed(self):
        assert not (PM_SUBSKILLS / "iteration-log.md").exists(), \
            "pm-specific/iteration-log.md should be deleted (superseded by cycle-runner)"


class TestPMIncludesYml:
    """PM includes.yml should not reference deleted files."""

    @pytest.fixture
    def includes(self):
        return PM_INCLUDES.read_text(encoding="utf-8")

    def test_no_git_commit_include(self, includes):
        assert "pm-specific/git-commit" not in includes

    def test_no_iteration_log_include(self, includes):
        assert "pm-specific/iteration-log" not in includes

    def test_has_cycle_runner(self, includes):
        """cycle-runner replaces the deleted sub-skills."""
        assert "common/cycle-runner" in includes
