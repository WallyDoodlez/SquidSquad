#!/usr/bin/env python3
"""SquidSquad Event Catalog -single source of truth for all event types.

Three-tier authority model:
  - emitted: scripts actively emit these (ground truth)
  - recognized: planned/expected, referenced by filters but not yet emitted
  - unknown: any event type not in either tier (treated as error)

Usage:
    python scripts/event_catalog.py list [--tier emitted|recognized|all]
    python scripts/event_catalog.py validate <event_type>
    python scripts/event_catalog.py describe <event_type>
    python scripts/event_catalog.py --help
"""

import json
import sys


# ---------------------------------------------------------------------------
# Emission Catalog (three-tier)
# ---------------------------------------------------------------------------

# Tier 1: emitted -scripts emit these (hard ground truth from tracker.py,
# git_ops.py, cycle_pre.py, cycle_post.py)
EMITTED = {
    "cycle-start": {
        "description": "Agent cycle began -mechanical pre-cycle complete",
        "source": "cycle_pre.py",
        "payload_fields": ["cycle_number"],
    },
    "cycle-end": {
        "description": "Agent cycle finished -post-cycle commit/push done",
        "source": "cycle_post.py",
        "payload_fields": ["cycle_number", "cycle_type"],
    },
    "git-pull": {
        "description": "Agent pulled latest changes from remote",
        "source": "git_ops.py",
        "payload_fields": ["result"],
    },
    "git-push": {
        "description": "Agent pushed commits to remote",
        "source": "git_ops.py",
        "payload_fields": ["branch"],
    },
    "git-commit": {
        "description": "Agent created a local commit",
        "source": "git_ops.py",
        "payload_fields": ["message", "branch", "files_changed", "commit_type"],
    },
    "status-transition": {
        "description": "Tracker item changed status (e.g. approved -> in-progress)",
        "source": "tracker.py",
        "payload_fields": ["issue_number", "from", "to"],
    },
    "tracker-comment": {
        "description": "Agent posted a comment on a tracker item",
        "source": "tracker.py",
        "payload_fields": ["issue_number", "role", "message_preview"],
    },
    "branch-checkout": {
        "description": "Agent checked out a feature branch for a task",
        "source": "git_ops.py",
        "payload_fields": ["branch", "task_number"],
    },
    "pr-create": {
        "description": "Agent created a pull request for a feature branch",
        "source": "git_ops.py",
        "payload_fields": ["pr_number", "title", "branch"],
    },
    "pr-merge": {
        "description": "A pull request was merged (code landed on main) — DEPRECATED: use pr-merged from harness",
        "source": "git_ops.py",
        "payload_fields": ["pr_number"],
    },
    "pr-merged": {
        "description": "Harness merged a PR — full payload with files changed",
        "source": "harness.py",
        "payload_fields": ["pr_number", "branch", "issue_number", "files_changed", "success"],
    },
    "compose-completed": {
        "description": "Harness ran compose.py deploy-all after a merge touching references/",
        "source": "harness.py",
        "payload_fields": ["success", "error", "trigger_pr"],
    },
    # #9873-A D6: the prior single "ack" event type is split into two
    # distinct types — both EMITTED. ack-cursor is the cursor-advance signal
    # emitted by agent infrastructure after the harness delivers events;
    # ack-stop is the stop-confirmation signal emitted by an agent when it
    # has accepted a stop intent.
    "ack-cursor": {
        "description": "Agent acknowledges event delivery — advances the harness consumer cursor past event_id for role. Emitted by agent infrastructure after a poll batch.",
        "source": "event_bus.py ack_cursor()",
        "payload_fields": ["event_id", "role"],
    },
    "ack-stop": {
        "description": "Agent acknowledges a stop request — confirms the agent has accepted an intent=stopping transition. Result field carries the disposition (e.g. \"stop-confirmed\").",
        "source": "event_bus.py ack_stop()",
        "payload_fields": ["event_id", "result"],
    },
}

