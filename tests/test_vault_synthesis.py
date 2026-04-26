"""Tests for vault-synthesis sub-skill — structural and content verification.

Verifies that the vault-synthesis sub-skill template contains the required
components: 5-cycle trigger, cross-agent note reading, posture note creation
with 'pattern' type and 'posture' tag, and human approval task filing.
"""

import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
REFERENCES_DIR = REPO_ROOT / "references"
SUB_SKILLS_DIR = REFERENCES_DIR / "sub-skills"


@pytest.fixture(scope="module")
def synthesis_text():
    """Read the vault-synthesis sub-skill content."""
    path = SUB_SKILLS_DIR / "pm-specific" / "vault-synthesis.md"
    assert path.exists(), "vault-synthesis.md not found"
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def composed_pm():
    """Read the composed PM CLAUDE.md output."""
    path = REPO_ROOT / ".squidsquad" / "pm" / "CLAUDE.md"
    if not path.exists():
        pytest.skip("Composed PM CLAUDE.md not available")
    return path.read_text(encoding="utf-8")


class TestVaultSynthesisStructure:
    """Verify the sub-skill file has required structural elements."""

    def test_file_exists(self):
        assert (SUB_SKILLS_DIR / "pm-specific" / "vault-synthesis.md").exists()

    def test_five_cycle_trigger(self, synthesis_text):
        """#3139: Synthesis triggers after 5 consecutive quiet cycles."""
        assert "5 consecutive quiet cycles" in synthesis_text

    def test_separate_counter(self, synthesis_text):
        """#3139: Synthesis counter is separate from improvement scan counter."""
        assert "separate" in synthesis_text.lower() and "scan" in synthesis_text.lower()

    def test_cross_agent_reading(self, synthesis_text):
        """#3139: Synthesis reads vault notes from ALL agents."""
        assert "all agents" in synthesis_text.lower() or "cross-agent" in synthesis_text.lower()

    def test_galaxy_notes_targeted(self, synthesis_text):
        """#3139: Synthesis reads galaxy/ notes specifically."""
        assert "galaxy" in synthesis_text

    def test_pattern_type_used(self, synthesis_text):
        """#3139: Posture notes use existing 'pattern' vault type."""
        # Check that the type field is set to pattern
        assert re.search(r'\*\*Type\*\*.*pattern', synthesis_text)

    def test_posture_tag_required(self, synthesis_text):
        """#3139: Posture notes include the 'posture' tag."""
        assert re.search(r'\*\*Tags\*\*.*posture', synthesis_text)

    def test_human_approval_task(self, synthesis_text):
        """#3139: Each posture files a pending task for human review."""
        assert "create-task" in synthesis_text
        assert "pending" in synthesis_text.lower() or "human" in synthesis_text.lower()

    def test_max_one_posture_per_cycle(self, synthesis_text):
        """#3139: Max 1 posture per synthesis cycle."""
        assert re.search(r'max.*1.*per.*synthesis', synthesis_text, re.IGNORECASE)

    def test_convergence_requirement(self, synthesis_text):
        """#3139: Postures require convergence from 2+ sources."""
        assert re.search(r'2\+.*sources|2\+.*distinct|cross-agent only', synthesis_text, re.IGNORECASE)

    def test_vault_check_after_creation(self, synthesis_text):
        """#3139: vault-check Level 1 runs after posture note creation."""
        assert "vault-check" in synthesis_text

    def test_last_synthesis_sentinel(self, synthesis_text):
        """#3139: .last-synthesis file used to track last run."""
        assert ".last-synthesis" in synthesis_text

    def test_vault_size_gate(self, synthesis_text):
        """#3139: Vault must have 10+ galaxy notes before synthesis runs."""
        assert re.search(r'10\+.*galaxy.*notes', synthesis_text)

    def test_never_auto_approve(self, synthesis_text):
        """#3139: Postures are never auto-approved."""
        assert "never auto-approve" in synthesis_text.lower()


class TestVaultSynthesisComposed:
    """Verify the sub-skill is properly composed into PM's CLAUDE.md."""

    def test_synthesis_in_composed_output(self, composed_pm):
        """#3139: vault-synthesis appears in composed PM CLAUDE.md."""
        assert "Vault Synthesis" in composed_pm

    def test_synthesis_after_vault_optimize(self, composed_pm):
        """#3139: vault-synthesis appears after vault-optimize in compose order."""
        optimize_pos = composed_pm.find("vault-optimize")
        synthesis_pos = composed_pm.find("vault-synthesis")
        assert optimize_pos > 0 and synthesis_pos > 0, "Both sections must exist"
        assert synthesis_pos > optimize_pos, "Synthesis must come after optimize"

    def test_posture_tag_in_composed(self, composed_pm):
        """#3139: 'posture' tag convention documented in composed output."""
        assert "posture" in composed_pm


class TestVaultSynthesisManifest:
    """Verify manifest.md includes vault-synthesis."""

    def test_manifest_entry_exists(self):
        manifest = (SUB_SKILLS_DIR / "manifest.md").read_text(encoding="utf-8")
        assert "pm-specific/vault-synthesis" in manifest

    def test_includes_yml_entry(self):
        includes_path = REFERENCES_DIR / "roles" / "pm" / "includes.yml"
        includes_text = includes_path.read_text(encoding="utf-8")
        assert "pm-specific/vault-synthesis" in includes_text
