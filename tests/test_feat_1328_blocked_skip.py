"""Tests for #1328 — verification skips blocked:human-action items.

Structural assertions that both PM and verifier sub-skills include the
blocked:human-action check before attempting verification.

#10156: post-#6274.2 rename (qa→verifier). Test method and class names
that contain `qa` are intentionally NOT renamed to avoid breaking
`pytest -k` filters and CI configs; only docstrings + assertions updated."""
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
PM_VERIFICATION = REPO / "references/sub-skills/roles/pm/testing-and-verification.md"
QA_VERIFICATION = REPO / "references/sub-skills/roles/verifier/verification.md"  # #10156


class TestPMVerificationBlockedCheck:
    """PM delegates verification to the verifier — no direct verification steps."""

    @pytest.fixture
    def content(self):
        return PM_VERIFICATION.read_text(encoding="utf-8")

    def test_pm_does_not_verify_directly(self, content):
        """PM template explicitly states the verifier handles verification.
        #10156: terminology — post-#6274.2 the role is `verifier`, not `qa`."""
        assert "Verifier handles all testing and verification" in content

    def test_pm_has_no_verification_steps(self, content):
        """PM should not contain Step 5/6 verification sections."""
        assert "Step 5" not in content
        assert "Step 6 — Verify" not in content


class TestShipCounterOwnership:
    """Regression for #7793 + #12749 (DM-ARCH) — release-counter ownership.

    #7793 established a single incrementer to prevent double-counting.
    #12749 moves release state off the verifier ENTIRELY: the verifier
    owns no release state; the DM owns the `Shipped Since Last Bump`
    counter under its L4 project policy. This test locks the new model —
    neither the verifier nor PM carries a counter-increment command."""

    def test_qa_owns_ship_counter(self):
        """Verifier verification.md must NOT increment the ship counter —
        release state is the DM's under its L4 policy (#12749). Method name
        retained for pytest -k compatibility (#10156)."""
        content = QA_VERIFICATION.read_text(encoding="utf-8")
        # No increment command may survive on the verifier (the prior
        # `config.py set shipped-since-bump` line was removed).
        assert "set shipped-since-bump" not in content
        # And the verifier explicitly disclaims release state.
        assert "belongs entirely to the DM" in content

    def test_pm_does_not_own_ship_counter(self):
        """PM must never increment the ship counter — it is DM-owned."""
        content = PM_VERIFICATION.read_text(encoding="utf-8")
        assert "set shipped-since-bump" not in content


class TestQAVerificationBlockedCheck:
    """Verifier verification (Steps 4-5) skips blocked:human-action items.
    Class name retained for pytest -k compatibility (#10156)."""

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
