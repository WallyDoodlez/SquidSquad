"""Tests for #3663 — Dev agent checks open PRs for merge conflicts each cycle.

Structural assertions that the git-commit sub-skill includes PR conflict
detection and rebase instructions when PR Flow is on.
"""
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
GIT_COMMIT = REPO / "references/sub-skills/common/git-commit.md"


class TestPRConflictCheck:
    """git-commit sub-skill includes PR conflict check step."""

    @pytest.fixture
    def content(self):
        return GIT_COMMIT.read_text(encoding="utf-8")

    def test_checks_mergeable_status(self, content):
        """Step queries PR mergeable status."""
        assert "mergeable" in content
        assert "CONFLICTING" in content

    def test_rebases_conflicting_prs(self, content):
        """Conflicting PRs are rebased onto main."""
        assert "git rebase" in content

    def test_force_push_after_rebase(self, content):
        """Successful rebase is force-pushed."""
        assert "force-with-lease" in content

    def test_abort_on_conflict(self, content):
        """Failed rebase is aborted cleanly."""
        assert "rebase --abort" in content

    def test_only_own_branches(self, content):
        """Only rebases own role's branches."""
        assert "squidsquad/[ROLE]/" in content
        assert "never touch other agents" in content.lower() or "Only rebase own branches" in content

    def test_gated_on_pr_flow(self, content):
        """Step only runs when PR Flow is on."""
        assert "PR Flow" in content
        # The step is inside the "If yes" block
        idx_step = content.index("check own open PRs for merge conflicts")
        idx_pr_flow = content.rindex("PR Flow `yes`", 0, idx_step)
        assert idx_pr_flow < idx_step
