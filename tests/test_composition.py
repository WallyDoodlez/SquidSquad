"""Static analysis: Verify sub-skill composition in CLAUDE.md.

Checks that every sub-skill section is properly opened and closed,
and that sub-skill names are consistent.
"""

import re
import pytest
from pathlib import Path

from conftest import SQUIDSQUAD_DIR, REFERENCES_DIR


def _extract_sub_skill_markers(text):
    """Extract all sub-skill open/close markers from text."""
    opens = re.findall(r'<!-- sub-skill: (\S+) -->', text)
    closes = re.findall(r'<!-- /sub-skill: (\S+) -->', text)
    return opens, closes


class TestSkillComposition:
    """Verify sub-skill markers in skill/CLAUDE.md."""

    def test_all_sub_skills_closed(self, skill_claude_md):
        opens, closes = _extract_sub_skill_markers(skill_claude_md)
        unclosed = set(opens) - set(closes)
        assert not unclosed, f"Unclosed sub-skill sections: {unclosed}"

    def test_all_closes_have_opens(self, skill_claude_md):
        opens, closes = _extract_sub_skill_markers(skill_claude_md)
        unopened = set(closes) - set(opens)
        assert not unopened, f"Close markers without matching open: {unopened}"

    def test_no_duplicate_opens(self, skill_claude_md):
        opens, _ = _extract_sub_skill_markers(skill_claude_md)
        dupes = [name for name in set(opens) if opens.count(name) > 1]
        assert not dupes, f"Duplicate sub-skill opens: {dupes}"

    def test_markers_properly_nested(self, skill_claude_md):
        """Verify open/close markers appear in correct order (no interleaving)."""
        stack = []
        for match in re.finditer(r'<!-- (/?)sub-skill: (\S+) -->', skill_claude_md):
            is_close = match.group(1) == "/"
            name = match.group(2)
            if is_close:
                assert stack, f"Close marker for '{name}' with empty stack"
                assert stack[-1] == name, (
                    f"Close marker for '{name}' but last open was '{stack[-1]}'"
                )
                stack.pop()
            else:
                stack.append(name)
        assert not stack, f"Unclosed sub-skill sections at end: {stack}"


class TestAgentInstructionsComposition:
    """Verify sub-skill markers in references/agent-instructions.md."""

    @pytest.fixture(autouse=True)
    def _load(self):
        path = REFERENCES_DIR / "agent-instructions.md"
        if not path.exists():
            pytest.skip("agent-instructions.md not found")
        self.content = path.read_text(encoding="utf-8")

    def test_all_sub_skills_closed(self):
        opens, closes = _extract_sub_skill_markers(self.content)
        unclosed = set(opens) - set(closes)
        assert not unclosed, f"Unclosed in agent-instructions.md: {unclosed}"

    def test_all_closes_have_opens(self):
        opens, closes = _extract_sub_skill_markers(self.content)
        unopened = set(closes) - set(opens)
        assert not unopened, f"Unopened closes in agent-instructions.md: {unopened}"
