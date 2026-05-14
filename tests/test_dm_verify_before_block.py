"""Regression test for #2700: DM must verify before declaring human-blocked.

Ensures the verification requirement exists in DM's prohibitions sub-skill
and the deployed CLAUDE.md template.
"""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestDmVerifyBeforeBlock:
    def test_prohibitions_has_verify_requirement(self):
        """DM prohibitions sub-skill must require verification before human-block."""
        path = REPO_ROOT / "references" / "sub-skills" / "roles" / "dm" / "prohibitions.md"
        content = path.read_text(encoding="utf-8")
        assert "verify" in content.lower()
        assert "pending-human-setup" in content
        assert "npm whoami" in content

    def test_soul_has_verify_boundary(self):
        """DM SOUL.md must include verification boundary."""
        path = REPO_ROOT / "references" / "roles" / "dm" / "SOUL.md"
        content = path.read_text(encoding="utf-8")
        assert "verify" in content.lower()
        assert "blocked" in content.lower() or "human action" in content.lower()

    def test_deployed_claude_md_has_verify_instruction(self):
        """Deployed DM CLAUDE.md must contain the verification instruction."""
        path = REPO_ROOT / ".squidsquad" / "dm" / "CLAUDE.md"
        if not path.exists():
            pytest.skip("DM not installed")
        content = path.read_text(encoding="utf-8")
        assert "pending-human-setup" in content
        assert "verify" in content.lower()
