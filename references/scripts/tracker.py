#!/usr/bin/env python3
"""SquidSquad tracker operations — single source of truth for labels and status flows.

Encodes the complete label taxonomy and legal status transitions.
Agents call this instead of constructing gh commands from prose.

Usage:
    python scripts/tracker.py list-issues <role>           (alias: list-bugs)
    python scripts/tracker.py list-tasks <role> [--status] (alias: list-features)
    python scripts/tracker.py create-issue --title <t> --body <b> --role <r> --severity <s> [--reporter <name>]  (alias: create-bug)
    python scripts/tracker.py create-task --title <t> --body <b> --role <r> --priority <p> [--reporter <name>]   (alias: create-feature)
    python scripts/tracker.py transition <number> <from-status> <to-status> --role <r> [--force]
    python scripts/tracker.py comment <number> --role <r> --message <m>
    python scripts/tracker.py get-labels <number>
    python scripts/tracker.py get-state <number>
    python scripts/tracker.py close <number>
    python scripts/tracker.py check-gh                   # Verify gh access
    python scripts/tracker.py --help

Role authority (who may call `transition`):
  - PM  (--role pm  or pm-lead)    : pending -> planning/approved, planning -> planned,
                                     planned -> approved; pending-test -> in-progress/pending-ship
  - QA  (--role qa  or qa-lead)    : pending-test -> in-progress, pending-test -> pending-ship
  - Assigned dev role (--role <r>) : open -> in-progress, approved -> in-progress,
                                     in-progress <-> pending-test, open -> pending-test,
                                     in-progress -> approved (must match issue's `role:*` label)
  - DM  (--role dm  or dm-lead)    : in-progress -> pending-ship, pending-ship -> shipped,
                                     pending-ship -> in-progress (merge conflict rollback)
  - Human override                 : --force bypasses authority + unread-feedback guards
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent

# === FORGE ADAPTER (optional — falls back to direct gh calls if unavailable) ===

_forge_adapter = None
_forge_checked = False


def _get_forge_adapter():
    """Get the forge adapter if configured for a non-GitHub backend.

    Returns the adapter instance, or None (use direct gh calls).
    For GitHub provider, returns None — gh CLI is used directly for full compat.
    Only returns an adapter for Forgejo or other non-GitHub backends.
    """
    global _forge_adapter, _forge_checked
    if _forge_checked:
        return _forge_adapter
    _forge_checked = True
    try:
        from forge_adapter import get_adapter, _read_forge_config
        config = _read_forge_config()
        if config["provider"] not in ("github", ""):
            _forge_adapter = get_adapter(config)
    except ImportError:
        pass
    return _forge_adapter


# === LABEL TAXONOMY (single source of truth) ===

TYPE_LABELS = {"issue": "type:issue", "task": "type:task",
               # Backward-compat aliases
               "bug": "type:issue", "feature": "type:task"}

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

SPECIAL_LABELS = {"squidsquad", "improvement-scan", "squidsquad-test", "review:human-required"}

# === LEGAL STATUS TRANSITIONS (pessimistic enforcement) ===

LEGAL_TRANSITIONS = {
    "status:open": {"status:pending-test", "status:in-progress"},
    "status:pending": {"status:planning", "status:approved"},
    "status:planning": {"status:planned"},
    "status:planned": {"status:approved"},
    "status:approved": {"status:in-progress"},
    "status:in-progress": {
        "status:pending-test",
        "status:pending-ship",  # #6261: DM skips QA — goes directly to pending-ship
        "status:approved",
        # #6057: code review rejection path — dev sends task back to PM for re-planning
        "status:planning",
        # #328 Phase E: worker self-pause edges (Q7 HITL + Q-new11 tool setup).
        # The assigned worker moves its own in-progress issue into a
        # human-waiting state when it needs human input or environment work.
        "status:pending-human-review",
        "status:pending-human-setup",
    },
    "status:pending-test": {"status:in-progress", "status:pending-ship", "status:pending-human-review"},
    "status:pending-human-review": {"status:in-progress", "status:pending-ship"},
    "status:pending-ship": {"status:shipped", "status:in-progress"},
    "status:shipped": set(),  # terminal

    # --- #328 Phase E: new pending-human-* transitions (Q-new4, Q7, Q-new11) ---
    # `pending-human-approval` is the future replacement for `pending`. It is
    # added alongside `pending` during Phase E and will supersede it in the
    # Phase I migration. Its legal targets mirror `pending`'s — PM either
    # schedules planning or fast-tracks to approved.
    "status:pending-human-approval": {"status:planning", "status:approved"},
    # NOTE: pending-human-review targets are defined above (line 132) — not
    # duplicated here. Both PR Flow and HITL designer loop share the same
    # legal targets: {in-progress, pending-ship}.
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
    ("status:in-progress", "status:planning"): {"_assignee"},  # #6057 code review rejection
    ("status:in-progress", "status:pending-ship"): {"dm"},  # #6261: DM skips QA

    # QA/PM owns verification. PM and QA are both authorized.
    ("status:pending-test", "status:in-progress"): {"qa", "pm"},
    ("status:pending-test", "status:pending-ship"): {"qa", "pm"},
    # PR Flow: QA transitions to pending-human-review (not pending-ship) when PR Flow enabled
    ("status:pending-test", "status:pending-human-review"): {"qa", "pm"},
    # pending-human-review transitions: PM (PR Flow merge/feedback) + _assignee
    # (HITL designer self-pause loop). Both paths share the same targets.
    ("status:pending-human-review", "status:in-progress"): {"pm", "_assignee"},
    ("status:pending-human-review", "status:pending-ship"): {"pm", "_assignee"},

    # DM owns delivery / shipping
    ("status:pending-ship", "status:shipped"): {"dm"},

    # Backward: pending-ship→in-progress for merge conflicts (#1727, #6261)
    ("status:pending-ship", "status:in-progress"): {"pm", "qa", "dm"},

    # --- #328 Phase E: authority for new pending-human-* transitions ---

    # PM owns the new pending-human-approval intake edges (mirrors the
    # existing `pending` entries above).
    ("status:pending-human-approval", "status:planning"): {"pm"},
    ("status:pending-human-approval", "status:approved"): {"pm"},

    # The worker self-pauses into human-review (HITL designer loop).
    # The resume/approve transitions are merged above with PR Flow entries.
    ("status:in-progress", "status:pending-human-review"): {"_assignee"},

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

    # Check named roles first (e.g. "pm", "qa", "dm")
    named_roles = auth - {"_assignee"}
    if canon in named_roles:
        return True, None

    # Check assignee-based authority
    if "_assignee" in auth:
        issue_roles = _get_issue_role_labels(number)
        if not issue_roles:
            return False, (
                f"#{number} has no role:* label — cannot verify assignee authority"
            )
        if canon in issue_roles:
            return True, None
        return False, (
            f"role '{canon}' is not assigned to #{number} "
            f"(issue role labels: {sorted(issue_roles)}); only the assigned "
            f"role may perform {from_label} -> {to_label}"
        )

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


_RESOLVED_GH_BIN: str | None = None


def _resolve_gh_bin() -> str:
    """Locate the ``gh`` CLI binary via ``shutil.which`` (PATHEXT-aware).

    Cached after the first call. Falls back to the literal string
    ``"gh"`` if resolution fails — that path goes through subprocess's
    own lookup, which on POSIX honors the executable bit and on
    Windows finds ``gh.exe`` via PATH (no functional change vs. the
    pre-#9398 behavior).

    Why: on Windows, ``subprocess.run([\"gh\", ...])`` uses
    ``CreateProcessW`` for executable lookup, which only honors
    ``.exe``/``.com`` extensions — ``.cmd`` files in PATH get
    skipped. The #9398 Phase A PATH-shim ships ``gh.cmd``, which
    ``shutil.which`` finds (it's PATHEXT-aware) but
    ``subprocess.run([\"gh\", ...])`` does not. Routing through the
    resolved path closes the gap so tests can shim ``gh`` for the
    real-agent-subprocess fixture work. Same shape as
    ``run_comprehension_test._find_claude`` (#9574 fix for the same
    root cause on the ``claude`` CLI).
    """
    global _RESOLVED_GH_BIN
    if _RESOLVED_GH_BIN is None:
        _RESOLVED_GH_BIN = shutil.which("gh") or "gh"
    return _RESOLVED_GH_BIN


def _run_list(cmd_list, check=True):
    """Run a command from repo root using list form (safe for variable args).

    #9398: if the first element is the literal string ``"gh"``,
    substitute with the resolved gh binary path so PATH shims with
    ``.cmd`` extensions are found on Windows (see ``_resolve_gh_bin``).
    Other commands are passed through unchanged. Subprocess invocations
    that pass a full path (already-resolved) are also unchanged.
    """
    if cmd_list and cmd_list[0] == "gh":
        cmd_list = [_resolve_gh_bin()] + list(cmd_list[1:])
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
    """Verify forge backend connectivity (gh CLI or Forgejo API)."""
    adapter = _get_forge_adapter()
    if adapter:
        ok, msg = adapter.check_connection()
        if not ok:
            print(f"ERROR: Forge connection check failed: {msg}", file=sys.stderr)
            return False
        print("OK")
        return True
    # Default: gh CLI check
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
    label_list = [type_label, role_label]
    if status:
        label_list.append(_resolve_status(status))

    adapter = _get_forge_adapter()
    if adapter:
        issues = adapter.list_issues(labels=label_list, state="open", limit=50)
        print(json.dumps(issues, indent=2))
        return issues

    # Default: gh CLI
    labels = ",".join(label_list)
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


def list_by_labels(labels_str, state="open"):
    """List issues by arbitrary label string (for cross-role queries).

    Args:
        labels_str: comma-separated label names
        state: "open", "closed", or "all" (default: "open")
    """
    label_list = [l.strip() for l in labels_str.split(",") if l.strip()]

    adapter = _get_forge_adapter()
    if adapter:
        issues = adapter.list_issues(labels=label_list, state=state, limit=50)
        print(json.dumps(issues, indent=2))
        return issues

    # Default: gh CLI
    result = _run_list(
        ["gh", "issue", "list", "--label", labels_str, "--state", state,
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
    adapter = _get_forge_adapter()
    if adapter:
        issues = adapter.list_issues(labels=None, state="open", limit=50)
        print(json.dumps(issues, indent=2))
        return issues

    # Default: gh CLI
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


def work_queue(role):
    """Return a single prioritized work list for an agent role.

    Priority order (strict):
    1. In-progress items (resume first)
    2. Approved issues — severity:high → medium → low
    3. Approved tasks — priority:high → medium → low
    4. Open issues — severity:high → medium → low

    Returns a JSON array of {number, title, type, priority, status}.
    """
    role_label = f"role:{role}"

    # Single query: all open items for this role
    result = _run_list(
        ["gh", "issue", "list", "--label", role_label, "--state", "open",
         "--json", "number,title,labels", "--limit", "100"],
        check=False,
    )
    if result.returncode != 0:
        print(f"ERROR: gh failed: {result.stderr}", file=sys.stderr)
        return []
    items = json.loads(result.stdout) if result.stdout.strip() else []

    def _get_label(item, prefix):
        for lbl in item.get("labels", []):
            if lbl["name"].startswith(prefix):
                return lbl["name"][len(prefix):]
        return None

    PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

    queue = []
    for item in items:
        status = _get_label(item, "status:")
        item_type = _get_label(item, "type:")
        priority = _get_label(item, "priority:")
        severity = _get_label(item, "severity:")

        if not status or not item_type:
            continue

        # Skip items not actionable by dev agents
        if status not in ("in-progress", "approved", "open"):
            continue

        # Determine sort key: (status_rank, type_rank, priority_rank)
        if status == "in-progress":
            status_rank = 0
        elif status == "approved":
            status_rank = 1
        else:  # open
            status_rank = 2

        type_rank = 0 if item_type == "issue" else 1
        prio = severity if item_type == "issue" else priority
        prio_rank = PRIORITY_ORDER.get(prio, 1)  # default medium

        queue.append({
            "number": item["number"],
            "title": item["title"],
            "type": item_type,
            "priority": prio or "medium",
            "status": status,
            "_sort": (status_rank, type_rank, prio_rank),
        })

    queue.sort(key=lambda x: x["_sort"])
    # Remove sort key from output
    for item in queue:
        del item["_sort"]

    print(json.dumps(queue, indent=2))
    return queue


def add_labels(number, labels_str):
    """Add labels to an issue (for metadata labels like design:, squidsquad)."""
    adapter = _get_forge_adapter()
    if adapter:
        adapter.add_labels(number, labels_str.split(","))
    else:
        _run_list(["gh", "issue", "edit", str(number), "--add-label", labels_str])
    print(f"#{number}: added labels {labels_str}")


def create_issue(title, body, role, severity, reporter=None):
    """Create an issue with correct label format."""
    sev_label = SEVERITY_LABELS.get(severity, f"severity:{severity}")
    role_label = f"role:{role}"
    # Issues start at `open` (immediately actionable by the assigned dev agent).
    # Tasks start at `pending` (awaiting human approval via PM intake).
    # This distinction matters: dev-agent Step 2 picks up all non-shipped
    # issues — if issues started at `pending`, they'd sit in limbo because
    # agents interpret `pending` as "awaiting human approval".
    labels = f"type:issue,{sev_label},{role_label},squidsquad,status:open"

    full_body = body
    if reporter:
        full_body = f"**Reported By**: {reporter}\n**Severity**: {severity.title()}\n\n{body}"

    # Strip existing prefix to avoid double ISSUE: ISSUE: or legacy BUG: BUG:
    clean_title = title.removeprefix("ISSUE:").removeprefix("ISSUE :").removeprefix("BUG:").removeprefix("BUG :").strip()
    full_title = f"ISSUE: {clean_title}"
    label_list = labels.split(",")

    adapter = _get_forge_adapter()
    if adapter:
        result = adapter.create_issue(full_title, full_body, labels=label_list)
        if not result:
            print("ERROR: Failed to create issue via forge adapter", file=sys.stderr)
            return -1
        print(json.dumps(result))
        return result.get("number", -1)

    result = _run_list([
        "gh", "issue", "create",
        "--title", full_title,
        "--body", full_body,
        "--label", labels,
    ])
    url = result.stdout.strip()
    try:
        number = int(url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        print(f"ERROR: could not parse issue number from gh output: {url}", file=sys.stderr)
        return -1
    print(json.dumps({"number": number, "url": url}))
    return number


# Backward-compat alias
create_bug = create_issue


def create_task(title, body, role, priority, reporter=None):
    """Create a task with correct label format."""
    pri_label = PRIORITY_LABELS.get(priority, f"priority:{priority}")
    role_label = f"role:{role}"
    labels = f"type:task,{pri_label},{role_label},squidsquad,status:pending"

    full_body = body
    if reporter:
        full_body = f"**Reported By**: {reporter}\n**Priority**: {priority.title()}\n\n{body}"

    # Strip existing prefix to avoid double TASK: TASK: or legacy FEAT: FEAT:
    clean_title = title.removeprefix("TASK:").removeprefix("TASK :").removeprefix("FEAT:").removeprefix("FEAT :").strip()
    full_title = f"TASK: {clean_title}"
    label_list = labels.split(",")

    adapter = _get_forge_adapter()
    if adapter:
        result = adapter.create_issue(full_title, full_body, labels=label_list)
        if not result:
            print("ERROR: Failed to create task via forge adapter", file=sys.stderr)
            return -1
        print(json.dumps(result))
        return result.get("number", -1)

    result = _run_list([
        "gh", "issue", "create",
        "--title", full_title,
        "--body", full_body,
        "--label", labels,
    ])
    url = result.stdout.strip()
    try:
        number = int(url.rstrip("/").split("/")[-1])
    except (ValueError, IndexError):
        print(f"ERROR: could not parse issue number from gh output: {url}", file=sys.stderr)
        return -1
    print(json.dumps({"number": number, "url": url}))
    return number


# Backward-compat alias
create_feature = create_task


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


def _get_working_branch():
    """Get the configured working branch. Falls back to 'main'."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        branch = get_field("working-branch")
        return branch.strip() if branch else "main"
    except Exception:
        return "main"


def _check_unmerged_branch(number):
    """Check if a feature branch exists with commits not merged to the working branch.

    Feature branches follow ``squidsquad/*/NUMBER`` (#9478: branch+PR is
    the only mode, no toggle). If such a branch exists and has commits
    not on the working branch (main), shipping should be blocked.

    Returns (branch_name, commit_count) if unmerged branch found, None otherwise.
    """
    working = _get_working_branch()

    # List all branches matching squidsquad/*/NUMBER pattern
    result = _run_list(
        ["git", "branch", "-a", "--list", f"*squidsquad/*/{number}"],
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None

    for line in result.stdout.strip().splitlines():
        branch = line.strip().lstrip("* ")
        # Normalize remotes/origin/ prefix for comparison
        local_name = branch.replace("remotes/origin/", "")

        # Verify this branch's last path segment matches the issue number
        parts = local_name.split("/")
        if len(parts) < 3 or parts[-1] != str(number):
            continue

        # Check if branch has commits not on the working branch
        count_result = _run_list(
            ["git", "rev-list", "--count", f"{working}..{branch}"],
            check=False,
        )
        if count_result.returncode != 0:
            continue

        count = int(count_result.stdout.strip())
        if count > 0:
            return local_name, count

    return None


def _check_unmerged_pr(number):
    """Check if there's an open PR for this issue number.

    Searches for PRs with branch names matching squidsquad/*/NUMBER.
    Returns (pr_number, pr_url) if found, None otherwise.
    """
    adapter = _get_forge_adapter()
    if adapter:
        try:
            prs = adapter.list_prs(state="open", search=f"squidsquad/ {number}")
            for pr in prs:
                head = pr.get("headRefName", "")
                parts = head.split("/")
                if len(parts) >= 2 and parts[-1] == str(number):
                    return pr.get("number"), pr.get("url", "")
        except Exception:
            pass
        return None

    # Default: gh CLI
    result = _run_list(
        ["gh", "pr", "list", "--state", "open",
         "--json", "number,headRefName,url", "--limit", "20"],
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        prs = json.loads(result.stdout) if result.stdout.strip() else []
        for pr in prs:
            head = pr.get("headRefName", "")
            parts = head.split("/")
            if len(parts) >= 2 and parts[-1] == str(number):
                return pr["number"], pr.get("url", "")
    except (json.JSONDecodeError, KeyError):
        pass
    return None


def _convert_draft_pr_to_ready(number):
    """Convert draft PR to ready-for-review for an issue.

    Searches for PRs matching squidsquad/*/NUMBER. If found and draft,
    converts to ready. Silent no-op if no PR or already ready.
    """
    adapter = _get_forge_adapter()
    if adapter:
        try:
            prs = adapter.list_prs(state="open", search=f"squidsquad/ {number}")
            for pr in prs:
                head = pr.get("headRefName", "")
                parts = head.split("/")
                if len(parts) >= 2 and parts[-1] == str(number):
                    if pr.get("isDraft", False):
                        # Convert draft to ready via forge adapter (#4991 GAP-3)
                        try:
                            adapter.pr_ready(pr.get("number"))
                        except (AttributeError, Exception):
                            pass  # Adapter may not support pr_ready
        except Exception:
            pass
        return

    # Default: gh CLI
    result = _run_list(
        ["gh", "pr", "list", "--state", "open",
         "--json", "number,headRefName,isDraft", "--limit", "20"],
        check=False,
    )
    if result.returncode != 0:
        return
    try:
        prs = json.loads(result.stdout) if result.stdout.strip() else []
        for pr in prs:
            head = pr.get("headRefName", "")
            parts = head.split("/")
            if len(parts) >= 2 and parts[-1] == str(number):
                if pr.get("isDraft", False):
                    _run_list(
                        ["gh", "pr", "ready", str(pr["number"])],
                        check=False,
                    )
                return
    except (json.JSONDecodeError, KeyError):
        pass


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

    # Find the last comment by the caller role (canonicalize for matching)
    canon = _canonicalize_role(caller_role)
    # Build all prefix variants: raw, canonical, canonical-lead
    prefixes = set()
    for r in (caller_role, canon, f"{canon}-lead"):
        prefixes.add(f"**{r}**:")
        prefixes.add(f"**{r} ")
    caller_last_idx = -1
    for i, c in enumerate(comments):
        body = c.get("body", "")
        if any(body.startswith(p) for p in prefixes):
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

    # 4. Guard: TC coverage gate for pending-test -> pending-ship
    #    (NEVER bypassed, even with --force)
    if from_label == "status:pending-test" and to_label == "status:pending-ship":
        try:
            from tc_coverage import _discover_files, check_coverage
            tp, qr = _discover_files(number)
            if tp is not None:
                if qr is None:
                    _log_diagnostic(
                        "error",
                        f"TC coverage gate blocked #{number}: test plan found but no QA-RESULTS",
                    )
                    print(
                        f"BLOCKED: #{number} has a test plan ({tp.name}) but no QA-RESULTS. "
                        f"QA must complete all TCs before shipping.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                rc = check_coverage(str(tp), str(qr))
                if rc != 0:
                    _log_diagnostic(
                        "error",
                        f"TC coverage gate blocked #{number}: exit code {rc}",
                    )
                    print(
                        f"BLOCKED: #{number} failed TC coverage gate (exit {rc}). "
                        f"All TCs in the test plan must have valid results in QA-RESULTS.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
        except ImportError:
            # tc_coverage.py not available — graceful degradation
            print(
                "WARNING: tc_coverage.py not found — TC coverage gate skipped.",
                file=sys.stderr,
            )

    # 5. Guard: block shipped if unmerged PR or unmerged branch exists
    #    (never bypassed, even with --force)
    if to_label == "status:shipped":
        unmerged = _check_unmerged_pr(number)
        if unmerged:
            pr_num, pr_url = unmerged
            _log_diagnostic(
                "error",
                f"Blocked shipped transition on #{number}: unmerged PR #{pr_num}",
            )
            print(
                f"BLOCKED: Cannot ship #{number} — PR #{pr_num} is open and unmerged. "
                f"Merge the PR first: {pr_url}",
                file=sys.stderr,
            )
            sys.exit(1)

        unmerged_branch = _check_unmerged_branch(number)
        if unmerged_branch:
            branch_name, commit_count = unmerged_branch
            _log_diagnostic(
                "error",
                f"Blocked shipped transition on #{number}: branch {branch_name} "
                f"has {commit_count} unmerged commit(s)",
            )
            print(
                f"BLOCKED: Cannot ship #{number} — branch '{branch_name}' has "
                f"{commit_count} commit(s) not merged to the working branch. "
                f"Merge the branch or create a PR first.",
                file=sys.stderr,
            )
            sys.exit(1)

    adapter = _get_forge_adapter()
    if adapter:
        adapter.edit_labels(number, add=[to_label], remove=[from_label])
    else:
        _run_list(["gh", "issue", "edit", str(number), "--remove-label", from_label, "--add-label", to_label])

    # Auto-convert draft PR to ready on pending-test or pending-ship
    if to_label in ("status:pending-test", "status:pending-ship"):
        _convert_draft_pr_to_ready(number)

    # Auto-close on shipped (handle already-closed from GitHub auto-close #3747)
    if to_label == "status:shipped":
        if adapter:
            adapter.close_issue(number)
        else:
            result = _run_list(["gh", "issue", "close", str(number)], check=False)
            if result.returncode != 0 and "already closed" not in result.stderr.lower():
                print(f"WARNING: gh issue close #{number} failed: {result.stderr.strip()}",
                      file=sys.stderr)

    # Emit status-transition event on every transition (#5856)
    try:
        from event_bus import emit as _emit_event
        emit_role = (role or "unknown").replace("-lead", "")
        _emit_event("status-transition", emit_role, payload={
            "issue_number": str(number),
            "from": from_label.replace("status:", ""),
            "to": to_label.replace("status:", ""),
        })
    except (ImportError, Exception):
        pass

    print(f"#{number}: {from_label} -> {to_label}")
    return True


def _get_repo_url():
    """Get the repo URL from config.md for issue link expansion."""
    try:
        result = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "config.py"), "get", "repo"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False, cwd=str(REPO_ROOT),
        )
        repo = result.stdout.strip()
        if repo:
            # Normalize: ensure https:// prefix
            if not repo.startswith("http"):
                repo = f"https://{repo}"
            return repo.rstrip("/")
    except Exception:
        pass
    return None


def _expand_issue_refs(text):
    """Expand #NNN issue references to include full URL.

    Transforms '#123' to '#123 (https://github.com/.../issues/123)'.
    Only expands references that look like issue numbers (1+ digits after #),
    not preceded by a word character (avoids expanding inside URLs or hex codes).
    Skips references that already have a URL immediately following.
    """
    repo_url = _get_repo_url()
    if not repo_url:
        return text

    def _replace(match):
        num = match.group(1)
        # Check if already followed by a URL (avoid double-expansion)
        end = match.end()
        if end < len(text) and text[end:end + 2] == " (":
            rest = text[end + 2:]
            if rest.startswith("http"):
                return match.group(0)
        return f"#{num} ({repo_url}/issues/{num})"

    # Match #NNN not preceded by word char, with 1-5 digit issue number
    return re.sub(r'(?<!\w)#(\d{1,5})\b', _replace, text)


def comment(number, role, message, _suppress_event=False):
    """Add a discussion comment to an issue."""
    # No manual timestamps — GitHub provides them
    message = _expand_issue_refs(message)
    body = f"**{role}**: {message}"
    adapter = _get_forge_adapter()
    if adapter:
        adapter.add_comment(number, body)
    else:
        _run_list(["gh", "issue", "comment", str(number), "--body", body])
    print(f"Commented on #{number}")

    # Emit tracker-comment event (#4709) — suppressed for auto-comments from transition()
    if not _suppress_event:
        try:
            from event_bus import emit as _emit_event
            emit_role = role.split(" ")[0].replace("-lead", "")  # "skill-lead (Ralph)" → "skill"
            # Extract mentioned roles from **role**: bold patterns
            mentioned = re.findall(r'\*\*(\w+)\*\*:', message)
            preview = message[:120].replace("\n", " ")
            _emit_event("tracker-comment", emit_role, payload={
                "issue_number": str(number),
                "commenter_role": emit_role,
                "comment_preview": preview,
                "mentioned_roles": mentioned,
            })
        except (ImportError, Exception):
            pass


def get_labels(number):
    """Get label names for an issue."""
    adapter = _get_forge_adapter()
    if adapter:
        data = adapter.view_issue(number)
        labels = [l["name"] for l in data.get("labels", [])] if data else []
        print(json.dumps(labels))
        return labels
    result = _run_list(["gh", "issue", "view", str(number), "--json", "labels"])
    data = json.loads(result.stdout)
    labels = [l["name"] for l in data.get("labels", [])]
    print(json.dumps(labels))
    return labels


def get_state(number):
    """Get issue state (OPEN/CLOSED)."""
    adapter = _get_forge_adapter()
    if adapter:
        data = adapter.view_issue(number)
        state = (data or {}).get("state") or "UNKNOWN"
        print(state)
        return state
    result = _run_list(["gh", "issue", "view", str(number), "--json", "state"])
    data = json.loads(result.stdout)
    state = data["state"]
    print(state)
    return state


def close_issue(number):
    """Close an issue."""
    adapter = _get_forge_adapter()
    if adapter:
        adapter.close_issue(number)
    else:
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

    elif cmd in ("list-issues", "list-bugs"):
        if not pos:
            print(f"Usage: tracker.py {cmd} <role> [--status <s>]", file=sys.stderr)
            sys.exit(1)
        list_issues(pos[0], "issue", opts.get("status"))

    elif cmd in ("list-tasks", "list-features"):
        if not pos:
            print(f"Usage: tracker.py {cmd} <role> [--status <s>]", file=sys.stderr)
            sys.exit(1)
        list_issues(pos[0], "task", opts.get("status"))

    elif cmd == "work-queue":
        if not pos:
            print("Usage: tracker.py work-queue <role>", file=sys.stderr)
            sys.exit(1)
        work_queue(pos[0])

    elif cmd in ("create-issue", "create-bug"):
        for req in ("title", "body", "role", "severity"):
            if req not in opts:
                print(f"Missing --{req}", file=sys.stderr)
                sys.exit(1)
        create_issue(opts["title"], opts["body"], opts["role"],
                     opts["severity"], opts.get("reporter"))

    elif cmd in ("create-task", "create-feature"):
        for req in ("title", "body", "role", "priority"):
            if req not in opts:
                print(f"Missing --{req}", file=sys.stderr)
                sys.exit(1)
        create_task(opts["title"], opts["body"], opts["role"],
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
            print("Usage: tracker.py list-by-labels <labels> [--state open|closed|all]", file=sys.stderr)
            sys.exit(1)
        list_by_labels(pos[0], state=opts.get("state", "open"))

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
