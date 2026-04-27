"""
FEAT-QA-1075 — Vault Candidates in Phase 1 Research output template.

Tests verify that:
- task-intake.md RESEARCH.md template includes "## Vault Candidates" section
- The section appears after "## Recommendation"
- The research agent analysis list instructs vault candidate identification
- The candidate format includes type/description/rationale fields
- A cap of max 5 candidates is specified
- research.md.j2 prompt template includes the same elements
"""
import pytest
from pathlib import Path

REPO = Path(__file__).parent.parent.parent.parent
TASK_INTAKE = REPO / "references/sub-skills/pm-specific/task-intake.md"
RESEARCH_PROMPT = REPO / "references/prompts/research.md.j2"


# ---------------------------------------------------------------------------
# TC-01: RESEARCH.md template includes Vault Candidates section
# ---------------------------------------------------------------------------

class TestTC01VaultCandidatesSectionPresent:
    """TC-1: ## Vault Candidates section is present in RESEARCH.md template."""

    def test_task_intake_file_exists(self):
        assert TASK_INTAKE.exists(), f"task-intake.md not found at {TASK_INTAKE}"

    def test_vault_candidates_section_in_task_intake(self):
        content = TASK_INTAKE.read_text(encoding="utf-8")
        assert "## Vault Candidates" in content, (
            "Expected '## Vault Candidates' section in task-intake.md RESEARCH.md template"
        )

    def test_vault_candidates_after_recommendation(self):
        content = TASK_INTAKE.read_text(encoding="utf-8")
        assert "## Recommendation" in content, "## Recommendation section missing"
        assert "## Vault Candidates" in content, "## Vault Candidates section missing"
        rec_pos = content.index("## Recommendation")
        vc_pos = content.index("## Vault Candidates")
        assert vc_pos > rec_pos, (
            f"## Vault Candidates (pos {vc_pos}) must appear after ## Recommendation (pos {rec_pos})"
        )

    def test_research_prompt_file_exists(self):
        assert RESEARCH_PROMPT.exists(), f"research.md.j2 not found at {RESEARCH_PROMPT}"

    def test_vault_candidates_section_in_research_prompt(self):
        content = RESEARCH_PROMPT.read_text(encoding="utf-8")
        assert "## Vault Candidates" in content, (
            "Expected '## Vault Candidates' section in research.md.j2 output template"
        )

    def test_vault_candidates_after_recommendation_in_prompt(self):
        content = RESEARCH_PROMPT.read_text(encoding="utf-8")
        assert "## Recommendation" in content, "## Recommendation section missing in research.md.j2"
        assert "## Vault Candidates" in content, "## Vault Candidates section missing in research.md.j2"
        rec_pos = content.index("## Recommendation")
        vc_pos = content.index("## Vault Candidates")
        assert vc_pos > rec_pos, (
            f"In research.md.j2: ## Vault Candidates (pos {vc_pos}) must appear after "
            f"## Recommendation (pos {rec_pos})"
        )


# ---------------------------------------------------------------------------
# TC-02: Research agent prompt requests vault candidates
# ---------------------------------------------------------------------------

class TestTC02ResearchPromptRequestsVaultCandidates:
    """TC-2: Research agent analysis steps include vault candidate identification."""

    def test_task_intake_analysis_list_mentions_vault_candidates(self):
        content = TASK_INTAKE.read_text(encoding="utf-8")
        # The analysis numbered list should include a vault candidates step
        assert "vault candidates" in content.lower(), (
            "task-intake.md research agent analysis list should mention 'vault candidates'"
        )

    def test_research_prompt_instructions_mention_vault(self):
        content = RESEARCH_PROMPT.read_text(encoding="utf-8")
        assert "vault" in content.lower(), (
            "research.md.j2 instructions should mention 'vault'"
        )

    def test_research_prompt_instructions_mention_candidates(self):
        content = RESEARCH_PROMPT.read_text(encoding="utf-8")
        assert "candidates" in content.lower(), (
            "research.md.j2 instructions should mention 'candidates'"
        )

    def test_research_prompt_discovery_instruction_present(self):
        content = RESEARCH_PROMPT.read_text(encoding="utf-8")
        # Should instruct the agent to flag vault-worthy discoveries
        lower = content.lower()
        has_flag = "flag" in lower or "preserv" in lower or "vault-worthy" in lower
        assert has_flag, (
            "research.md.j2 should instruct agent to flag vault-worthy discoveries "
            "(look for 'flag', 'preserv', or 'vault-worthy')"
        )


