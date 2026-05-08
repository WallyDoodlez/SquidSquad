"""Tests for references/scripts/event_validator.py — cross-agent validation (#5868 AC-4)."""

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from event_validator import (
    check_hallucinated_events,
    check_missing_consumers,
    check_orphaned_emits,
    check_reaction_cycles,
    validate,
)


class TestHallucinatedEvents:
    def test_valid_events_pass(self):
        reactions = {"skill": {"emits": ["status-transition"], "reacts_to": ["pr-merge"]}}
        findings = check_hallucinated_events(reactions)
        assert len(findings) == 0

    def test_unknown_emit_is_error(self):
        reactions = {"skill": {"emits": ["fake-event"], "reacts_to": []}}
        findings = check_hallucinated_events(reactions)
        assert len(findings) == 1
        assert findings[0].severity == "error"
        assert findings[0].check == "hallucinated"

    def test_unknown_react_is_error(self):
        reactions = {"skill": {"emits": [], "reacts_to": ["nonexistent"]}}
        findings = check_hallucinated_events(reactions)
        assert len(findings) == 1
        assert findings[0].severity == "error"

    def test_recognized_events_pass(self):
        reactions = {"pm": {"emits": [], "reacts_to": ["verification-failed", "agent-health"]}}
        findings = check_hallucinated_events(reactions)
        assert len(findings) == 0

    def test_no_raw_event_names_in_output(self):
        """AC-4 fix: hallucinated check must not expose raw event names."""
        reactions = {"skill": {"emits": ["my-secret-event"], "reacts_to": []}}
        findings = check_hallucinated_events(reactions)
        assert len(findings) == 1
        assert "my-secret-event" not in findings[0].detail


class TestMissingConsumers:
    def test_reacting_to_emitted_event_passes(self):
        reactions = {
            "skill": {"emits": ["status-transition"], "reacts_to": []},
            "pm": {"emits": [], "reacts_to": ["status-transition"]},
        }
        findings = check_missing_consumers(reactions)
        assert len(findings) == 0

    def test_reacting_to_recognized_event_passes(self):
        reactions = {"pm": {"emits": [], "reacts_to": ["verification-failed"]}}
        findings = check_missing_consumers(reactions)
        assert len(findings) == 0

    def test_reacting_to_infrastructure_event_passes(self):
        """Infrastructure events (EMITTED) are always available."""
        reactions = {"pm": {"emits": [], "reacts_to": ["cycle-start"]}}
        findings = check_missing_consumers(reactions)
        assert len(findings) == 0


class TestOrphanedEmits:
    def test_consumed_emit_passes(self):
        reactions = {
            "skill": {"emits": ["status-transition"], "reacts_to": []},
            "pm": {"emits": [], "reacts_to": ["status-transition"]},
        }
        findings = check_orphaned_emits(reactions)
        assert len(findings) == 0

    def test_unconsumed_emit_is_warning(self):
        reactions = {
            "skill": {"emits": ["tracker-comment"], "reacts_to": []},
            "pm": {"emits": [], "reacts_to": ["pr-merge"]},
        }
        findings = check_orphaned_emits(reactions)
        assert len(findings) == 1
        assert findings[0].severity == "warning"
        assert findings[0].check == "orphaned-emit"


class TestReactionCycles:
    def test_no_cycle_passes(self):
        reactions = {
            "skill": {"emits": ["status-transition"], "reacts_to": ["pr-merge"]},
            "pm": {"emits": ["pr-merge"], "reacts_to": ["status-transition"]},
        }
        # Different event types in each direction = no same-event cycle
        findings = check_reaction_cycles(reactions)
        assert len(findings) == 0

    def test_infrastructure_event_cycle_is_warning(self):
        """Infrastructure events (EMITTED tier) downgrade to warning — cascade protected."""
        reactions = {
            "skill": {"emits": ["status-transition"], "reacts_to": ["status-transition"]},
            "pm": {"emits": ["status-transition"], "reacts_to": ["status-transition"]},
        }
        findings = check_reaction_cycles(reactions)
        assert len(findings) >= 1
        assert findings[0].severity == "warning"  # Not error — cascade protected
        assert findings[0].check == "reaction-cycle"

    def test_non_infrastructure_cycle_is_error(self):
        """Non-infrastructure bidirectional cycles are still errors."""
        reactions = {
            "skill": {"emits": ["verification-failed"], "reacts_to": ["verification-failed"]},
            "pm": {"emits": ["verification-failed"], "reacts_to": ["verification-failed"]},
        }
        findings = check_reaction_cycles(reactions)
        assert len(findings) >= 1
        assert findings[0].severity == "error"

    def test_single_role_no_cycle(self):
        """Single role can't form a pairwise cycle."""
        reactions = {
            "skill": {"emits": ["status-transition"], "reacts_to": ["status-transition"]},
        }
        findings = check_reaction_cycles(reactions)
        assert len(findings) == 0


class TestValidateIntegration:
    def test_empty_reactions_passes(self):
        findings, has_errors = validate("## Nothing\n")
        assert findings == []
        assert has_errors is False

    def test_valid_config_passes(self):
        config = """## Event Reactions

### skill
- **emits**: status-transition
- **reacts-to**: pr-merge

### pm
- **emits**: status-transition
- **reacts-to**: pr-merge, status-transition
"""
        findings, has_errors = validate(config)
        errors = [f for f in findings if f.severity == "error"]
        # No hallucinated or missing consumer errors expected
        assert not any(f.check == "hallucinated" for f in errors)
        assert not any(f.check == "missing-consumer" for f in errors)

    def test_hallucinated_config_has_errors(self):
        config = """## Event Reactions

### skill
- **emits**: totally-fake-event
- **reacts-to**: pr-merge
"""
        findings, has_errors = validate(config)
        assert has_errors is True
        assert any(f.check == "hallucinated" for f in findings)
