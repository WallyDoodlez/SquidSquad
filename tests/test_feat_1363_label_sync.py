"""Tests for #1363 — PR label sync.

PR label sync is implemented as part of the pipeline sentinel template
(references/sub-skills/pm-specific/pipeline-sentinel.md, section 3).
No standalone Python script exists for this feature.

These are content-verification tests ensuring the PR Status Sync
instructions are present and correctly specified.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SENTINEL_FILE = REPO_ROOT / "references" / "sub-skills" / "pm-specific" / "pipeline-sentinel.md"


@pytest.fixture
def sentinel_text():
    assert SENTINEL_FILE.exists(), f"Pipeline sentinel file missing: {SENTINEL_FILE}"
    return SENTINEL_FILE.read_text(encoding="utf-8")


class TestPrLabelSyncExists:
    """#1363: PR label sync section must exist in pipeline sentinel."""

    def test_pr_status_sync_section_present(self, sentinel_text):
        """#1363: pipeline-sentinel.md must contain a PR Status Sync section."""
        assert "PR Status Sync" in sentinel_text

    def test_section_under_sentinel(self, sentinel_text):
        """#1363: PR Status Sync is section 3 of the pipeline sentinel."""
        # Verify ordering: section 3 appears after sections 1 and 2
        conflict_pos = sentinel_text.index("PR Conflict Detection")
        stall_pos = sentinel_text.index("Stall Detection")
        sync_pos = sentinel_text.index("PR Status Sync")
        assert conflict_pos < stall_pos < sync_pos


class TestMergedPrSync:
    """#1363: Merged PRs must sync status to Pending Ship."""

    def test_merged_pr_triggers_pending_ship(self, sentinel_text):
        """#1363: When a PR is merged, the tracker item updates to Pending Ship."""
        assert "If merged" in sentinel_text
        assert "Pending Ship" in sentinel_text

    def test_merged_pr_adds_comment(self, sentinel_text):
        """#1363: Merged PR sync adds a comment to the tracker item."""
        assert "PR merged" in sentinel_text


class TestClosedPrSync:
    """#1363: PRs closed without merge must sync status to In Progress."""

    def test_closed_pr_triggers_in_progress(self, sentinel_text):
        """#1363: When a PR is closed without merge, status returns to In Progress."""
        assert "closed without merge" in sentinel_text.lower()
        assert "In Progress" in sentinel_text

    def test_closed_pr_adds_comment(self, sentinel_text):
        """#1363: Closed-without-merge sync adds a comment."""
        # The section describes commenting on state changes
        sync_section_start = sentinel_text.index("PR Status Sync")
        sync_section = sentinel_text[sync_section_start:]
        # Both merged and closed paths mention Comment
        assert "Comment" in sync_section


class TestSyncDataSource:
    """#1363: PR sync uses the conflict check query data (no duplicate API calls)."""

    def test_reuses_conflict_check_query(self, sentinel_text):
        """#1363: PR sync reuses the PR list from the conflict check step."""
        assert "from the conflict check query above" in sentinel_text
