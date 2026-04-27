"""Tests for #1075 — Vault Candidates section in Phase 1 Research output.

Structural assertions that the research template and prompt include
a Vault Candidates section with correct format and candidate cap.
"""
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
TASK_INTAKE = REPO / "references/sub-skills/pm-specific/task-intake.md"
RESEARCH_PROMPT = REPO / "references/prompts/research.md.j2"


class TestTaskIntakeTemplate:
    """task-intake.md RESEARCH.md template includes Vault Candidates."""

    @pytest.fixture
    def content(self):
        return TASK_INTAKE.read_text(encoding="utf-8")

    def test_vault_candidates_section_in_template(self, content):
        """TC-1: RESEARCH.md format template has ## Vault Candidates section."""
        assert "## Vault Candidates" in content

    def test_vault_candidates_after_recommendation(self, content):
        """TC-1: Vault Candidates appears after Recommendation in template."""
        rec_pos = content.index("## Recommendation")
        vc_pos = content.index("## Vault Candidates")
        assert vc_pos > rec_pos

    def test_research_agent_instructed_to_find_candidates(self, content):
        """TC-2: Research agent analysis list includes vault candidates instruction."""
        assert "vault candidates" in content.lower()

    def test_candidate_format_has_type(self, content):
        """TC-3: Candidate format includes type field."""
        # Find the Vault Candidates section
        vc_start = content.index("## Vault Candidates")
        vc_section = content[vc_start:vc_start + 300]
        assert "decision/pattern/learning" in vc_section

    def test_candidate_cap(self, content):
        """TC-4: Prompt limits candidates to max 5."""
        assert "max 5" in content.lower()


class TestResearchPromptTemplate:
    """research.md.j2 prompt template includes Vault Candidates."""

    @pytest.fixture
    def content(self):
        return RESEARCH_PROMPT.read_text(encoding="utf-8")

    def test_vault_candidates_section_in_prompt(self, content):
        """TC-1: research.md.j2 has ## Vault Candidates section."""
        assert "## Vault Candidates" in content

    def test_prompt_instructs_vault_discovery(self, content):
        """TC-2: Prompt instructions mention vault candidates."""
        assert "vault" in content.lower()
        assert "candidates" in content.lower()

    def test_prompt_has_candidate_cap(self, content):
        """TC-4: Prompt limits candidates to max 5."""
        assert "max 5" in content.lower()