# Tier 2: recognized -planned/expected, referenced by filters but not yet
# emitted by scripts. These are allowed in config, no error.
RECOGNIZED = {
    "verification-failed": {
        "description": "QA or PM verification found gaps -task sent back to dev",
        "planned_source": "qa/pm verification step",
        "payload_fields": ["issue_number", "findings"],
    },
    "verification-passed": {
        "description": "QA or PM verification passed -task ready for shipping",
        "planned_source": "qa/pm verification step",
        "payload_fields": ["issue_number"],
    },
    "agent-health": {
        "description": "Agent health status changed (alive, stalled, dead)",
        "planned_source": "harness.py health poller",
        "payload_fields": ["role", "status", "previous_status"],
    },
    "phase-change": {
        "description": "Task moved to a new lifecycle phase (planning, execution, etc.)",
        "planned_source": "harness.py or pm cycle",
        "payload_fields": ["issue_number", "phase"],
    },
    "request-merge": {
        "description": "Agent requested harness to merge a PR — audit trail",
        "planned_source": "harness.py (logged on POST /merge)",
        "payload_fields": ["pr_number", "branch", "role"],
    },
    # L1 event types for event-driven architecture (#7630 Phase 2)
    "assigned-to": {
        "description": "Work item assigned to a role — agent should wake and process",
        "planned_source": "harness.py ExternalActivityDetector",
        "payload_fields": ["issue_number", "title", "target_alias", "event_context"],
    },
    "stop-requested": {
        "description": "Harness requests agent to checkpoint and exit cleanly",
        "planned_source": "harness.py intent API",
        "payload_fields": ["reason"],
    },
    "shipped": {
        "description": "Item shipped — agent may need to update state or celebrate",
        "planned_source": "harness.py (on tracker transition to shipped)",
        "payload_fields": ["issue_number", "title", "version"],
    },
    "version-bump": {
        "description": "Version bump completed — agents should note new version",
        "planned_source": "harness.py (after DM version bump)",
        "payload_fields": ["old_version", "new_version", "items_included"],
    },
    # #9873-A D6: the prior "ack" RECOGNIZED entry is REPLACED by the
    # "ack-cursor" and "ack-stop" EMITTED entries above (#9873-A).
}


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------


def get_tier(event_type):
    """Return the tier of an event type: 'emitted', 'recognized', or 'unknown'."""
    if event_type in EMITTED:
        return "emitted"
    if event_type in RECOGNIZED:
        return "recognized"
    return "unknown"


def is_valid(event_type):
    """Return True if the event type is in emitted or recognized tier."""
    return event_type in EMITTED or event_type in RECOGNIZED


def get_description(event_type):
    """Return the human-readable description for an event type, or None."""
    entry = EMITTED.get(event_type) or RECOGNIZED.get(event_type)
    return entry["description"] if entry else None


def all_event_types():
    """Return set of all known event types (emitted + recognized)."""
    return set(EMITTED.keys()) | set(RECOGNIZED.keys())


def list_by_tier(tier="all"):
    """Return dict of event entries filtered by tier."""
    if tier == "emitted":
        return dict(EMITTED)
    if tier == "recognized":
        return dict(RECOGNIZED)
    # all
    combined = dict(EMITTED)
    combined.update(RECOGNIZED)
    return combined


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        return 0

    cmd = args[0]

    if cmd == "list":
        tier = "all"
        if "--tier" in args:
            idx = args.index("--tier")
            if idx + 1 < len(args):
                tier = args[idx + 1]
        entries = list_by_tier(tier)
        for name, entry in sorted(entries.items()):
            t = get_tier(name)
            print(f"  [{t}] {name}: {entry['description']}")
        print(f"\nTotal: {len(entries)} event type(s)")
        return 0

    if cmd == "validate":
        if len(args) < 2:
            print("Usage: event_catalog.py validate <event_type>", file=sys.stderr)
            return 2
        event_type = args[1]
        tier = get_tier(event_type)
        if tier == "unknown":
            print(f"INVALID: '{event_type}' is not a known event type", file=sys.stderr)
            return 1
        print(f"VALID: '{event_type}' (tier: {tier})")
        return 0

    if cmd == "describe":
        if len(args) < 2:
            print("Usage: event_catalog.py describe <event_type>", file=sys.stderr)
            return 2
        event_type = args[1]
        entry = EMITTED.get(event_type) or RECOGNIZED.get(event_type)
        if not entry:
            print(f"Unknown event type: '{event_type}'", file=sys.stderr)
            return 1
        tier = get_tier(event_type)
        print(json.dumps({"event_type": event_type, "tier": tier, **entry}, indent=2))
        return 0

    print(f"Unknown command: {cmd}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
