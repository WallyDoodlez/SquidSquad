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
    """Verify catalog structure and core events (#7801: no hardcoded full sets)."""

    # Core events that must always exist — stable subset, not exhaustive.
    CORE_EMITTED = {
        "cycle-start", "cycle-end", "git-pull", "git-push", "git-commit",
        "status-transition", "tracker-comment", "pr-create",
    }
    CORE_RECOGNIZED = {
        "verification-failed", "verification-passed", "request-merge",
    }

    def test_emitted_tier_contains_core_events(self):
        actual = set(event_catalog.EMITTED.keys())
        missing = self.CORE_EMITTED - actual
        assert not missing, f"Core emitted events missing from catalog: {missing}"

    def test_recognized_tier_contains_core_events(self):
        """RECOGNIZED must contain core + L1 event-driven events (#7630).

        #9873-A D6: the previous shared ``ack`` RECOGNIZED entry was REPLACED
        by ``ack-cursor`` and ``ack-stop`` in the EMITTED tier (see the new
        TestAckEventTypes class below). Do not expect ``ack`` here anymore.
        """
        core = self.CORE_RECOGNIZED | {
            "assigned-to", "stop-requested", "shipped", "version-bump",
        }
        actual = set(event_catalog.RECOGNIZED.keys())
        missing = core - actual
        assert not missing, f"Core recognized events missing: {missing}"

    def test_emitted_tier_is_non_empty(self):
        assert len(event_catalog.EMITTED) >= len(self.CORE_EMITTED)

    def test_recognized_tier_is_non_empty(self):
        assert len(event_catalog.RECOGNIZED) >= len(self.CORE_RECOGNIZED)

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


class TestAckEventTypes9873A:
    """#9873-A D6 / AC-5 / AC-6: the prior shared ``ack`` event type is split
    into ``ack-cursor`` and ``ack-stop``, both registered in the EMITTED tier.
    """

    def test_ac5_ack_cursor_in_emitted(self):
        """AC-5: ack-cursor catalog entry — EMITTED tier."""
        assert "ack-cursor" in event_catalog.EMITTED
        entry = event_catalog.EMITTED["ack-cursor"]
        assert entry["payload_fields"] == ["event_id", "role"]
        # Description must identify it as the cursor-advance signal
        assert "cursor" in entry["description"].lower()

    def test_ac6_ack_stop_in_emitted(self):
        """AC-6: ack-stop catalog entry — EMITTED tier."""
        assert "ack-stop" in event_catalog.EMITTED
        entry = event_catalog.EMITTED["ack-stop"]
        assert entry["payload_fields"] == ["event_id", "result"]
        # Description must identify it as the stop-confirmation signal
        assert "stop" in entry["description"].lower()

    def test_ac6_old_ack_entry_removed(self):
        """AC-6: the old shared ``ack`` RECOGNIZED entry MUST be removed."""
        assert "ack" not in event_catalog.RECOGNIZED
        assert "ack" not in event_catalog.EMITTED

    def test_both_classified_as_emitted(self):
        assert event_catalog.get_tier("ack-cursor") == "emitted"
        assert event_catalog.get_tier("ack-stop") == "emitted"
        assert event_catalog.is_valid("ack-cursor") is True
        assert event_catalog.is_valid("ack-stop") is True
