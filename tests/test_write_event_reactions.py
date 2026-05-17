"""Tests for config.py write_event_reactions() — #8392.

Covers: section replacement, section append, atomic write, round-trip
with get_event_reactions, empty/single-role inputs, and sort order.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_CONFIG_WITH_SECTION = """\
# SquidSquad Config

## General
- **Version**: 0.38.0

## Event Reactions

### pm
- **emits**: status-transition
- **reacts-to**: pr-merge

### skill
- **emits**: status-transition, tracker-comment
- **reacts-to**: pr-merge, verification-failed

## Other Section
- **Field**: value
"""

SAMPLE_CONFIG_WITHOUT_SECTION = """\
# SquidSquad Config

## General
- **Version**: 0.38.0

## Other Section
- **Field**: value
"""


# ---------------------------------------------------------------------------
# Tests — Replace existing section
# ---------------------------------------------------------------------------

class TestReplaceExistingSection:
    """write_event_reactions replaces ## Event Reactions when present."""

    def test_replaces_section_content(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITH_SECTION, encoding="utf-8")

        new_reactions = {
            "qa": {"emits": ["verification-passed"], "reacts_to": ["status-transition"]},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(new_reactions)

        result = config_file.read_text(encoding="utf-8")
        assert "### qa" in result
        assert "verification-passed" in result
        # Old roles should be gone
        assert "### pm" not in result
        assert "### skill" not in result

    def test_preserves_surrounding_sections(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITH_SECTION, encoding="utf-8")

        new_reactions = {
            "skill": {"emits": ["new-event"], "reacts_to": ["new-react"]},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(new_reactions)

        result = config_file.read_text(encoding="utf-8")
        # General section preserved
        assert "## General" in result
        assert "0.38.0" in result
        # Other section preserved
        assert "## Other Section" in result
        assert "- **Field**: value" in result


# ---------------------------------------------------------------------------
# Tests — Append when section absent
# ---------------------------------------------------------------------------

class TestAppendWhenAbsent:
    """write_event_reactions appends section when not present."""

    def test_appends_section_to_end(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITHOUT_SECTION, encoding="utf-8")

        reactions = {
            "pm": {"emits": ["status-transition"], "reacts_to": ["pr-merge"]},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(reactions)

        result = config_file.read_text(encoding="utf-8")
        assert "## Event Reactions" in result
        assert "### pm" in result
        assert "status-transition" in result
        # Original content preserved
        assert "## General" in result
        assert "## Other Section" in result

    def test_appended_section_is_at_end(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITHOUT_SECTION, encoding="utf-8")

        reactions = {
            "skill": {"emits": ["evt"], "reacts_to": ["react"]},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(reactions)

        result = config_file.read_text(encoding="utf-8")
        # Event Reactions should appear after Other Section
        other_idx = result.index("## Other Section")
        event_idx = result.index("## Event Reactions")
        assert event_idx > other_idx


# ---------------------------------------------------------------------------
# Tests — Atomic write behavior
# ---------------------------------------------------------------------------

class TestAtomicWrite:
    """write_event_reactions uses tmp file for atomic write."""

    def test_no_tmp_file_left_behind(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITHOUT_SECTION, encoding="utf-8")

        reactions = {"pm": {"emits": ["evt"], "reacts_to": ["react"]}}

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(reactions)

        tmp_file = config_file.with_suffix(".tmp")
        assert not tmp_file.exists(), ".tmp file should be cleaned up after atomic write"

    def test_config_file_updated(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITHOUT_SECTION, encoding="utf-8")

        reactions = {"pm": {"emits": ["evt"], "reacts_to": ["react"]}}

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(reactions)

        result = config_file.read_text(encoding="utf-8")
        assert "## Event Reactions" in result


# ---------------------------------------------------------------------------
# Tests — Round-trip with get_event_reactions
# ---------------------------------------------------------------------------

class TestRoundTrip:
    """write then read should produce the same data."""

    def test_single_role_round_trip(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITHOUT_SECTION, encoding="utf-8")

        reactions = {
            "skill": {"emits": ["status-transition", "tracker-comment"],
                      "reacts_to": ["pr-merge", "verification-failed"]},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(reactions)

        written_text = config_file.read_text(encoding="utf-8")
        parsed = config.get_event_reactions(written_text)

        assert parsed["skill"]["emits"] == ["status-transition", "tracker-comment"]
        assert parsed["skill"]["reacts_to"] == ["pr-merge", "verification-failed"]

    def test_multi_role_round_trip(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITHOUT_SECTION, encoding="utf-8")

        reactions = {
            "pm": {"emits": ["status-transition"], "reacts_to": ["pr-merge"]},
            "qa": {"emits": ["verification-passed"], "reacts_to": ["status-transition"]},
            "skill": {"emits": ["tracker-comment"], "reacts_to": ["task-approved"]},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(reactions)

        written_text = config_file.read_text(encoding="utf-8")
        parsed = config.get_event_reactions(written_text)

        assert set(parsed.keys()) == {"pm", "qa", "skill"}
        assert parsed["pm"]["emits"] == ["status-transition"]
        assert parsed["qa"]["reacts_to"] == ["status-transition"]
        assert parsed["skill"]["reacts_to"] == ["task-approved"]

    def test_replace_then_read_round_trip(self, tmp_path):
        """Replace existing section and verify read produces new data."""
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITH_SECTION, encoding="utf-8")

        new_reactions = {
            "dm": {"emits": ["delivery-complete"], "reacts_to": ["pending-ship"]},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(new_reactions)

        written_text = config_file.read_text(encoding="utf-8")
        parsed = config.get_event_reactions(written_text)

        assert set(parsed.keys()) == {"dm"}
        assert parsed["dm"]["emits"] == ["delivery-complete"]


# ---------------------------------------------------------------------------
# Tests — Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Edge cases for write_event_reactions."""

    def test_empty_reactions_dict(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITHOUT_SECTION, encoding="utf-8")

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions({})

        written_text = config_file.read_text(encoding="utf-8")
        assert "## Event Reactions" in written_text
        # No role headings
        assert "###" not in written_text.split("## Event Reactions")[1]

    def test_roles_sorted_alphabetically(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITHOUT_SECTION, encoding="utf-8")

        reactions = {
            "skill": {"emits": ["a"], "reacts_to": ["b"]},
            "dm": {"emits": ["c"], "reacts_to": ["d"]},
            "pm": {"emits": ["e"], "reacts_to": ["f"]},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(reactions)

        result = config_file.read_text(encoding="utf-8")
        dm_idx = result.index("### dm")
        pm_idx = result.index("### pm")
        skill_idx = result.index("### skill")
        assert dm_idx < pm_idx < skill_idx

    def test_empty_emits_and_reacts(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(SAMPLE_CONFIG_WITHOUT_SECTION, encoding="utf-8")

        reactions = {
            "qa": {"emits": [], "reacts_to": []},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(reactions)

        written_text = config_file.read_text(encoding="utf-8")
        assert "### qa" in written_text
        # Empty emits should produce "- **emits**: " (empty after colon)
        assert "- **emits**: \n" in written_text or "- **emits**:" in written_text

    def test_text_parameter_bypasses_file_read(self, tmp_path):
        """When text parameter is provided, don't read CONFIG_PATH."""
        config_file = tmp_path / "config.md"
        config_file.write_text("should be overwritten", encoding="utf-8")

        reactions = {
            "pm": {"emits": ["evt"], "reacts_to": ["react"]},
        }

        with patch.object(config, "CONFIG_PATH", config_file):
            config.write_event_reactions(reactions, text=SAMPLE_CONFIG_WITHOUT_SECTION)

        result = config_file.read_text(encoding="utf-8")
        assert "## General" in result  # From the text param, not from file
        assert "### pm" in result
