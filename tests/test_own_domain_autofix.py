"""Tests for #3027: PM auto-fixes own-domain bugs immediately.

Verifies that:
1. The own-domain-autofix sub-skill exists and is included in PM template
2. vault-remember BRIEFING.md staleness check runs before quiet-cycle gate
3. PM SOUL.md contains Own-Domain Housekeeping section
4. Composed PM CLAUDE.md contains the auto-fix instruction
"""

import re
import pytest
from pathlib import Path

from conftest import REFERENCES_DIR, SQUIDSQUAD_DIR, SUB_SKILLS_DIR


class TestOwnDomainAutofix:
    """Verify the own-domain-autofix sub-skill is properly wired."""

    def test_sub_skill_file_exists(self):
        """The own-domain-autofix.md sub-skill file exists."""
        path = SUB_SKILLS_DIR / "pm-specific" / "own-domain-autofix.md"
        assert path.exists(), "Missing pm-specific/own-domain-autofix.md"

    def test_sub_skill_content_has_required_sections(self):
        """The sub-skill defines what counts and what doesn't."""
        path = SUB_SKILLS_DIR / "pm-specific" / "own-domain-autofix.md"
        text = path.read_text(encoding="utf-8")
        assert "What counts as PM's own domain" in text
        assert "What does NOT count" in text
        assert "BRIEFING.md staleness" in text
        assert "Config counters" in text

    def test_included_in_pm_includes_yml(self):
        """PM includes.yml references own-domain-autofix."""
        import yaml
        yml_path = REFERENCES_DIR / "roles" / "pm" / "includes.yml"
        data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        assert "pm-specific/own-domain-autofix" in data["includes"]

    def test_included_in_pm_template(self):
        """PM CLAUDE.md template has the include directive."""
        tmpl_path = REFERENCES_DIR / "roles" / "pm" / "CLAUDE.md"
        text = tmpl_path.read_text(encoding="utf-8")
        assert "{{include: pm-specific/own-domain-autofix}}" in text

    def test_composed_pm_has_autofix_section(self):
        """Composed PM CLAUDE.md contains the Own-Domain Auto-Fix section."""
        path = SQUIDSQUAD_DIR / "pm" / "CLAUDE.md"
        if not path.exists():
            pytest.skip("Composed PM CLAUDE.md not deployed")
        text = path.read_text(encoding="utf-8")
        assert "Own-Domain Auto-Fix" in text

    def test_autofix_after_pipeline_sentinel(self):
        """own-domain-autofix appears after pipeline-sentinel in includes."""
        import yaml
        yml_path = REFERENCES_DIR / "roles" / "pm" / "includes.yml"
        data = yaml.safe_load(yml_path.read_text(encoding="utf-8"))
        includes = data["includes"]
        sentinel_idx = includes.index("pm-specific/pipeline-sentinel")
        autofix_idx = includes.index("pm-specific/own-domain-autofix")
        assert autofix_idx > sentinel_idx, (
            "own-domain-autofix should come after pipeline-sentinel"
        )

    def test_manifest_references_autofix(self):
        """manifest.md references the new sub-skill."""
        manifest = (SUB_SKILLS_DIR / "manifest.md").read_text(encoding="utf-8")
        assert "pm-specific/own-domain-autofix" in manifest


class TestVaultRememberBriefingGate:
    """Verify BRIEFING.md staleness check runs before quiet-cycle gate."""

    def test_briefing_check_before_quiet_gate(self):
        """BRIEFING.md staleness check appears before the quiet-cycle gate."""
        path = SUB_SKILLS_DIR / "common" / "vault-remember.md"
        text = path.read_text(encoding="utf-8")

        briefing_pos = text.find("BRIEFING.md staleness check")
        quiet_pos = text.find("Quiet-cycle gate")

        assert briefing_pos != -1, "BRIEFING.md staleness check not found"
        assert quiet_pos != -1, "Quiet-cycle gate not found"
        assert briefing_pos < quiet_pos, (
            "BRIEFING.md staleness check must appear BEFORE quiet-cycle gate "
            f"(briefing at {briefing_pos}, quiet at {quiet_pos})"
        )

    def test_briefing_check_not_gated_by_quiet(self):
        """BRIEFING.md check explicitly states it's not gated."""
        path = SUB_SKILLS_DIR / "common" / "vault-remember.md"
        text = path.read_text(encoding="utf-8")
        assert "runs every cycle" in text, (
            "BRIEFING.md check should state it runs every cycle"
        )

    def test_vault_protocol_says_every_cycle(self):
        """vault-protocol BRIEFING.md description says every cycle."""
        path = SUB_SKILLS_DIR / "common" / "vault-protocol.md"
        text = path.read_text(encoding="utf-8")
        assert "every cycle (including quiet cycles)" in text


class TestPmSoulHousekeeping:
    """Verify PM SOUL.md has Own-Domain Housekeeping guidance."""

    def test_source_soul_has_housekeeping(self):
        """Source PM SOUL.md has Own-Domain Housekeeping section."""
        path = REFERENCES_DIR / "roles" / "pm" / "SOUL.md"
        text = path.read_text(encoding="utf-8")
        assert "### Own-Domain Housekeeping" in text

    def test_deployed_soul_has_housekeeping(self):
        """Deployed PM SOUL.md has Own-Domain Housekeeping section."""
        path = SQUIDSQUAD_DIR / "pm" / "SOUL.md"
        if not path.exists():
            pytest.skip("Deployed PM SOUL.md not present")
        text = path.read_text(encoding="utf-8")
        assert "### Own-Domain Housekeeping" in text

    def test_housekeeping_anti_patterns(self):
        """Housekeeping section includes key anti-patterns."""
        path = REFERENCES_DIR / "roles" / "pm" / "SOUL.md"
        text = path.read_text(encoding="utf-8")
        assert "BRIEFING.md is stale" in text, (
            "Should list noting staleness as an anti-pattern"
        )
        assert "Filing a tracker issue for a config counter" in text, (
            "Should list self-filing as an anti-pattern"
        )
