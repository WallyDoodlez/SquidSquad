"""Tests for references/scripts/event_catalog.py — three-tier event catalog (#5868 AC-1)."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import event_catalog


class TestTierClassification:
    def test_emitted_events_are_emitted_tier(self):
        for event_type in event_catalog.EMITTED:
            assert event_catalog.get_tier(event_type) == "emitted"

    def test_recognized_events_are_recognized_tier(self):
        for event_type in event_catalog.RECOGNIZED:
            assert event_catalog.get_tier(event_type) == "recognized"

    def test_unknown_event_is_unknown_tier(self):
        assert event_catalog.get_tier("nonexistent-event") == "unknown"

    def test_is_valid_for_emitted(self):
        assert event_catalog.is_valid("status-transition") is True

    def test_is_valid_for_recognized(self):
        assert event_catalog.is_valid("verification-failed") is True

    def test_is_valid_for_unknown(self):
        assert event_catalog.is_valid("made-up-event") is False


class TestCatalogCompleteness:
    """Verify the catalog matches actual emit() calls in scripts."""

    def test_emitted_tier_has_expected_events(self):
        expected = {
            "cycle-start", "cycle-end", "git-pull", "git-push", "git-commit",
            "status-transition", "tracker-comment", "branch-checkout",
            "pr-create", "pr-merge", "pr-merged", "compose-completed",
        }
        assert set(event_catalog.EMITTED.keys()) == expected

    def test_recognized_tier_has_core_events(self):
        """RECOGNIZED must contain core events (subset check, not exact — #7801)."""
        core = {
            "verification-failed", "verification-passed", "request-merge",
            "assigned-to", "stop-requested", "shipped", "version-bump", "ack",
        }
        actual = set(event_catalog.RECOGNIZED.keys())
        missing = core - actual
        assert not missing, f"Core recognized events missing: {missing}"

    def test_all_event_types_is_union(self):
        all_types = event_catalog.all_event_types()
        assert all_types == set(event_catalog.EMITTED.keys()) | set(event_catalog.RECOGNIZED.keys())

    def test_no_overlap_between_tiers(self):
        overlap = set(event_catalog.EMITTED.keys()) & set(event_catalog.RECOGNIZED.keys())
        assert overlap == set(), f"Events in both tiers: {overlap}"


class TestDescriptions:
    def test_emitted_event_has_description(self):
        desc = event_catalog.get_description("status-transition")
        assert desc is not None
        assert len(desc) > 10

    def test_recognized_event_has_description(self):
        desc = event_catalog.get_description("verification-failed")
        assert desc is not None

    def test_unknown_event_returns_none(self):
        assert event_catalog.get_description("fake-event") is None

    def test_all_emitted_have_descriptions(self):
        for name, entry in event_catalog.EMITTED.items():
            assert "description" in entry, f"{name} missing description"
            assert len(entry["description"]) > 0

    def test_all_recognized_have_descriptions(self):
        for name, entry in event_catalog.RECOGNIZED.items():
            assert "description" in entry, f"{name} missing description"


class TestListByTier:
    def test_list_emitted_only(self):
        result = event_catalog.list_by_tier("emitted")
        assert "status-transition" in result
        assert "verification-failed" not in result

    def test_list_recognized_only(self):
        result = event_catalog.list_by_tier("recognized")
        assert "verification-failed" in result
        assert "status-transition" not in result

    def test_list_all(self):
        result = event_catalog.list_by_tier("all")
        assert "status-transition" in result
        assert "verification-failed" in result
