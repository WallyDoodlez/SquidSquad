"""Tests for #1328 — verification skips blocked:human-action items.

Structural assertions that both PM and QA verification sub-skills
include the blocked:human-action check before attempting verification.
"""
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
PM_VERIFICATION = REPO / "references/sub-skills/roles/pm/testing-and-verification.md"
QA_VERIFICATION = REPO / "references/sub-skills/roles/qa/verification.md"


class TestPMVerificationBlockedCheck:
    """PM verification (Steps 5-6) skips blocked:human-action items."""

    @pytest.fixture
    def content(self):
        return PM_VERIFICATION.read_text(encoding="utf-8")

    def test_step5_has_blocked_check(self, content):
        """Step 5 (verify fixed issues) checks blocked:human-action before verifying."""
        # Find Step 5 section and verify the blocked check appears before
        # the first verification action
        step5_start = content.index("Step 5")
        step6_start = content.index("Step 6")
        step5_text = content[step5_start:step6_start]
        assert "blocked:human-action" in step5_text

    def test_step6_has_blocked_check(self, content):
        """Step 6 (verify pending test tasks) checks blocked:human-action before verifying."""
        step6_start = content.index("Step 6 — Verify Pending Test Tasks")
        step6c_start = content.index("Step 6c")
        step6_text = content[step6_start:step6c_start]
        assert "blocked:human-action" in step6_text

    def test_blocked_check_says_skip(self, content):
        """Blocked check instructs to skip, not transition status."""
        assert "skip it" in content.lower() or "Skip it" in content


class TestQAVerificationBlockedCheck:
    """QA verification (Steps 4-5) skips blocked:human-action items."""

    @pytest.fixture
    def content(self):
        return QA_VERIFICATION.read_text(encoding="utf-8")

    def test_step4_has_blocked_check(self, content):
        """Step 4 (verify fixed issues) checks blocked:human-action."""
        step4_start = content.index("Step 4")
        step5_start = content.index("Step 5")
        step4_text = content[step4_start:step5_start]
        assert "blocked:human-action" in step4_text

    def test_step5_has_blocked_check(self, content):
        """Step 5 (verify pending test tasks) checks blocked:human-action."""
        step5_start = content.index("Step 5 — Verify Pending Test Tasks")
        step5b_start = content.index("Step 5b")
        step5_text = content[step5_start:step5b_start]
        assert "blocked:human-action" in step5_text

    def test_no_status_transition_for_blocked(self, content):
        """Blocked items must not have their status changed."""
        # Each blocked check should say "Do not change its status"
        assert content.count("Do not change its status") >= 2
