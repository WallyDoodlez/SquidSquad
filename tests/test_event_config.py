"""Tests for config.py Event Reactions parsing (#5868 AC-2)."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config


class TestGetEventReactions:
    def test_parses_valid_section(self):
        text = """## Event Reactions

### skill
- **emits**: status-transition, tracker-comment
- **reacts-to**: pr-merge, verification-failed

### pm
- **emits**: status-transition
- **reacts-to**: pr-merge, status-transition, agent-health
"""
        result = config.get_event_reactions(text)
        assert "skill" in result
        assert "pm" in result
        assert result["skill"]["emits"] == ["status-transition", "tracker-comment"]
        assert result["skill"]["reacts_to"] == ["pr-merge", "verification-failed"]
        assert result["pm"]["reacts_to"] == ["pr-merge", "status-transition", "agent-health"]

    def test_missing_section_returns_empty(self):
        text = "## Other Section\n- **Field**: value\n"
        assert config.get_event_reactions(text) == {}

    def test_empty_section_returns_empty(self):
        text = "## Event Reactions\n\n## Next Section\n"
        assert config.get_event_reactions(text) == {}

    def test_malformed_lines_skipped(self):
        text = """## Event Reactions

### skill
- **emitz**: typo-field
- **emits**: status-transition
some random text
- **reacts-to**: pr-merge
"""
        result = config.get_event_reactions(text)
        assert result["skill"]["emits"] == ["status-transition"]
        assert result["skill"]["reacts_to"] == ["pr-merge"]

    def test_empty_emits_list(self):
        text = """## Event Reactions

### dm
- **emits**:
- **reacts-to**: status-transition
"""
        result = config.get_event_reactions(text)
        assert result["dm"]["emits"] == []
        assert result["dm"]["reacts_to"] == ["status-transition"]


class TestGetEventFiltersForRole:
    def test_returns_set_for_configured_role(self):
        text = """## Event Reactions

### skill
- **emits**: status-transition
- **reacts-to**: pr-merge, verification-failed
"""
        result = config.get_event_filters_for_role("skill", text)
        assert result == {"pr-merge", "verification-failed"}

    def test_returns_none_for_missing_section(self):
        text = "## Other\n- **Foo**: bar\n"
        assert config.get_event_filters_for_role("skill", text) is None

    def test_returns_none_for_missing_role(self):
        text = """## Event Reactions

### pm
- **emits**: status-transition
- **reacts-to**: pr-merge
"""
        assert config.get_event_filters_for_role("skill", text) is None

    def test_returns_none_for_empty_reacts_to(self):
        """Empty reacts-to = not configured = use defaults."""
        text = """## Event Reactions

### skill
- **emits**: status-transition
- **reacts-to**:
"""
        assert config.get_event_filters_for_role("skill", text) is None


class TestGracefulDegradation:
    """AC-7: Verify graceful degradation when section is absent or malformed."""

    def test_absent_section_returns_empty(self):
        assert config.get_event_reactions("# Config\n- **Version**: 1.0\n") == {}

    def test_none_text_reads_from_disk(self):
        # Should not crash when text is None (reads actual config.md)
        result = config.get_event_reactions(None)
        assert isinstance(result, dict)

    def test_garbage_section_returns_partial(self):
        text = """## Event Reactions
not valid markdown at all
### skill
completely wrong format
- **emits**: status-transition
"""
        result = config.get_event_reactions(text)
        assert result.get("skill", {}).get("emits") == ["status-transition"]
