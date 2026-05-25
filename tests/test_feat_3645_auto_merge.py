"""Tests for #3645 — Auto Merge config wired into PR Flow verification.

Structural assertions that QA and PM verification sub-skills check Auto Merge
config and review:human-required label before deciding merge vs human review.
"""
import sys
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
QA_VERIFICATION = REPO / "references/sub-skills/roles/verifier/verification.md"  # #10156
PM_VERIFICATION = REPO / "references/sub-skills/roles/pm/testing-and-verification.md"
SCRIPTS = REPO / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))


class TestQAVerificationAutoMerge:
    """QA verification checks Auto Merge before routing."""

    @pytest.fixture
    def content(self):
        return QA_VERIFICATION.read_text(encoding="utf-8")

    def test_checks_auto_merge_config(self, content):
        assert "auto-merge" in content

    def test_checks_human_required_label(self, content):
        assert "review:human-required" in content

    def test_auto_merge_on_merges_directly(self, content):
        """Auto Merge ON path merges PR and goes to pending-ship."""
        assert "pr-merge" in content
        assert "pending-ship" in content

    def test_auto_merge_off_routes_to_review(self, content):
        """Auto Merge OFF path routes to pending-human-review."""
        assert "pending-human-review" in content

    def test_per_ticket_override(self, content):
        """review:human-required label overrides Auto Merge."""
        # Both conditions mentioned together
        idx_auto = content.index("Auto Merge")
        idx_review = content.index("review:human-required")
        # Both appear in the PR Flow section
        assert abs(idx_auto - idx_review) < 2000


class TestPMVerificationAutoMerge:
    """PM verification (QA fallback) checks Auto Merge."""

    @pytest.fixture
    def content(self):
        return PM_VERIFICATION.read_text(encoding="utf-8")

    def test_checks_auto_merge_config(self, content):
        assert "auto-merge" in content

    def test_checks_human_required_label(self, content):
        assert "review:human-required" in content

    def test_pr_flow_gate_exists(self, content):
        """PM Step 6 has a PR Flow gate for Auto Merge."""
        assert "PR Flow gate" in content


class TestTrackerLabelTaxonomy:
    """review:human-required label is in tracker.py."""

    def test_special_labels_includes_review_human_required(self):
        import tracker
        assert "review:human-required" in tracker.SPECIAL_LABELS
