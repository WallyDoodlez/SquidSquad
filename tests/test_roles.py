"""Static analysis: Verify role definitions and directory structure.

Checks that configured agents have their required directories and files.
"""

import re
import pytest
from pathlib import Path

from conftest import SQUIDSQUAD_DIR, REFERENCES_DIR


def _get_configured_dev_agents():
    """Read dev agents from config.md."""
    config = (SQUIDSQUAD_DIR / "config.md").read_text(encoding="utf-8")
    match = re.search(r'\*\*Dev Agents\*\*:\s*(.+)', config)
    if not match:
        return []
    return [a.strip() for a in match.group(1).split(",")]


class TestRoleDirectories:
    """Verify each configured role has required directories."""

    @pytest.fixture(autouse=True, scope="class")
    def _agents(self, request):
        request.cls.dev_agents = _get_configured_dev_agents()

    def test_dev_agent_dirs_exist(self):
        for agent in self.dev_agents:
            agent_dir = SQUIDSQUAD_DIR / agent
            assert agent_dir.is_dir(), f"Missing agent directory: .squidsquad/{agent}/"

    def test_dev_agent_has_claude_md(self):
        for agent in self.dev_agents:
            claude_md = SQUIDSQUAD_DIR / agent / "CLAUDE.md"
            assert claude_md.exists(), f"Missing CLAUDE.md for agent: {agent}"

    def test_dev_agent_has_working_state(self):
        for agent in self.dev_agents:
            ws = SQUIDSQUAD_DIR / agent / "working-state.md"
            assert ws.exists(), f"Missing working-state.md for agent: {agent}"

    def test_pm_dir_exists(self):
        assert (SQUIDSQUAD_DIR / "pm").is_dir(), "Missing pm/ directory"

    def test_pm_has_claude_md(self):
        assert (SQUIDSQUAD_DIR / "pm" / "CLAUDE.md").exists(), "Missing pm/CLAUDE.md"


class TestRoleEntryFiles:
    """Verify role entry files exist in the role directory registry.

    Q-new22 moved every role's SOUL.md + CLAUDE.md into its self-contained
    directory at `references/roles/<role>/`. The legacy
    `references/sub-skills/{souls,roles}/` layout has been retired.
    """

    def test_dev_entry_exists(self):
        path = REFERENCES_DIR / "roles" / "dev" / "CLAUDE.md"
        assert path.exists(), "Missing references/roles/dev/CLAUDE.md"

    def test_pm_entry_exists(self):
        path = REFERENCES_DIR / "roles" / "pm" / "CLAUDE.md"
        assert path.exists(), "Missing references/roles/pm/CLAUDE.md"

    def test_all_role_claude_md_files_exist(self):
        expected = {"pm", "dm", "designer", "dev", "qa"}
        missing = {
            role for role in expected
            if not (REFERENCES_DIR / "roles" / role / "CLAUDE.md").exists()
        }
        assert not missing, f"Missing CLAUDE.md for roles: {missing}"

    def test_soul_files_exist(self):
        expected = {"pm", "dm", "designer", "dev", "qa"}
        missing = {
            role for role in expected
            if not (REFERENCES_DIR / "roles" / role / "SOUL.md").exists()
        }
        assert not missing, f"Missing SOUL.md for roles: {missing}"

    def test_legacy_souls_dir_is_gone(self):
        """Defensive — the legacy sub-skills/souls/ must not reappear."""
        legacy = REFERENCES_DIR / "sub-skills" / "souls"
        assert not legacy.exists(), (
            f"Legacy souls directory should not exist after Q-new22: {legacy}"
        )

    def test_legacy_roles_dir_is_gone(self):
        """Defensive — the legacy sub-skills/roles/ must not reappear."""
        legacy = REFERENCES_DIR / "sub-skills" / "roles"
        assert not legacy.exists(), (
            f"Legacy roles directory should not exist after Q-new22: {legacy}"
        )
