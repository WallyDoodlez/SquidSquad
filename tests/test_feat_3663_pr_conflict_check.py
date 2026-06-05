"""Tests for #3663 — Dev agent checks open PRs for merge conflicts each cycle.

Structural assertions that the git-commit sub-skill includes PR conflict
detection and merge-based resolution instructions when PR Flow is on. The
original feature shipped with rebase-based resolution; per the standing
"always merge, never rebase" project rule the resolution path was migrated
to `git merge origin/<working-branch>` and these assertions follow.
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

    def test_merges_conflicting_prs(self, content):
        """Conflicting PRs are merged from the working branch."""
        assert "git merge origin/" in content

    def test_push_after_merge(self, content):
        """Successful merge is pushed (plain push — no force-with-lease)."""
        assert "git push origin" in content
        assert "force-with-lease" not in content

    def test_abort_on_conflict(self, content):
        """Failed merge is aborted cleanly."""
        assert "git merge --abort" in content

    def test_only_own_branches(self, content):
        """Only resolves own role's branches."""
        assert "squidsquad/" in content
        assert "never touch other agents" in content.lower()

    def test_gated_on_pr_flow(self, content):
        """Step only runs when PR Flow is on."""
        assert "PR Flow" in content
        # The step is inside the "When PR Flow `yes`" block
        idx_step = content.index("check own open PRs for merge conflicts")
        idx_pr_flow = content.rindex("PR Flow `yes`", 0, idx_step + len("check own open PRs for merge conflicts"))
        assert idx_pr_flow <= idx_step
