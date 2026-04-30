"""Tests for #1228 — PM pipeline sentinel.

The pipeline sentinel is implemented as template instructions in
references/sub-skills/roles/pm/pipeline-sentinel.md (not as a Python script).
These are comprehension tests verifying the sub-skill file contains the expected
sentinel checks.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SENTINEL_FILE = REPO_ROOT / "references" / "sub-skills" / "roles" / "pm" / "pipeline-sentinel.md"


@pytest.fixture
def sentinel_text():
    assert SENTINEL_FILE.exists(), f"Pipeline sentinel file missing: {SENTINEL_FILE}"
    return SENTINEL_FILE.read_text(encoding="utf-8")


class TestPipelineSentinelExists:
    """#1228: Pipeline sentinel sub-skill file must exist."""

    def test_file_exists(self):
        """#1228: pipeline-sentinel.md must exist in pm-specific sub-skills."""
        assert SENTINEL_FILE.exists()


class TestPrConflictDetection:
    """#1228: Sentinel must include PR conflict detection."""

    def test_conflict_detection_section(self, sentinel_text):
        """#1228: Sentinel checks open PRs for CONFLICTING mergeable status."""
        assert "PR Conflict Detection" in sentinel_text
        assert "CONFLICTING" in sentinel_text

    def test_conflict_transitions_back(self, sentinel_text):
        """#1228: Conflicting PRs trigger transition back to in-progress."""
        assert "in-progress" in sentinel_text
        assert "merge conflicts" in sentinel_text.lower()


class TestStallDetection:
    """#1228: Sentinel must include stall detection."""

    def test_stall_detection_section(self, sentinel_text):
        """#1228: Sentinel detects items stalled beyond threshold."""
        assert "Stall Detection" in sentinel_text
        assert "90 minutes" in sentinel_text

    def test_stall_nudge_limits(self, sentinel_text):
        """#1228: Sentinel limits nudges to avoid noise."""
        assert "Max 2 nudges per cycle" in sentinel_text


class TestPrStatusSync:
    """#1228: Sentinel must include PR status sync."""

    def test_pr_status_sync_section(self, sentinel_text):
        """#1228: Sentinel syncs PR merge/close state to tracker items."""
        assert "PR Status Sync" in sentinel_text

    def test_merged_pr_updates_status(self, sentinel_text):
        """#1228: Merged PRs trigger Pending Ship status update."""
        assert "Pending Ship" in sentinel_text

    def test_closed_pr_updates_status(self, sentinel_text):
        """#1228: Closed-without-merge PRs trigger In Progress update."""
        assert "closed without merge" in sentinel_text.lower()


class TestStuckStateDetection:
    """#1228: Sentinel must include comprehensive stuck-state detection."""

    def test_orphaned_pr_check(self, sentinel_text):
        """#1228: Sentinel detects orphaned PRs (item closed but PR open)."""
        assert "Orphaned PR" in sentinel_text

    def test_shipped_without_merge_check(self, sentinel_text):
        """#1228: Sentinel detects items shipped but branch never merged."""
        assert "Shipped without merge" in sentinel_text

    def test_approved_no_pickup_check(self, sentinel_text):
        """#1228: Sentinel detects approved items with no agent pickup."""
        assert "Approved but no pickup" in sentinel_text

    def test_dead_agent_check(self, sentinel_text):
        """#1228: Sentinel detects in-progress tasks on dead agents."""
        assert "dead agent" in sentinel_text.lower()
        assert "health_check.py" in sentinel_text

    def test_tier_system(self, sentinel_text):
        """#1228: Sentinel uses Tier 1 (immediate) and Tier 2 (root-cause) responses."""
        assert "Tier 1" in sentinel_text
        assert "Tier 2" in sentinel_text
