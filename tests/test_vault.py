"""Static analysis: Verify vault structure matches PARAG model.

Checks that the vault has required directories, templates exist,
and vault notes have valid frontmatter.
"""

import re
import pytest
from pathlib import Path

from conftest import VAULT_DIR, REFERENCES_DIR

# Try to import yaml for frontmatter parsing
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

PARAG_DIRS = ["projects", "areas", "resources", "archives", "galaxy"]
VALID_GALAXY_PREFIXES = {"decision-", "pattern-", "learning-", "style-"}


class TestVaultStructure:
    """Verify vault has PARAG directory structure."""

    def test_vault_exists(self):
        assert VAULT_DIR.exists(), "Vault directory missing: .squidsquad/vault/"

    @pytest.mark.parametrize("dirname", ["projects", "areas", "galaxy"])
    def test_core_parag_dirs_exist(self, dirname):
        path = VAULT_DIR / dirname
        assert path.exists(), f"Missing PARAG directory: vault/{dirname}/"

    @pytest.mark.parametrize("dirname", ["resources", "archives"])
    def test_optional_parag_dirs_exist(self, dirname):
        """Resources and archives may not exist until vault-init creates them."""
        path = VAULT_DIR / dirname
        if not path.exists():
            pytest.skip(f"vault/{dirname}/ not yet created (run vault-init)")

    def test_briefing_exists(self):
        assert (VAULT_DIR / "BRIEFING.md").exists(), "Missing vault/BRIEFING.md"


class TestVaultTemplates:
    """Verify vault templates exist in references."""

    def test_templates_dir_exists(self):
        path = REFERENCES_DIR / "vault-templates"
        assert path.exists(), "Missing references/vault-templates/"

    @pytest.mark.parametrize("template", [
        "areas-template.md",
        "galaxy-template.md",
        "projects-template.md",
        "BRIEFING.md",
    ])
    def test_template_exists(self, template):
        path = REFERENCES_DIR / "vault-templates" / template
        assert path.exists(), f"Missing vault template: {template}"


class TestGalaxyNotes:
    """Verify galaxy notes follow naming conventions and have frontmatter."""

    def _get_galaxy_notes(self):
        galaxy = VAULT_DIR / "galaxy"
        if not galaxy.exists():
            return []
        return [f for f in galaxy.glob("*.md") if f.name != ".gitkeep"]

    def test_galaxy_notes_have_valid_prefix(self):
        for note in self._get_galaxy_notes():
            has_prefix = any(note.name.startswith(p) for p in VALID_GALAXY_PREFIXES)
            assert has_prefix, (
                f"Galaxy note '{note.name}' lacks valid prefix. "
                f"Expected one of: {VALID_GALAXY_PREFIXES}"
            )

    @pytest.mark.skipif(not HAS_YAML, reason="pyyaml not installed")
    def test_galaxy_notes_have_frontmatter(self):
        for note in self._get_galaxy_notes():
            content = note.read_text(encoding="utf-8")
            assert content.startswith("---"), (
                f"Galaxy note '{note.name}' missing YAML frontmatter"
            )
            # Extract frontmatter
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm = yaml.safe_load(parts[1])
                assert fm, f"Empty frontmatter in '{note.name}'"
                assert "type" in fm, f"Missing 'type' in frontmatter: {note.name}"
