#!/usr/bin/env python3
"""SquidSquad Event Validator -- cross-agent event contract validation.

Deterministic Python validation of the ## Event Reactions section in config.md.
Runs after every compose (single-role or deploy-all). Validates contracts
against the event catalog to catch wiring errors before they reach agents.

Detects:
  - Orphaned emits: role emits something nothing consumes (warning)
  - Missing consumers: role reacts-to something nothing emits and not recognized (error)
  - Hallucinated events: unknown tier event type (error)
  - Reaction cycles: A reacts to B's emit, B reacts to A's emit (error)

All failures presented in plain human-readable process-gap language using
catalog descriptions. Raw event names do not appear in user-facing output.

Usage:
    python scripts/event_validator.py validate [--config PATH]
    python scripts/event_validator.py --help

Exit codes:
    0 -- all checks pass (warnings are OK)
    1 -- errors found (must fix before deploying)
    2 -- usage error
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from event_catalog import EMITTED, RECOGNIZED, get_tier, get_description, all_event_types
from config import get_event_reactions


# ---------------------------------------------------------------------------
# Validation checks
# ---------------------------------------------------------------------------


class Finding:
    """A single validation finding."""

    __slots__ = ("severity", "check", "message", "detail")

    def __init__(self, severity, check, message, detail=""):
        self.severity = severity  # "error" or "warning"
        self.check = check
        self.message = message
        self.detail = detail

    def __str__(self):
        tag = "ERROR" if self.severity == "error" else "WARNING"
        line = f"  {tag}: {self.message}"
        if self.detail:
            line += f"\n         {self.detail}"
        return line


def _describe(event_type):
    """Get human-readable description for an event type."""
    desc = get_description(event_type)
    if desc:
        return f'"{desc}"'
    return f"'{event_type}' (unknown event)"


def check_hallucinated_events(reactions):
    """Check for event types not in the catalog (unknown tier)."""
    findings = []
    known = all_event_types()
    for role, data in reactions.items():
        for event_type in data.get("emits", []):
            if event_type not in known:
                findings.append(Finding(
                    "error", "hallucinated",
                    f"{role} claims to emit an event the system doesn't recognize.",
                    f"An unrecognized event type was found in {role}'s emits list. "
                    f"Check the event catalog for valid types, or add the new type to the catalog.",
                ))
        for event_type in data.get("reacts_to", []):
            if event_type not in known:
                findings.append(Finding(
                    "error", "hallucinated",
                    f"{role} is configured to react to an event the system doesn't recognize.",
                    f"An unrecognized event type was found in {role}'s reacts-to list. "
                    f"Check the event catalog for valid types, or remove the unknown entry.",
                ))
    return findings


def check_missing_consumers(reactions):
    """Check for roles reacting to events that nothing emits and aren't recognized."""
    findings = []
    # Collect all emitted event types across all roles
    all_emits = set()
    for data in reactions.values():
        all_emits.update(data.get("emits", []))
    # Also include infrastructure emitted events (from scripts, not role contracts)
    all_emits.update(EMITTED.keys())

    for role, data in reactions.items():
        for event_type in data.get("reacts_to", []):
            if event_type not in all_emits and event_type not in RECOGNIZED:
                desc = _describe(event_type)
                findings.append(Finding(
                    "error", "missing-consumer",
                    f"{role} expects to react to {desc}, but nothing in the system produces it.",
                    f"Either add an emitter for this event or remove it from {role}'s reacts-to list.",
                ))
    return findings


def check_orphaned_emits(reactions):
    """Check for roles emitting events that no other role consumes."""
    findings = []
    # Collect all reacts-to event types across all roles
    all_reacts = set()
    for data in reactions.values():
        all_reacts.update(data.get("reacts_to", []))

    for role, data in reactions.items():
        for event_type in data.get("emits", []):
            if event_type not in all_reacts:
                desc = _describe(event_type)
                findings.append(Finding(
                    "warning", "orphaned-emit",
                    f"{role} produces {desc}, but no other role is configured to react to it.",
                    f"This event is emitted but never consumed. It may be unused or a missing subscription.",
                ))
    return findings


def check_reaction_cycles(reactions):
    """Check for circular reaction chains (A reacts to B's emit, B reacts to A's emit)."""
    findings = []
    roles = list(reactions.keys())

    for i, role_a in enumerate(roles):
        emits_a = set(reactions[role_a].get("emits", []))
        reacts_a = set(reactions[role_a].get("reacts_to", []))

        for role_b in roles[i + 1:]:
            emits_b = set(reactions[role_b].get("emits", []))
            reacts_b = set(reactions[role_b].get("reacts_to", []))

            # A emits something B reacts to AND B emits something A reacts to
            a_triggers_b = emits_a & reacts_b
            b_triggers_a = emits_b & reacts_a

            if a_triggers_b and b_triggers_a:
                # Check if any overlapping event could cause a loop
                # (same event type in both directions)
                loop_events = a_triggers_b & b_triggers_a
                if loop_events:
                    for evt in loop_events:
                        desc = _describe(evt)
                        findings.append(Finding(
                            "error", "reaction-cycle",
                            f"Potential infinite loop: {role_a} and {role_b} both emit and react to {desc}.",
                            f"If {role_a} emits this event, {role_b} reacts and may emit it back, "
                            f"causing {role_a} to react again. Break the cycle by removing one side.",
                        ))
    return findings


# ---------------------------------------------------------------------------
# Main validation entry point
# ---------------------------------------------------------------------------


def validate(config_text=None):
    """Run all validation checks on the Event Reactions section.

    Returns (findings, has_errors). findings is a list of Finding objects.
    has_errors is True if any finding has severity "error".
    """
    reactions = get_event_reactions(config_text)
    if not reactions:
        return [], False  # No section = no validation needed

    findings = []
    findings.extend(check_hallucinated_events(reactions))
    findings.extend(check_missing_consumers(reactions))
    findings.extend(check_orphaned_emits(reactions))
    findings.extend(check_reaction_cycles(reactions))

    has_errors = any(f.severity == "error" for f in findings)
    return findings, has_errors


def validate_and_print(config_text=None):
    """Run validation and print results. Returns exit code (0 or 1)."""
    findings, has_errors = validate(config_text)

    if not findings:
        print("Event contract validation passed -- no issues found.")
        return 0

    errors = [f for f in findings if f.severity == "error"]
    warnings = [f for f in findings if f.severity == "warning"]

    if warnings:
        print(f"\n--- Warnings ({len(warnings)}) ---")
        for f in warnings:
            print(str(f))

    if errors:
        print(f"\n--- Errors ({len(errors)}) ---")
        for f in errors:
            print(str(f))
        print(f"\nValidation FAILED: {len(errors)} error(s), {len(warnings)} warning(s).")
        print("Fix the errors above and re-run compose.")
        return 1

    print(f"\nValidation passed with {len(warnings)} warning(s).")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        return 0

    cmd = args[0]

    if cmd == "validate":
        config_text = None
        if "--config" in args:
            idx = args.index("--config")
            if idx + 1 < len(args):
                config_text = Path(args[idx + 1]).read_text(encoding="utf-8")
        return validate_and_print(config_text)

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
