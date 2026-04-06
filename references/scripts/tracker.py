#!/usr/bin/env python3
"""SquidSquad tracker operations — single source of truth for labels and status flows.

Encodes the complete label taxonomy and legal status transitions.
Agents call this instead of constructing gh commands from prose.

Usage:
    python scripts/tracker.py list-bugs <role>
    python scripts/tracker.py list-features <role> [--status approved|in-progress|pending-test]
    python scripts/tracker.py create-bug --title <t> --body <b> --role <r> --severity <s> [--reporter <name>]
    python scripts/tracker.py create-feature --title <t> --body <b> --role <r> --priority <p> [--reporter <name>]
    python scripts/tracker.py transition <number> <from-status> <to-status>
    python scripts/tracker.py comment <number> --role <r> --message <m>
    python scripts/tracker.py get-labels <number>
    python scripts/tracker.py get-state <number>
    python scripts/tracker.py close <number>
    python scripts/tracker.py check-gh                   # Verify gh access
    python scripts/tracker.py --help
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

# === LABEL TAXONOMY (single source of truth) ===

TYPE_LABELS = {"bug": "type:bug", "feature": "type:feature"}

PRIORITY_LABELS = {
    "high": "priority:high",
    "medium": "priority:medium",
    "low": "priority:low",
}

STATUS_LABELS = {
    "open": "status:open",
    "pending": "status:pending",
    "planning": "status:planning",
    "planned": "status:planned",
    "approved": "status:approved",
    "in-progress": "status:in-progress",
    "pending-test": "status:pending-test",
    "pending-ship": "status:pending-ship",
    "shipped": "status:shipped",
}

SEVERITY_LABELS = {
    "high": "severity:high",
    "medium": "severity:medium",
    "low": "severity:low",
}

DESIGN_LABELS = {
    "needed": "design:needed",
    "in-progress": "design:in-progress",
    "complete": "design:complete",
}

SPECIAL_LABELS = {"squidsquad", "improvement-scan", "squidsquad-test"}

# === LEGAL STATUS TRANSITIONS (pessimistic enforcement) ===

LEGAL_TRANSITIONS = {
    "status:open": {"status:pending-test", "status:in-progress"},
    "status:pending": {"status:planning", "status:approved"},
    "status:planning": {"status:planned"},
    "status:planned": {"status:approved"},
    "status:approved": {"status:in-progress"},
    "status:in-progress": {"status:pending-test", "status:approved"},
    "status:pending-test": {"status:in-progress", "status:pending-ship"},
    "status:pending-ship": {"status:shipped"},
    "status:shipped": set(),  # terminal
}


def _run_list(cmd_list, check=True):
    """Run a command from repo root using list form (safe for variable args)."""
    return subprocess.run(
        cmd_list, capture_output=True, text=True,
        check=check, cwd=str(REPO_ROOT),
    )


def _resolve_status(name):
    """Resolve a status name to its full label."""
    if name.startswith("status:"):
        return name
    if name in STATUS_LABELS:
        return STATUS_LABELS[name]
    print(f"ERROR: Unknown status '{name}'. Valid: {list(STATUS_LABELS.keys())}", file=sys.stderr)
    sys.exit(1)


def check_gh():
    """Verify gh CLI access."""
    result = _run_list(["gh", "issue", "list", "--limit", "1"], check=False)
    if result.returncode != 0:
        print("ERROR: GitHub Issues permission check failed.", file=sys.stderr)
        print("Run 'gh auth refresh' with 'repo' scope.", file=sys.stderr)
        return False
    print("OK")
    return True


def list_issues(role, issue_type="bug", status=None):
    """List issues by role and optional type/status filter."""
    type_label = TYPE_LABELS.get(issue_type, f"type:{issue_type}")
    role_label = f"role:{role}"
    labels = f"{type_label},{role_label}"
    if status:
        status_label = _resolve_status(status)
        labels += f",{status_label}"
    result = _run_list(
        ["gh", "issue", "list", "--label", labels, "--state", "open",
         "--json", "number,title,labels", "--limit", "50"],
        check=False,
    )
    if result.returncode != 0:
        print(f"ERROR: gh failed: {result.stderr}", file=sys.stderr)
        return []
    issues = json.loads(result.stdout) if result.stdout.strip() else []
    print(json.dumps(issues, indent=2))
    return issues


def list_by_labels(labels_str):
    """List issues by arbitrary label string (for cross-role queries)."""
    result = _run_list(
        ["gh", "issue", "list", "--label", labels_str, "--state", "open",
         "--json", "number,title,labels", "--limit", "50"],
        check=False,
    )
    if result.returncode != 0:
        print(f"ERROR: gh failed: {result.stderr}", file=sys.stderr)
        return []
    issues = json.loads(result.stdout) if result.stdout.strip() else []
    print(json.dumps(issues, indent=2))
    return issues


def list_all_open():
    """List all open issues (for ingestion/triage of external issues)."""
    result = _run_list(
        ["gh", "issue", "list", "--state", "open",
         "--json", "number,title,labels,body", "--limit", "50"],
        check=False,
    )
    if result.returncode != 0:
        print(f"ERROR: gh failed: {result.stderr}", file=sys.stderr)
        return []
    issues = json.loads(result.stdout) if result.stdout.strip() else []
    print(json.dumps(issues, indent=2))
    return issues


def add_labels(number, labels_str):
    """Add labels to an issue (for metadata labels like design:, squidsquad)."""
    _run_list(["gh", "issue", "edit", str(number), "--add-label", labels_str])
    print(f"#{number}: added labels {labels_str}")


def create_bug(title, body, role, severity, reporter=None):
    """Create a bug issue with correct label format."""
    sev_label = SEVERITY_LABELS.get(severity, f"severity:{severity}")
    role_label = f"role:{role}"
    labels = f"type:bug,{sev_label},{role_label},squidsquad,status:pending"

    full_body = body
    if reporter:
        full_body = f"**Reported By**: {reporter}\n**Severity**: {severity.title()}\n\n{body}"

    result = _run_list([
        "gh", "issue", "create",
        "--title", f"BUG: {title}",
        "--body", full_body,
        "--label", labels,
    ])
    url = result.stdout.strip()
    number = int(url.rstrip("/").split("/")[-1])
    print(json.dumps({"number": number, "url": url}))
    return number


def create_feature(title, body, role, priority, reporter=None):
    """Create a feature issue with correct label format."""
    pri_label = PRIORITY_LABELS.get(priority, f"priority:{priority}")
    role_label = f"role:{role}"
    labels = f"type:feature,{pri_label},{role_label},squidsquad,status:pending"

    result = _run_list([
        "gh", "issue", "create",
        "--title", f"FEAT: {title}",
        "--body", body,
        "--label", labels,
    ])
    url = result.stdout.strip()
    number = int(url.rstrip("/").split("/")[-1])
    print(json.dumps({"number": number, "url": url}))
    return number


def transition(number, from_status, to_status):
    """Transition an issue status with enforcement."""
    from_label = _resolve_status(from_status)
    to_label = _resolve_status(to_status)

    # Enforce legal transitions
    legal = LEGAL_TRANSITIONS.get(from_label, set())
    if to_label not in legal:
        print(
            f"ERROR: Illegal transition {from_label} -> {to_label}. "
            f"Legal from {from_label}: {sorted(legal)}",
            file=sys.stderr,
        )
        sys.exit(1)

    _run_list(["gh", "issue", "edit", str(number), "--remove-label", from_label, "--add-label", to_label])

    # Auto-close on shipped
    if to_label == "status:shipped":
        _run_list(["gh", "issue", "close", str(number)])

    print(f"#{number}: {from_label} -> {to_label}")
    return True


def comment(number, role, message):
    """Add a discussion comment to an issue."""
    # No manual timestamps — GitHub provides them
    body = f"**{role}**: {message}"
    _run_list(["gh", "issue", "comment", str(number), "--body", body])
    print(f"Commented on #{number}")


def get_labels(number):
    """Get label names for an issue."""
    result = _run_list(["gh", "issue", "view", str(number), "--json", "labels"])
    data = json.loads(result.stdout)
    labels = [l["name"] for l in data.get("labels", [])]
    print(json.dumps(labels))
    return labels


def get_state(number):
    """Get issue state (OPEN/CLOSED)."""
    result = _run_list(["gh", "issue", "view", str(number), "--json", "state"])
    data = json.loads(result.stdout)
    state = data["state"]
    print(state)
    return state


def close_issue(number):
    """Close an issue."""
    _run_list(["gh", "issue", "close", str(number)])
    print(f"Closed #{number}")


def _parse_args():
    """Simple arg parser."""
    args = sys.argv[1:]
    if not args or args[0] == "--help":
        print(__doc__)
        sys.exit(0)

    cmd = args[0]
    opts = {}
    i = 1
    positional = []
    while i < len(args):
        if args[i].startswith("--"):
            key = args[i][2:]
            if i + 1 < len(args) and not args[i + 1].startswith("--"):
                opts[key] = args[i + 1]
                i += 2
            else:
                opts[key] = True
                i += 1
        else:
            positional.append(args[i])
            i += 1
    return cmd, positional, opts


def main():
    cmd, pos, opts = _parse_args()

    if cmd == "check-gh":
        sys.exit(0 if check_gh() else 1)

    elif cmd == "list-bugs":
        if not pos:
            print("Usage: tracker.py list-bugs <role>", file=sys.stderr)
            sys.exit(1)
        list_issues(pos[0], "bug")

    elif cmd == "list-features":
        if not pos:
            print("Usage: tracker.py list-features <role> [--status <s>]", file=sys.stderr)
            sys.exit(1)
        list_issues(pos[0], "feature", opts.get("status"))

    elif cmd == "create-bug":
        for req in ("title", "body", "role", "severity"):
            if req not in opts:
                print(f"Missing --{req}", file=sys.stderr)
                sys.exit(1)
        create_bug(opts["title"], opts["body"], opts["role"],
                    opts["severity"], opts.get("reporter"))

    elif cmd == "create-feature":
        for req in ("title", "body", "role", "priority"):
            if req not in opts:
                print(f"Missing --{req}", file=sys.stderr)
                sys.exit(1)
        create_feature(opts["title"], opts["body"], opts["role"],
                       opts["priority"], opts.get("reporter"))

    elif cmd == "transition":
        if len(pos) < 3:
            print("Usage: tracker.py transition <number> <from> <to>", file=sys.stderr)
            sys.exit(1)
        transition(int(pos[0]), pos[1], pos[2])

    elif cmd == "comment":
        if not pos or "role" not in opts or "message" not in opts:
            print("Usage: tracker.py comment <number> --role <r> --message <m>", file=sys.stderr)
            sys.exit(1)
        comment(int(pos[0]), opts["role"], opts["message"])

    elif cmd == "get-labels":
        if not pos:
            print("Usage: tracker.py get-labels <number>", file=sys.stderr)
            sys.exit(1)
        get_labels(int(pos[0]))

    elif cmd == "get-state":
        if not pos:
            print("Usage: tracker.py get-state <number>", file=sys.stderr)
            sys.exit(1)
        get_state(int(pos[0]))

    elif cmd == "close":
        if not pos:
            print("Usage: tracker.py close <number>", file=sys.stderr)
            sys.exit(1)
        close_issue(int(pos[0]))

    elif cmd == "list-by-labels":
        if not pos:
            print("Usage: tracker.py list-by-labels <labels>", file=sys.stderr)
            sys.exit(1)
        list_by_labels(pos[0])

    elif cmd == "list-all-open":
        list_all_open()

    elif cmd == "add-labels":
        if len(pos) < 2:
            print("Usage: tracker.py add-labels <number> <labels>", file=sys.stderr)
            sys.exit(1)
        add_labels(int(pos[0]), pos[1])

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
