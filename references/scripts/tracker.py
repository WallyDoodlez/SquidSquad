#!/usr/bin/env python3
"""SquidSquad tracker operations — single source of truth for labels and status flows.

Encodes the complete label taxonomy and legal status transitions.
Agents call this instead of constructing gh commands from prose.

Usage:
    python scripts/tracker.py list-bugs <role>
    python scripts/tracker.py list-features <role> [--status approved|in-progress|pending-test]
    python scripts/tracker.py create-bug --title <t> --body <b> --role <r> --severity <s> [--reporter <name>]
    python scripts/tracker.py create-feature --title <t> --body <b> --role <r> --priority <p> [--reporter <name>]
    python scripts/tracker.py transition <number> <from-status> <to-status> --role <r> [--force]
    python scripts/tracker.py comment <number> --role <r> --message <m>
    python scripts/tracker.py get-labels <number>
    python scripts/tracker.py get-state <number>
    python scripts/tracker.py close <number>
    python scripts/tracker.py check-gh                   # Verify gh access
    python scripts/tracker.py --help

Role authority (who may call `transition`):
  - PM  (--role pm  or pm-lead)    : pending -> planning/approved, planning -> planned,
                                     planned -> approved; AND pending-test -> in-progress,
                                     pending-test -> pending-ship (PM/QA combined identity)
  - QA  (--role qa  or qa-lead)    : pending-test -> in-progress, pending-test -> pending-ship
                                     (when deployed as a separate agent alongside PM)
  - Assigned dev role (--role <r>) : open -> in-progress, approved -> in-progress,
                                     in-progress <-> pending-test, open -> pending-test,
                                     in-progress -> approved (must match issue's `role:*` label)
  - DM  (--role dm  or dm-lead)    : pending-ship -> shipped
  - Human override                 : --force bypasses authority + unread-feedback guards
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
    # --- #328 Phase E: new pending-human-* taxonomy (Q-new4) ---
    # These are ADDITIVE in this phase. The existing `pending` label stays
    # legal until Phase I performs the `pending` -> `pending-human-approval`
    # migration on GitHub. Until then, both taxonomies coexist so agents
    # written against either can operate.
    "pending-human-approval": "status:pending-human-approval",
    "pending-human-review": "status:pending-human-review",
    "pending-human-setup": "status:pending-human-setup",
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
    "status:in-progress": {
        "status:pending-test",
        "status:approved",
        # #328 Phase E: worker self-pause edges (Q7 HITL + Q-new11 tool setup).
        # The assigned worker moves its own in-progress issue into a
        # human-waiting state when it needs human input or environment work.
        "status:pending-human-review",
        "status:pending-human-setup",
    },
    "status:pending-test": {"status:in-progress", "status:pending-ship"},
    "status:pending-ship": {"status:shipped"},
    "status:shipped": set(),  # terminal

    # --- #328 Phase E: new pending-human-* transitions (Q-new4, Q7, Q-new11) ---
    # `pending-human-approval` is the future replacement for `pending`. It is
    # added alongside `pending` during Phase E and will supersede it in the
    # Phase I migration. Its legal targets mirror `pending`'s — PM either
    # schedules planning or fast-tracks to approved.
    "status:pending-human-approval": {"status:planning", "status:approved"},
    # HITL review (designer loop): human redirects (back to in-progress) or
    # approves (straight to pending-ship, skipping pending-test because the
    # human already validated the work).
    "status:pending-human-review": {
        "status:in-progress",
        "status:pending-ship",
    },
    # Worker-pause-for-environment-setup: PM completes the tool/config setup
    # and hands the issue back to the worker to resume.
    "status:pending-human-setup": {"status:in-progress"},
}

# === ROLE AUTHORITY (who may perform each legal transition) ===
#
# Keys are (from_label, to_label). Values are sets of canonical role prefixes
# (e.g. "pm" matches both "pm" and "pm-lead"). The special marker "_assignee"
# means "must match one of the issue's role:* labels" — used for work handled
# by the role the issue is assigned to (any dev role, or DM/QA bug fixes).
#
# Every legal transition MUST appear here. A legal transition missing from
# this table will be rejected with "no authority mapping" unless --force is
# passed. This fails closed by design.
#
# Bypass: --force overrides authority (and the unread-feedback guard) but
# NOT legality. Humans use --force when intervening manually.

ROLE_AUTHORITY = {
    # PM owns the intake lifecycle
    ("status:pending", "status:planning"): {"pm"},
    ("status:pending", "status:approved"): {"pm"},
    ("status:planning", "status:planned"): {"pm"},
    ("status:planned", "status:approved"): {"pm"},

    # Assigned role owns implementation work on their own issues
    ("status:open", "status:in-progress"): {"_assignee"},
    ("status:open", "status:pending-test"): {"_assignee"},
    ("status:approved", "status:in-progress"): {"_assignee"},
    ("status:in-progress", "status:pending-test"): {"_assignee"},
    ("status:in-progress", "status:approved"): {"_assignee"},

    # QA/PM owns verification. PM is always authorized because the PM agent
    # holds the combined PM/QA identity in deployments without a dedicated QA
    # agent (see pm/CLAUDE.md "SquidSquad — PM/QA"). QA is also authorized
    # when installed. Dev and DM roles remain locked out.
    ("status:pending-test", "status:in-progress"): {"qa", "pm"},
    ("status:pending-test", "status:pending-ship"): {"qa", "pm"},

    # DM owns delivery / shipping
    ("status:pending-ship", "status:shipped"): {"dm"},

    # --- #328 Phase E: authority for new pending-human-* transitions ---

    # PM owns the new pending-human-approval intake edges (mirrors the
    # existing `pending` entries above).
    ("status:pending-human-approval", "status:planning"): {"pm"},
    ("status:pending-human-approval", "status:approved"): {"pm"},

    # The worker self-pauses into human-review (HITL designer loop) and
    # resumes (redirect or approve) itself — assignee-bound on both sides.
    ("status:in-progress", "status:pending-human-review"): {"_assignee"},
    ("status:pending-human-review", "status:in-progress"): {"_assignee"},
    ("status:pending-human-review", "status:pending-ship"): {"_assignee"},

    # Worker self-pauses for environment/tool setup; PM completes the setup
    # and hands the issue back to the worker.
    ("status:in-progress", "status:pending-human-setup"): {"_assignee"},
    ("status:pending-human-setup", "status:in-progress"): {"pm"},
}


def _canonicalize_role(role):
    """Normalize a role string for authority comparison.

    Strips optional trailing '-lead' suffix and any parenthetical alias:
        "skill-lead"         -> "skill"
        "pm (pm)"            -> "pm"
        "qa-lead (tester)"   -> "qa"
        "dm"                 -> "dm"

    Returns None if role is None.
    """
    if role is None:
        return None
    paren = role.find(" (")
    if paren >= 0:
        role = role[:paren]
    role = role.strip()
    if role.endswith("-lead"):
        role = role[: -len("-lead")]
    return role


def _get_issue_role_labels(number):
    """Return the set of role prefixes from an issue's `role:*` labels.

    e.g. labels `role:skill`, `role:dm` -> {"skill", "dm"}. Returns an empty
    set on API failure (caller decides how to treat missing data).
    """
    result = _run_list(
        ["gh", "issue", "view", str(number), "--json", "labels"],
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return set()
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return set()
    roles = set()
    for lbl in data.get("labels", []):
        name = lbl.get("name", "")
        if name.startswith("role:"):
            roles.add(name[len("role:"):])
    return roles


def _check_authority(number, from_label, to_label, caller_role):
    """Decide whether `caller_role` may perform (from_label -> to_label) on #number.

    Returns (authorized: bool, reason: str | None). `reason` is None on success,
    a human-readable explanation on failure.
    """
    auth = ROLE_AUTHORITY.get((from_label, to_label))
    if auth is None:
        # Legal transition with no authority entry -- fail closed.
        return False, (
            f"transition {from_label} -> {to_label} has no authority mapping "
            f"(legal but unassigned)"
        )

    canon = _canonicalize_role(caller_role)
    if not canon:
        return False, f"--role is required for transition {from_label} -> {to_label}"

    if "_assignee" in auth:
        issue_roles = _get_issue_role_labels(number)
        if not issue_roles:
            return False, (
                f"#{number} has no role:* label — cannot verify assignee authority"
            )
        if canon not in issue_roles:
            return False, (
                f"role '{canon}' is not assigned to #{number} "
                f"(issue role labels: {sorted(issue_roles)}); only the assigned "
                f"role may perform {from_label} -> {to_label}"
            )
        return True, None

    if canon in auth:
        return True, None
    return False, (
        f"role '{canon}' is not authorized for {from_label} -> {to_label} "
        f"(allowed: {sorted(auth)})"
    )


def _log_diagnostic(severity, message, context=None):
    """Log a diagnostic entry (silently fails if diagnostics.py unavailable)."""
    try:
        cmd = [sys.executable, str(SCRIPT_DIR / "diagnostics.py"), "log", severity, "tracker", message]
        if context:
            cmd.extend(["--context", json.dumps(context) if not isinstance(context, str) else context])
        subprocess.run(cmd, capture_output=True, check=False, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT))
    except Exception:
        pass


def _run_list(cmd_list, check=True):
    """Run a command from repo root using list form (safe for variable args)."""
    return subprocess.run(
        cmd_list, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
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
    # Bugs start at `open` (immediately actionable by the assigned dev agent).
    # Features start at `pending` (awaiting human approval via PM intake).
    # This distinction matters: dev-agent Step 2 picks up all non-shipped
    # bugs — if bugs started at `pending`, they'd sit in limbo because
    # agents interpret `pending` as "awaiting human approval".
    labels = f"type:bug,{sev_label},{role_label},squidsquad,status:open"

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


# Roles whose comments trigger the unread feedback guard.
# Dev agents and designer comments do NOT trigger — only oversight roles and humans.
FEEDBACK_ROLES = {"pm", "qa", "human"}


def _is_feedback_comment(body, caller_role):
    """Check if a comment is feedback from an oversight role or a human.

    Returns (is_feedback, role_name) or (False, None).
    Handles: **pm**: ..., **pm (alias)**: ..., **qa**: ..., and human comments
    (no **role**: prefix — plain text from GitHub UI).
    """
    if not body.startswith("**"):
        # No role prefix — likely a human comment from GitHub UI
        return True, "human"

    # Extract role from **role**: or **role (alias)**:
    role_end = body.find("**", 2)
    if role_end <= 2:
        return False, None
    raw_role = body[2:role_end]
    # Strip alias: "pm (pm)" → "pm", "qa (tester)" → "qa"
    base_role = raw_role.split("(")[0].strip().split("-")[0].strip()

    # Skip caller's own comments
    caller_base = caller_role.split("-")[0].strip()
    if base_role == caller_base:
        return False, None

    # Only trigger on oversight roles
    if base_role in FEEDBACK_ROLES:
        return True, raw_role

    return False, None


def _check_unread_feedback(number, caller_role):
    """Check for unread oversight/human comments after the caller's last comment.

    Returns a list of (role, timestamp) tuples. Empty list means no unread feedback.
    API failures return a sentinel that causes the guard to block (fail closed).
    """
    result = _run_list(
        ["gh", "issue", "view", str(number), "--json", "comments"],
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        # Fail closed — if we can't read comments, block the transition
        return [("unknown (API error)", "unknown")]

    data = json.loads(result.stdout)
    comments = data.get("comments", [])
    if not comments:
        return []

    # Find the last comment by the caller role
    caller_last_idx = -1
    for i, c in enumerate(comments):
        body = c.get("body", "")
        if body.startswith(f"**{caller_role}**:") or body.startswith(f"**{caller_role} "):
            caller_last_idx = i

    # Collect all unread feedback after caller's last comment
    unread = []
    for c in comments[caller_last_idx + 1:]:
        body = c.get("body", "")
        is_feedback, role_name = _is_feedback_comment(body, caller_role)
        if is_feedback:
            timestamp = c.get("createdAt", "unknown")
            unread.append((role_name, timestamp))

    return unread


# Guarded transitions: these transitions check for unread feedback before proceeding
_GUARDED_TRANSITIONS = {
    ("status:in-progress", "status:pending-test"),
    ("status:pending-test", "status:pending-ship"),
}


def transition(number, from_status, to_status, role=None, force=False):
    """Transition an issue status with legality + role authority enforcement.

    Args:
        number: issue number
        from_status: current status (short or full label)
        to_status: target status (short or full label)
        role: caller's role (e.g. "skill-lead", "pm", "qa-lead"). Required
              unless `force` is set. Checked against ROLE_AUTHORITY.
        force: human override — bypasses role authority AND the unread-feedback
              guard. Does NOT bypass legality.
    """
    from_label = _resolve_status(from_status)
    to_label = _resolve_status(to_status)

    # 1. Enforce legal transitions (never bypassed)
    legal = LEGAL_TRANSITIONS.get(from_label, set())
    if to_label not in legal:
        _log_diagnostic("error", f"Illegal transition {from_label} -> {to_label} on #{number}")
        print(
            f"ERROR: Illegal transition {from_label} -> {to_label}. "
            f"Legal from {from_label}: {sorted(legal)}",
            file=sys.stderr,
        )
        sys.exit(1)

    # 2. Enforce role authority (bypassable with --force)
    if not force:
        authorized, reason = _check_authority(number, from_label, to_label, role)
        if not authorized:
            _log_diagnostic(
                "error",
                f"Unauthorized transition on #{number}: {reason}",
                {"from": from_label, "to": to_label, "role": role},
            )
            print(
                f"ERROR: Unauthorized transition on #{number}: {reason}. "
                f"Use --force to override (humans only).",
                file=sys.stderr,
            )
            sys.exit(1)

    # 3. Guard: block guarded transitions if unread feedback exists
    if (from_label, to_label) in _GUARDED_TRANSITIONS and not force:
        # Match the caller's actual comment format (role is non-None here
        # because authority check required it; fall back to skill-lead
        # for back-compat if somehow unset).
        unread = _check_unread_feedback(number, role or "skill-lead")
        if unread:
            roles_summary = ", ".join(f"{role} ({ts})" for role, ts in unread)
            _log_diagnostic("warning", f"Blocked transition #{number} {from_label} -> {to_label}: unread feedback from {roles_summary}")
            print(
                f"BLOCKED: #{number} has unread feedback from: {roles_summary}. "
                f"Read and address before transitioning. "
                f"Use --force to override.",
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
            print(
                "Usage: tracker.py transition <number> <from> <to> --role <r> [--force]",
                file=sys.stderr,
            )
            sys.exit(1)
        transition(
            int(pos[0]), pos[1], pos[2],
            role=opts.get("role"),
            force=opts.get("force", False),
        )

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
