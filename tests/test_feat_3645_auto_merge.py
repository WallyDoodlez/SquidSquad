"""Tests for #3645 — Auto Merge config wired into PR Flow verification.

Structural assertions that verifier checks Auto Merge config and
review:human-required label before deciding merge vs human review.

#10213: PM-side coverage (TestPMVerificationAutoMerge) was removed
when #6274.2 rewrote PM's testing-and-verification.md to delegate
all verification to verifier — the auto-merge gate no longer lives
in the PM file by design. The TestQAVerificationAutoMerge class
below covers the assertions against the verifier file (the new
home of the gate logic).
"""
import sys
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
QA_VERIFICATION = REPO / "references/sub-skills/roles/verifier/verification.md"  # #10156
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


class TestPMDelegatesToVerifier:
    """#10213: After #6274.2, PM's testing-and-verification.md was rewritten
    to delegate all verification to verifier — including the auto-merge gate.
    The old TestPMVerificationAutoMerge class asserted PM-side `auto-merge`,
    `review:human-required`, and `PR Flow gate` substrings; those were
    moved to the verifier file (`PR Flow gate` was retired entirely). This
    class replaces those obsolete assertions with the inverse contract:
    the PM file delegates and does NOT carry the gate itself."""

    PM_VERIFICATION = REPO / "references/sub-skills/roles/pm/testing-and-verification.md"

    @pytest.fixture
    def content(self):
        return self.PM_VERIFICATION.read_text(encoding="utf-8")

    def test_pm_does_not_carry_auto_merge_gate(self, content):
        """PM no longer evaluates Auto Merge — that lives in verifier per
        #6274.2's delegation rewrite. If a future edit re-introduces it
        in PM, the gate decision will be in two places and drift."""
        assert "auto-merge" not in content.lower(), (
            "PM testing-and-verification.md must not carry the auto-merge "
            "gate — verifier owns it post-#6274.2"
        )

    def test_pm_does_not_check_human_required_label(self, content):
        """Same deal for the per-ticket override label. Case-normalized
        so any uppercase drift (e.g. `Review:Human-Required`) is also
        caught — matches the lowercase check in the auto-merge test."""
        assert "review:human-required" not in content.lower(), (
            "PM testing-and-verification.md must not check "
            "review:human-required — verifier owns the routing decision"
        )

    def test_pm_delegates_to_verifier(self, content):
        """The delegation statement must remain — it's the contract that
        prevents the gate from drifting back into PM. Bare `"erifier" in
        content` would pass for any verifier mention (e.g. 'the verifier
        is not involved'); require the active delegation verb so the
        contract isn't gameable by an unrelated reference."""
        assert "erifier handles" in content.lower(), (
            "PM testing-and-verification.md must contain a delegation "
            "statement of the form 'Verifier handles ...' — verifier "
            "owns verification post-#6274.2"
        )


class TestTrackerLabelTaxonomy:
    """review:human-required label is in tracker.py."""

    def test_special_labels_includes_review_human_required(self):
        import tracker
        assert "review:human-required" in tracker.SPECIAL_LABELS