# ---------------------------------------------------------------------------
# TC-03: Candidate format is structured (type, description, rationale)
# ---------------------------------------------------------------------------

class TestTC03CandidateFormatIsStructured:
    """TC-3: Vault Candidates format includes type, description, and rationale."""

    def _get_vault_candidates_section(self, content: str, max_chars: int = 500) -> str:
        """Extract text starting at ## Vault Candidates."""
        idx = content.index("## Vault Candidates")
        return content[idx: idx + max_chars]

    def test_task_intake_candidate_format_has_type_field(self):
        content = TASK_INTAKE.read_text(encoding="utf-8")
        section = self._get_vault_candidates_section(content)
        assert "decision/pattern/learning" in section, (
            "Vault Candidates section in task-intake.md should show type options: "
            "'decision/pattern/learning'"
        )

    def test_task_intake_candidate_format_has_why_rationale(self):
        content = TASK_INTAKE.read_text(encoding="utf-8")
        section = self._get_vault_candidates_section(content)
        lower = section.lower()
        assert "why" in lower or "rationale" in lower, (
            "Vault Candidates format in task-intake.md should include a 'Why' or rationale field"
        )

    def test_research_prompt_candidate_format_has_type_field(self):
        content = RESEARCH_PROMPT.read_text(encoding="utf-8")
        section = self._get_vault_candidates_section(content)
        assert "decision/pattern/learning" in section, (
            "Vault Candidates section in research.md.j2 should show type options: "
            "'decision/pattern/learning'"
        )

    def test_research_prompt_candidate_format_has_why_rationale(self):
        content = RESEARCH_PROMPT.read_text(encoding="utf-8")
        section = self._get_vault_candidates_section(content)
        lower = section.lower()
        assert "why" in lower or "rationale" in lower, (
            "Vault Candidates format in research.md.j2 should include a 'Why' or rationale field"
        )


# ---------------------------------------------------------------------------
# TC-04: Cap on candidates (max 3-5)
# ---------------------------------------------------------------------------

class TestTC04CandidateCap:
    """TC-4: A cap on the number of vault candidates is specified."""

    def test_task_intake_specifies_candidate_cap(self):
        content = TASK_INTAKE.read_text(encoding="utf-8")
        lower = content.lower()
        # Accept "max 3", "max 4", "max 5" — the test plan says 3-5
        has_cap = any(f"max {n}" in lower for n in range(3, 6))
        assert has_cap, (
            "task-intake.md should specify a cap of max 3-5 vault candidates "
            "(e.g. 'max 5 candidates')"
        )

    def test_research_prompt_specifies_candidate_cap(self):
        content = RESEARCH_PROMPT.read_text(encoding="utf-8")
        lower = content.lower()
        has_cap = any(f"max {n}" in lower for n in range(3, 6))
        assert has_cap, (
            "research.md.j2 should specify a cap of max 3-5 vault candidates "
            "(e.g. 'max 5 candidates')"
        )

    def test_task_intake_cap_is_in_vault_candidates_section(self):
        content = TASK_INTAKE.read_text(encoding="utf-8")
        idx = content.index("## Vault Candidates")
        # Look in the 300 chars after the section header
        section = content[idx: idx + 300].lower()
        has_cap = any(f"max {n}" in section for n in range(3, 6))
        assert has_cap, (
            "The cap ('max N candidates') should appear inside the Vault Candidates section "
            "in task-intake.md"
        )

    def test_research_prompt_cap_is_in_vault_candidates_section(self):
        content = RESEARCH_PROMPT.read_text(encoding="utf-8")
        idx = content.index("## Vault Candidates")
        section = content[idx: idx + 300].lower()
        has_cap = any(f"max {n}" in section for n in range(3, 6))
        assert has_cap, (
            "The cap ('max N candidates') should appear inside the Vault Candidates section "
            "in research.md.j2"
        )
