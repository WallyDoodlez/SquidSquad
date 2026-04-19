"""Tests for #1428 — deterministic QA verification framework.

Layer 1: Structural assertions that the framework content exists in
templates and deployed files. Catches regressions if someone edits
the template without preserving the deterministic QA rules.
"""
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent


class TestTestPlanTemplate:
    """test-plan.md.j2 enforces TC categorization."""

    @pytest.fixture
    def template(self):
        return (REPO / "references/prompts/test-plan.md.j2").read_text(encoding="utf-8")

    def test_deterministic_category_defined(self, template):
        assert "[deterministic]" in template

    def test_human_verification_category_defined(self, template):
        assert "[human-verification]" in template

    def test_requires_category_defined(self, template):
        assert "[requires:" in template

    def test_assertion_field_in_tc_format(self, template):
        assert "**Assertion**:" in template

    def test_no_unlabeled_tcs_rule(self, template):
        assert "unlabeled" in template.lower()

    def test_deterministic_categories_listed(self, template):
        """Template lists the deterministic categories."""
        lower = template.lower()
        for category in ["format", "completeness", "file reference",
                         "state transition", "regression", "comprehension"]:
            assert category in lower, f"Missing deterministic category: {category}"

    def test_human_verification_scoped_to_llm_reasoning(self, template):
        lower = template.lower()
        assert "llm reasoning" in lower or "reasoning quality" in lower


class TestVerificationSubSkill:
    """verification.md enforces deterministic results."""

    @pytest.fixture
    def verification(self):
        return (REPO / "references/sub-skills/qa-specific/verification.md").read_text(encoding="utf-8")

    def test_deferred_not_valid(self, verification):
        assert '"Deferred" is NOT a valid result' in verification

    def test_only_pass_fail_blocked(self, verification):
        assert "PASS, FAIL, or BLOCKED" in verification

    def test_blocked_requires_filing_issue(self, verification):
        assert "File a blocker issue" in verification

    def test_blocked_gate_prevents_shipping(self, verification):
        assert "BLOCKED gate" in verification

    def test_human_verification_skip_instruction(self, verification):
        assert "human-verification" in verification


class TestDeployedQAClaude:
    """QA CLAUDE.md has the framework deployed."""

    @pytest.fixture
    def qa_claude(self):
        return (REPO / ".squidsquad/qa/CLAUDE.md").read_text(encoding="utf-8")

    def test_deferred_rejection_deployed(self, qa_claude):
        assert '"Deferred" is NOT a valid result' in qa_claude

    def test_blocked_gate_deployed(self, qa_claude):
        assert "BLOCKED gate" in qa_claude

    def test_human_verification_deployed(self, qa_claude):
        assert "human-verification" in qa_claude
