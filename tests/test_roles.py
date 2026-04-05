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
    """Verify role entry files exist in sub-skills."""

    def test_dev_entry_exists(self):
        path = REFERENCES_DIR / "sub-skills" / "roles" / "dev-agent.md"
        assert path.exists(), "Missing dev-agent.md entry file"

    def test_pm_entry_exists(self):
        path = REFERENCES_DIR / "sub-skills" / "roles" / "pm-agent.md"
        assert path.exists(), "Missing pm-agent.md entry file"

    def test_soul_files_exist(self):
        souls_dir = REFERENCES_DIR / "sub-skills" / "souls"
        expected = {"dev.md", "pm.md", "qa.md", "designer.md", "dm.md"}
        actual = {f.name for f in souls_dir.glob("*.md")} if souls_dir.exists() else set()
        missing = expected - actual
        assert not missing, f"Missing soul files: {missing}"
