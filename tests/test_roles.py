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
        checked = 0
        for agent in self.dev_agents:
            agent_dir = SQUIDSQUAD_DIR / agent
            ws = agent_dir / "working-state.md"
            if not ws.exists():
                # In multi-clone setups, some agents run in other
                # clones and don't have working-state.md here (#4876).
                continue
            checked += 1
        # At least one local agent must have working state
        assert checked > 0, "No dev agents have working-state.md locally"

    def test_pm_dir_exists(self):
        assert (SQUIDSQUAD_DIR / "pm").is_dir(), "Missing pm/ directory"

    def test_pm_has_claude_md(self):
        assert (SQUIDSQUAD_DIR / "pm" / "CLAUDE.md").exists(), "Missing pm/CLAUDE.md"


class TestRoleEntryFiles:
    """Verify role entry files exist in the role directory registry.

    Q-new22 moved every role's SOUL.md + CLAUDE.md into its self-contained
    directory at `references/roles/<role>/`. The legacy `references/sub-skills/souls/`
    directory was retired. `references/sub-skills/roles/` remains active as the home
    for per-role sub-skill markdown files used by compose.py.
    """

    def test_dev_entry_exists(self):
        path = REFERENCES_DIR / "roles" / "worker" / "instructions.md"
        assert path.exists(), "Missing references/roles/worker/instructions.md"

    def test_pm_entry_exists(self):
        path = REFERENCES_DIR / "roles" / "pm" / "instructions.md"
        assert path.exists(), "Missing references/roles/pm/instructions.md"

    def test_all_role_claude_md_files_exist(self):
        expected = {"pm", "dm", "worker", "verifier"}
        missing = {
            role for role in expected
            if not (REFERENCES_DIR / "roles" / role / "instructions.md").exists()
        }
        assert not missing, f"Missing instructions.md for roles: {missing}"

    def test_soul_files_exist(self):
        expected = {"pm", "dm", "worker", "verifier"}
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

    def test_role_sub_skills_dir_exists(self):
        """Role-specific sub-skills live under sub-skills/roles/."""
        roles_ss = REFERENCES_DIR / "sub-skills" / "roles"
        assert roles_ss.exists(), "Missing sub-skills/roles/ directory"
