#!/usr/bin/env python3
"""SquidSquad cycle_pre — pre-cycle mechanical operations.

Runs before the agent's creative phase. Handles git pull, context pressure,
working state, triage, branch setup, and writes cycle-input.json.

Usage:
    python references/scripts/cycle_pre.py <role>             # /loop mode
    python references/scripts/cycle_pre.py <role> --task <n>  # event-driven, task-scoped (#8701)

In task mode (#8701, used by event-driven agents), `cycle_pre` skips the
work-queue scan and writes a `cycle-input.json` scoped to the single task
passed via `--task`. `cycle_post.py` detects task mode by the presence of
a `task` field in `cycle-output.json` and uses task-log files keyed by
task id + timestamp rather than monotonic cycle numbers.

Exit codes:
    0 — success (cycle-input.json written, possibly degraded)
    1 — fatal error (cannot continue)
"""

import json
import shlex
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUID_DIR = REPO_ROOT / ".squidsquad"

# Import state_bus for path resolution (#3664)
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from state_bus import state_path as _state_path
except ImportError:
    def _state_path(rel):
        return SQUID_DIR / rel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Default sub-process timeout (#9904). One misbehaving sub-script must NOT
# wedge the whole pre-cycle (the symptom that produced #9903). A bounded
# timeout converts a deadlock into a recoverable per-cycle failure — the
# caller sees returncode=124 (matching POSIX `timeout` convention) and the
# existing `if result.returncode != 0` paths degrade gracefully. 60s is
# generous for tracker.py / config.py / health_check.py while still bounding
# the worst-case cycle latency at ~36 * 60s rather than infinity.
DEFAULT_SCRIPT_TIMEOUT = 60


def _run(cmd, check=False, timeout=DEFAULT_SCRIPT_TIMEOUT):
    """Run a command from repo root.

    #9904: ``timeout`` defaults to ``DEFAULT_SCRIPT_TIMEOUT`` so a single
    hanging sub-process can't wedge the cycle. On timeout we return a fake
    ``CompletedProcess`` with ``returncode=124`` (POSIX ``timeout`` exit
    code) and a diagnostic on stderr — every existing call site already
    treats ``returncode != 0`` as failure, so no caller changes are needed.
    Pass ``timeout=None`` explicitly to opt out (no current call sites do).
    """
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
            check=check, cwd=str(REPO_ROOT),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        try:
            cmd_display = shlex.join(str(c) for c in cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
        except Exception:
            cmd_display = repr(cmd)
        msg = f"TIMEOUT after {timeout}s: {cmd_display}"
        print(f"  WARNING: {msg}", file=sys.stderr)
        return subprocess.CompletedProcess(
            args=cmd, returncode=124, stdout="", stderr=msg,
        )


def _run_script(script, *args, check=False, timeout=DEFAULT_SCRIPT_TIMEOUT):
    """Run a Python script in references/scripts/.

    #9904: forwards ``timeout`` to :func:`_run` (default 60s).
    """
    return _run(
        [sys.executable, str(SCRIPT_DIR / script)] + list(args),
        check=check, timeout=timeout,
    )


def _read_file(path):
    """Read a file, return content or empty string."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _config_get(field):
    """Get a config field value. Returns empty string on failure."""
    result = _run_script("config.py", "get", field)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def _config_get_int(field, default=0):
    """Get a config field as int with safe fallback on malformed values (#8115)."""
    raw = _config_get(field)
    if not raw:
        return default
    try:
        return int(raw)
    except (ValueError, TypeError):
        return default


def _write_status_bar(role, phase, description):
    """Write status bar state atomically."""
    state_file = SQUID_DIR / role / "current-state"
    tmp_file = state_file.with_suffix(".tmp")
    content = f"{phase}|{description}"
    try:
        tmp_file.write_text(content, encoding="utf-8")
        tmp_file.replace(state_file)
    except OSError:
        pass


def _timestamp():
    """Get current timestamp in ISO 8601 format."""
    return datetime.now().isoformat(timespec="seconds")


def _timestamp_short():
    """Get HH:MM:SS timestamp."""
    return datetime.now().strftime("%H:%M:%S")


# ---------------------------------------------------------------------------
# Common operations (all roles)
# ---------------------------------------------------------------------------


def _do_pull(role=None):
    """Run git pull. Returns pull_result string (#5378).

    Inspects stdout to distinguish normal states from real errors.
    """
    args = ["git_ops.py", "pull"]
    if role:
        args.append(role)
    result = _run_script(*args)
    stdout = result.stdout.strip().lower()
    stderr = result.stderr.strip().lower()
    combined = stdout + " " + stderr

    # Check stdout content first — more reliable than exit code
    if "stash pop conflict" in combined or "stash_conflict" in combined:
        return "stash_conflict"
    if "already up to date" in combined:
        return "ok"
    if "pulled" in stdout:
        return "ok"
    if result.returncode != 0:
        return "error"
    return "ok"


def _get_branch_name(role, number):
    """Get branch name using configured pattern (#5040)."""
    pattern = _config_get("branch-pattern")
    if not pattern:
        pattern = "squidsquad/{role}/{number}"
    return pattern.format(role=role, number=number)


def _enforce_branch(role, working_state):
    """Ensure the agent is on the correct branch before pull (#4942, #5208).

    If working-state has an active task, call task-begin to ensure the
    correct feature branch. Otherwise, ensure the agent is on the
    configured working branch.

    Returns a branch_correction dict if a correction was made, or None.
    """
    # #9478 D7: branch+PR workflow is the only mode; the toggle was removed.

    task = working_state.get("task", "none")
    status = working_state.get("status", "none")

    if task != "none" and status == "in-progress":
        # Extract issue number from task field (e.g. "#4942" -> "4942")
        number = task.lstrip("#").strip()
        if number.isdigit():
            result = _run_script("git_ops.py", "task-begin", role, number)
            if result.returncode != 0:
                # Non-fatal — log and continue on current branch
                pass
        return None
    else:
        # No active task — ensure on configured working branch (#5208)
        working = _config_get("working-branch") or "main"
        current = _run(["git", "branch", "--show-current"], check=False)
        current_branch = current.stdout.strip() if current.returncode == 0 else ""
        if current_branch and current_branch != working:
            print(f"  WARNING: Agent on branch '{current_branch}', expected '{working}'. "
                  f"Switching automatically (#5208).")
            _run(["git", "checkout", working], check=False)
            return {
                "corrected": True,
                "was_on": current_branch,
                "switched_to": working,
            }
        return None


def _validate_config_version():
    """Post-pull validation: fix config.md version if it regressed (#5136).

    Compares config.md version against the latest git tag. If config.md
    has an older version (branch merge overwrote it), auto-fix to the tag version.
    """
    try:
        # Get latest version tag
        result = _run(["git", "tag", "--sort=-v:refname", "-l", "v*"], check=False)
        tags = result.stdout.strip().splitlines() if result.returncode == 0 else []
        if not tags:
            return
        latest_tag = tags[0].lstrip("v")  # e.g. "0.31.0"

        # Get config.md version
        config_version = _config_get("version")
        if not config_version:
            return

        # Compare — simple string comparison works for semver with same digit count
        # Parse into tuples for proper comparison
        def _parse_ver(v):
            try:
                return tuple(int(x) for x in v.split("."))
            except (ValueError, AttributeError):
                return (0,)

        tag_ver = _parse_ver(latest_tag)
        cfg_ver = _parse_ver(config_version)

        if cfg_ver < tag_ver:
            # Config version regressed — fix it
            _run_script("config.py", "set", "version", latest_tag)
            print(f"  [config] Version regressed ({config_version} < {latest_tag}) — "
                  f"auto-fixed to {latest_tag} (#5136)")
    except Exception:
        pass  # Non-fatal — don't block the cycle


def _discover_harness_port():
    """Discover harness port — default 7373, with `.harness-port` overrides.

    Mirrors the resolution order used by `cycle_post.py` so both pre/post
    cycle helpers agree on which harness they're talking to: this repo's
    `.squidsquad/.harness-port`, then a 5-level parent-directory walk for
    an inherited port file (clone-isolation case), then the default 7373.
    Always returns an int.
    """
    port_file = SQUID_DIR / ".harness-port"
    if port_file.exists():
        try:
            return int(port_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass

    current = REPO_ROOT.parent
    for _ in range(5):
        candidate = current / ".squidsquad" / ".harness-port"
        if candidate.exists():
            try:
                return int(candidate.read_text(encoding="utf-8").strip())
            except (ValueError, OSError):
                pass
        parent = current.parent
        if parent == current:
            break
        current = parent

    return 7373


def _query_harness_status():
    """Probe the harness API and return `"reachable"` or `"unreachable"`.

    Informational only (#4792 §5.5, Q8). The result is surfaced in
    `cycle-input.json` so the agent can self-report harness liveness; no
    cycle_pre decision branches on it. Single short-timeout GET; any
    network/parse/timeout error returns `"unreachable"`.
    """
    port = _discover_harness_port()
    url = f"http://127.0.0.1:{port}/status"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if 200 <= resp.status < 300:
                return "reachable"
            return "unreachable"
    except (urllib.error.URLError, OSError, TimeoutError):
        return "unreachable"


def _read_context_pressure(role):
    """Read context pressure for a role."""
    pressure_file = SQUID_DIR / role / "context-pressure"
    try:
        used_pct = int(_read_file(pressure_file).strip() or "0")
    except (ValueError, TypeError):
        used_pct = 0

    threshold_str = _config_get("context-threshold")
    try:
        threshold = int(threshold_str)
    except (ValueError, TypeError):
        threshold = 70

    return {
        "used_pct": used_pct,
        "threshold": threshold,
        "exceeded": used_pct >= threshold,
    }


def _read_working_state(role):
    """Parse working-state.md into structured data."""
    ws_path = _state_path(f"{role}/working-state.md")
    raw = _read_file(ws_path)

    task = "none"
    status = "none"
    phase = None
    suppressed = False
    completed_steps = []
    remaining_steps = []
    key_decisions = []
    quiet_cycles = 0
    last_processed_event_id = None

    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("- **Task**:"):
            task = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- **Status**:"):
            status = stripped.split(":", 1)[1].strip()
        elif stripped.startswith("- **Phase**:"):
            phase = stripped.split(":", 1)[1].strip()
            suppressed = True
        elif stripped.startswith("- **Quiet Cycles**:"):
            try:
                quiet_cycles = int(stripped.split(":", 1)[1].strip())
            except ValueError:
                quiet_cycles = 0
        elif stripped.startswith("- **Last Processed Event ID**:"):
            val = stripped.split(":", 1)[1].strip()
            if val and val != "none":
                last_processed_event_id = val

    # Parse list sections
    current_section = None
    for line in raw.splitlines():
        stripped = line.strip()
        if stripped.startswith("## Completed Steps"):
            current_section = "completed"
        elif stripped.startswith("## Remaining Steps"):
            current_section = "remaining"
        elif stripped.startswith("## Key Decisions"):
            current_section = "decisions"
        elif stripped.startswith("## ") or stripped.startswith("# "):
            current_section = None
        elif stripped.startswith("- ") and current_section:
            item = stripped[2:].strip()
            if current_section == "completed":
                completed_steps.append(item)
            elif current_section == "remaining":
                remaining_steps.append(item)
            elif current_section == "decisions":
                key_decisions.append(item)

    result = {
        "task": task,
        "status": status,
        "raw_content": raw,
    }

    # Role-specific fields
    if phase is not None:
        result["phase"] = phase
        result["suppressed"] = suppressed
    else:
        result["suppressed"] = False

    result["completed_steps"] = completed_steps
    result["remaining_steps"] = remaining_steps
    result["key_decisions"] = key_decisions
    result["quiet_cycles"] = quiet_cycles
    result["last_processed_event_id"] = last_processed_event_id

    return result


def _get_cycle_number(role):
    """Compute next cycle number from existing iteration logs."""
    iter_dir = _state_path(f"{role}/iterations")
    if not iter_dir.exists():
        return 1

    max_n = 0
    for f in iter_dir.glob("iter-*.md"):
        try:
            n = int(f.stem.split("-")[1])
            max_n = max(max_n, n)
        except (IndexError, ValueError):
            pass
    return max_n + 1



# Per-role event type relevance config (#5622)
# Each role receives only event types relevant to its work.
# Unlisted roles receive all events (no filtering).
_ROLE_EVENT_TYPES = {
    "pm": {"pr-merged", "compose-completed", "verification-failed", "verification-passed",
            "cycle-start", "cycle-end", "status-transition", "agent-health"},
    "qa": {"pr-merged", "compose-completed", "status-transition", "cycle-end",
            "verification-failed"},
    "skill": {"pr-merged", "compose-completed", "verification-failed", "status-transition"},
    "dm": {"status-transition", "verification-passed", "pr-merged", "compose-completed"},
}


def _filter_events_for_role(events, role):
    """Filter events to those relevant to the given role (#5622, #5868).

    Reads event filters from config.md Event Reactions section if present.
    Falls back to hardcoded _ROLE_EVENT_TYPES when section is absent.
    If the role has no configured filter, all events pass through.
    """
    # Try config-driven filters first (#5868 AC-5)
    try:
        from config import get_event_filters_for_role
        config_filters = get_event_filters_for_role(role)
        if config_filters is not None:
            return [e for e in events if e.get("event_type") in config_filters]
    except (ImportError, Exception):
        pass  # Graceful fallback to hardcoded

    # Hardcoded fallback (preserved exactly per AC-7)
    allowed = _ROLE_EVENT_TYPES.get(role)
    if not allowed:
        return events
    return [e for e in events if e.get("event_type") in allowed]


def _run_mechanical_reactions(events, role):
    """Execute mechanical reactions for high-confidence idempotent patterns (#5622).

    Reactions are conservative — they verify local state before acting.
    Returns a list of reaction summaries for inclusion in cycle-input.json.
    """
    reactions = []
    if not events:
        return reactions

    for event in events:
        event_type = event.get("event_type", "")
        payload = event.get("payload", {})

        # Skip self-emitted events to prevent loops
        if event.get("role") == role:
            continue

        # Reaction: pr-merged → log for agent awareness (PM handles transitions)
        # (#6126) Updated from pr-merge to pr-merged — harness emits this now
        # Only react on successful merges — failed merges don't trigger pipeline steps
        if event_type == "pr-merged" and role == "pm" and payload.get("success"):
            pr_number = payload.get("pr_number")
            issue_number = payload.get("issue_number")
            if pr_number and issue_number:
                reactions.append({
                    "type": "pr-merge-detected",
                    "event_id": event.get("id"),
                    "pr_number": pr_number,
                    "issue_number": issue_number,
                })

        # Reaction: pr-merged → queue reactive pull for non-PM agents (#6126 AC-9)
        if event_type == "pr-merged" and payload.get("success") and role != "pm":
            reactions.append({
                "type": "reactive-pull-needed",
                "event_id": event.get("id"),
                "pr_number": payload.get("pr_number"),
                "issue_number": payload.get("issue_number"),
            })

        # Reaction: verification-failed → surface rework context for dev
        if event_type == "verification-failed" and role in ("skill", "be", "fe"):
            issue_number = payload.get("issue_number")
            if issue_number:
                reactions.append({
                    "type": "rework-needed",
                    "event_id": event.get("id"),
                    "issue_number": issue_number,
                    "reason": payload.get("reason", "QA verification failed"),
                })

    return reactions


def _read_config_flags():
    """Read common config flags.

    #9478: ``branch_workflow`` removed — branch+PR is the only mode.
    """
    _YES = ("yes", "true", "1")
    return {
        "pr_flow": _config_get("pr-flow").lower() in _YES,
        "improvement_scanning": _config_get("improvement-scanning").lower() in _YES,
        "vault_remember": _config_get("vault-remember").lower() in _YES,
        "vault_optimize": _config_get("vault-optimize").lower() in _YES,
    }


def _get_verifiable_roles():
    """Return all roles whose items QA/PM should verify (pending-test).

    Reads dev-agents from config (e.g. 'designer, skill') and adds the
    mandatory roles (pm, qa, dm) — any role can potentially have
    pending-test items. Deduplicates and returns a sorted list.

    Note (#9318): qa was previously sourced from dev-agents because the
    pre-#6055 config listed it there. Post-#6055 qa is mandatory and
    config.md only carries dev-style optional add-ons, so we add qa
    explicitly here alongside dm and pm — same pattern every other
    role-collector uses (compose._collect_all_roles, boot_remote._get_all_roles).
    """
    roles = set()
    raw = _config_get("dev-agents")
    if raw:
        for r in raw.split(","):
            r = r.strip()
            if r:
                roles.add(r)
    else:
        # Fallback: if config returned nothing, at least include skill
        roles.add("skill")
    # Always include the mandatory roles (pm, qa, dm) — any of them can
    # have pending-test items. qa added explicitly per #9318 after
    # config.md stopped listing it in dev-agents.
    roles.add("dm")
    roles.add("pm")
    roles.add("qa")
    return sorted(roles)


# ---------------------------------------------------------------------------
# Comment fetching — latest comment per issue (#2272)
# ---------------------------------------------------------------------------


def _fetch_latest_comment(number):
    """Fetch the latest comment on an issue. Returns dict or None."""
    result = _run(
        ["gh", "issue", "view", str(number), "--json", "comments",
         "--jq", ".comments[-1] | {author: .author.login, body: .body, createdAt: .createdAt}"],
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return None


def _enrich_with_comments(items):
    """Add latest_comment to each item in a list. Modifies items in place."""
    for item in items:
        num = item.get("number")
        if num:
            comment = _fetch_latest_comment(num)
            if comment:
                item["latest_comment"] = comment


# ---------------------------------------------------------------------------
# Role-specific: Skill
# ---------------------------------------------------------------------------


def _build_skill_input(role):
    """Build cycle-input.json fields specific to the skill agent."""
    # QA-rejected items
    result = _run_script("triage.py", "qa-rejected", role, "--json")
    try:
        qa_rejected = json.loads(result.stdout) if result.returncode == 0 else []
    except (json.JSONDecodeError, ValueError):
        qa_rejected = []

    # Work queue
    result = _run_script("tracker.py", "work-queue", role)
    try:
        queue = json.loads(result.stdout) if result.returncode == 0 else []
    except (json.JSONDecodeError, ValueError):
        queue = []

    # Enrich queue items with latest comments (#2272)
    _enrich_with_comments(qa_rejected)
    _enrich_with_comments(queue)

    # Planning artifacts for queued tasks
    planning_artifacts = {}
    for item in queue:
        num = str(item.get("number", ""))
        if not num:
            continue
        artifacts = {}
        # Check PM planning dir first, then skill planning dir
        for planning_dir in [SQUID_DIR / "pm" / "planning", SQUID_DIR / role / "planning"]:
            if not planning_dir.exists():
                continue
            for f in planning_dir.glob(f"*{num}*"):
                name = f.name.upper()
                if "RESEARCH" in name:
                    artifacts["research"] = str(f.relative_to(REPO_ROOT))
                elif "CONTEXT" in name and "PHASE2" not in name:
                    artifacts["context"] = str(f.relative_to(REPO_ROOT))
                elif "TEST-PLAN" in name:
                    artifacts["test_plan"] = str(f.relative_to(REPO_ROOT))
        if artifacts:
            planning_artifacts[num] = artifacts

    # Interval
    interval_str = _config_get("interval")
    try:
        interval_minutes = int(interval_str)
    except (ValueError, TypeError):
        interval_minutes = 30

    # Test command
    test_command = _config_get("test-command") or "python tests/run_tests.py"

    config = _read_config_flags()
    config["test_command"] = test_command

    return {
        "work_queue": {
            "qa_rejected": qa_rejected,
            "queue": queue,
        },
        "planning_artifacts": planning_artifacts,
        "config": config,
        "quiet_cycle_counter": 0,  # Will be read from working_state
        "interval_minutes": interval_minutes,
        "interval_changed": False,  # Agent checks this
    }


# ---------------------------------------------------------------------------
# Role-specific: PM
# ---------------------------------------------------------------------------


def _build_pm_input(role):
    """Build cycle-input.json fields specific to the PM agent."""
    # Tracker queries
    tracker_data = {
        "pending_test_issues": [],
        "pending_test_tasks": [],
        "pending_ship_tasks": [],
        "external_issues": [],
        "open_prs": [],
    }

    # Pending test issues — query ALL verifiable roles (#4803)
    verifiable_roles = _get_verifiable_roles()
    for query_role in verifiable_roles:
        result = _run_script("tracker.py", "list-issues", query_role, "--status", "pending-test")
        try:
            if result.returncode == 0 and result.stdout.strip():
                items = json.loads(result.stdout)
                for item in (items if isinstance(items, list) else []):
                    item["source_role"] = query_role
                tracker_data["pending_test_issues"].extend(
                    items if isinstance(items, list) else []
                )
        except (json.JSONDecodeError, ValueError):
            pass

    # Pending test tasks — query ALL verifiable roles (#4803)
    for query_role in verifiable_roles:
        result = _run_script("tracker.py", "list-tasks", query_role, "--status", "pending-test")
        try:
            if result.returncode == 0 and result.stdout.strip():
                items = json.loads(result.stdout)
                for item in (items if isinstance(items, list) else []):
                    item["source_role"] = query_role
                tracker_data["pending_test_tasks"].extend(
                    items if isinstance(items, list) else []
                )
        except (json.JSONDecodeError, ValueError):
            pass

    # Pending ship — reverted to --state open (#6262: --state all included stale closed items)
    result = _run_script("tracker.py", "list-by-labels", "status:pending-ship")
    try:
        if result.returncode == 0 and result.stdout.strip():
            items = json.loads(result.stdout)
            tracker_data["pending_ship_tasks"] = items if isinstance(items, list) else []
    except (json.JSONDecodeError, ValueError):
        pass

    # External issues (unlabeled)
    result = _run_script("tracker.py", "list-all-open")
    try:
        if result.returncode == 0 and result.stdout.strip():
            items = json.loads(result.stdout)
            tracker_data["external_issues"] = [
                i for i in (items if isinstance(items, list) else [])
                if "squidsquad" not in [l.get("name", "") for l in i.get("labels", [])]
            ]
    except (json.JSONDecodeError, ValueError):
        pass

    # Open PRs
    pr_result = _run(["gh", "pr", "list", "--search", "squidsquad/", "--state", "open",
                       "--json", "number,title,state,url,headRefName", "--limit", "20"])
    try:
        if pr_result.returncode == 0 and pr_result.stdout.strip():
            tracker_data["open_prs"] = json.loads(pr_result.stdout)
    except (json.JSONDecodeError, ValueError):
        pass

    # Agent health
    health_result = _run_script("health_check.py", "--json")
    agent_health = {}
    try:
        if health_result.stdout.strip():
            health_data = json.loads(health_result.stdout)
            for entry in (health_data if isinstance(health_data, list) else []):
                r = entry.get("role", "")
                s = entry.get("status", "unknown")
                if r:
                    agent_health[r] = s
    except (json.JSONDecodeError, ValueError):
        pass

    # Merged branches (for recompose check)
    merged_branches = []
    merge_result = _run(["git", "log", "--merges", "--oneline", "--since=2 hours ago"])
    if merge_result.returncode == 0:
        for line in merge_result.stdout.splitlines():
            if "squidsquad/" in line.lower():
                merged_branches.append(line.strip())

    config = _read_config_flags()
    config["ship_threshold"] = _config_get_int("ship-threshold", 10)
    config["shipped_since_bump"] = _config_get_int("shipped-since-bump", 0)
    # Boot detection — DEPRECATED (#3807). PM no longer auto-boots agents;
    # the harness owns agent respawn via the intent state machine + 60s
    # force-kill safety net (#4792 Phase 1). Field kept as empty list for
    # backward compat with composed CLAUDE.md files that still read it.
    boot_results = []

    # Approved items — dev pushback visibility (#2494)
    approved_items = []
    result = _run_script("tracker.py", "list-by-labels", "squidsquad,status:approved")
    try:
        if result.returncode == 0 and result.stdout.strip():
            items = json.loads(result.stdout)
            approved_items = items if isinstance(items, list) else []
    except (json.JSONDecodeError, ValueError):
        pass

    # Human-blocked items — waiting-on-human visibility (#2494)
    human_blocked = []
    for blocked_label in ["blocked:human-action", "status:pending-human-setup", "status:pending-human-review"]:
        result = _run_script("tracker.py", "list-by-labels", f"squidsquad,{blocked_label}")
        try:
            if result.returncode == 0 and result.stdout.strip():
                items = json.loads(result.stdout)
                if isinstance(items, list):
                    seen = {i["number"] for i in human_blocked}
                    for item in items:
                        if item.get("number") not in seen:
                            human_blocked.append(item)
        except (json.JSONDecodeError, ValueError):
            pass

    # Recently commented items — human input visibility (#2494)
    # Find items with comments in the last cycle interval, regardless of status
    recently_commented = []
    result = _run(
        ["gh", "issue", "list", "--label", "squidsquad", "--state", "open",
         "--json", "number,title,labels,updatedAt", "--limit", "50"],
        check=False,
    )
    try:
        if result.returncode == 0 and result.stdout.strip():
            all_open = json.loads(result.stdout)
            if isinstance(all_open, list):
                for item in all_open:
                    updated = item.get("updatedAt", "")
                    if not updated:
                        continue
                    try:
                        updated_dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        now = datetime.now(updated_dt.tzinfo) if updated_dt.tzinfo else datetime.now()
                        delta = (now - updated_dt).total_seconds()
                        # Items updated within 2x iteration interval (default 60 min)
                        interval = _config_get_int("interval", 30)
                        if delta <= interval * 2 * 60:
                            recently_commented.append(item)
                    except (ValueError, TypeError):
                        pass
    except (json.JSONDecodeError, ValueError):
        pass

    # Enrich tracker items with latest comments (#2272)
    _enrich_with_comments(tracker_data["pending_test_issues"])
    _enrich_with_comments(tracker_data["pending_test_tasks"])
    _enrich_with_comments(tracker_data["pending_ship_tasks"])
    _enrich_with_comments(approved_items)
    _enrich_with_comments(human_blocked)
    _enrich_with_comments(recently_commented)

    return {
        "tracker": tracker_data,
        "approved_items": approved_items,
        "human_blocked": human_blocked,
        "recently_commented": recently_commented,
        "agent_health": agent_health,
        "boot_results": boot_results,
        "config": config,
        "merged_branches": merged_branches,
    }


# ---------------------------------------------------------------------------
# Role-specific: QA
# ---------------------------------------------------------------------------


def _build_qa_input(role):
    """Build cycle-input.json fields specific to the QA agent."""
    # Verification queue — pending test issues with branch info
    verification_queue = {
        "pending_test_issues": [],
        "pending_test_tasks": [],
    }

    # Pending test issues — query ALL verifiable roles (#4803)
    verifiable_roles = _get_verifiable_roles()
    for query_role in verifiable_roles:
        result = _run_script("tracker.py", "list-issues", query_role, "--status", "pending-test")
        try:
            if result.returncode == 0 and result.stdout.strip():
                items = json.loads(result.stdout)
                for item in (items if isinstance(items, list) else []):
                    num = item.get("number", "")
                    branch = _get_branch_name(query_role, num) if num else ""
                    item["branch"] = branch
                    item["source_role"] = query_role
                    # Check for test plan
                    test_plan_path = ""
                    for planning_dir in [SQUID_DIR / "pm" / "planning", SQUID_DIR / "qa" / "planning"]:
                        if planning_dir.exists():
                            for f in planning_dir.glob(f"*{num}*TEST-PLAN*"):
                                test_plan_path = str(f.relative_to(REPO_ROOT))
                                break
                    item["test_plan_path"] = test_plan_path
                    verification_queue["pending_test_issues"].append(item)
        except (json.JSONDecodeError, ValueError):
            pass

    # Pending test tasks — query ALL verifiable roles (#4803)
    for query_role in verifiable_roles:
        result = _run_script("tracker.py", "list-tasks", query_role, "--status", "pending-test")
        try:
            if result.returncode == 0 and result.stdout.strip():
                items = json.loads(result.stdout)
                for item in (items if isinstance(items, list) else []):
                    num = item.get("number", "")
                    branch = _get_branch_name(query_role, num) if num else ""
                    item["branch"] = branch
                    item["source_role"] = query_role
                    test_plan_path = ""
                    for planning_dir in [SQUID_DIR / "pm" / "planning", SQUID_DIR / "qa" / "planning"]:
                        if planning_dir.exists():
                            for f in planning_dir.glob(f"*{num}*TEST-PLAN*"):
                                test_plan_path = str(f.relative_to(REPO_ROOT))
                                break
                    item["test_plan_path"] = test_plan_path
                    verification_queue["pending_test_tasks"].append(item)
        except (json.JSONDecodeError, ValueError):
            pass

    # Open PRs
    open_prs = []
    pr_result = _run(["gh", "pr", "list", "--state", "open",
                       "--json", "number,title,state,url,headRefName,reviews", "--limit", "20"])
    try:
        if pr_result.returncode == 0 and pr_result.stdout.strip():
            open_prs = json.loads(pr_result.stdout)
    except (json.JSONDecodeError, ValueError):
        pass

    # Enrich verification items with latest comments (#2272)
    _enrich_with_comments(verification_queue["pending_test_issues"])
    _enrich_with_comments(verification_queue["pending_test_tasks"])

    # Agent health
    health_result = _run_script("health_check.py", "--json")
    agent_health = {}
    try:
        if health_result.stdout.strip():
            health_data = json.loads(health_result.stdout)
            for entry in (health_data if isinstance(health_data, list) else []):
                r = entry.get("role", "")
                s = entry.get("status", "unknown")
                if r:
                    agent_health[r] = s
    except (json.JSONDecodeError, ValueError):
        pass

    config = _read_config_flags()
    config["iteration_interval"] = _config_get_int("interval", 30)

    # E2E test result (run if configured)
    e2e_result = {"result": "skipped", "tests_run": 0, "failures": []}
    e2e_cmd = _config_get("e2e-tests")
    if e2e_cmd and e2e_cmd.strip() and e2e_cmd.strip().lower() not in ("(none)", "none", ""):
        # #9904: opt out of DEFAULT_SCRIPT_TIMEOUT here — E2E test suites
        # are user-configured commands that can legitimately exceed 60s.
        # Killing a long E2E run and reporting it as "failed" would be a
        # behavioral regression (DS review finding on the #9904 fix PR).
        # The tracker-style sub-scripts (tracker.py / config.py /
        # health_check.py) are bounded; arbitrary user commands are not.
        test_run = _run(shlex.split(e2e_cmd), check=False, timeout=None)
        if test_run.returncode == 0:
            e2e_result["result"] = "passed"
        else:
            e2e_result["result"] = "failed"
        # Basic parsing — agent interprets details during creative phase

    # Branch setup removed (#3296) — task-begin/task-end in git_ops.py handles
    # per-item branch checkout in the creative phase, not cycle-level pre-checkout.

    return {
        "e2e_test_result": e2e_result,
        "verification_queue": verification_queue,
        "open_prs": open_prs,
        "agent_health": agent_health,
        "config": config,
    }


# ---------------------------------------------------------------------------
# Role-specific: DM
# ---------------------------------------------------------------------------


def _build_dm_input(role):
    """Build cycle-input.json fields specific to the DM agent."""
    # Bugs assigned to DM
    bugs = []
    result = _run_script("tracker.py", "list-issues", "dm")
    try:
        if result.returncode == 0 and result.stdout.strip():
            bugs = json.loads(result.stdout)
            if not isinstance(bugs, list):
                bugs = []
    except (json.JSONDecodeError, ValueError):
        pass

    # Pending ship items — reverted to --state open (#6262: --state all included stale closed items)
    pending_ship = []
    result = _run_script("tracker.py", "list-by-labels", "status:pending-ship")
    try:
        if result.returncode == 0 and result.stdout.strip():
            items = json.loads(result.stdout)
            for item in (items if isinstance(items, list) else []):
                # Check for delivery:skip in comments
                num = item.get("number", "")
                delivery_skip = False
                if num:
                    comment_result = _run(
                        ["gh", "issue", "view", str(num), "--json", "comments"],
                        check=False,
                    )
                    try:
                        if comment_result.returncode == 0:
                            comment_data = json.loads(comment_result.stdout)
                            for comment in comment_data.get("comments", []):
                                if "delivery: skip" in comment.get("body", "").lower() or \
                                   "delivery:skip" in comment.get("body", "").lower():
                                    delivery_skip = True
                                    break
                    except (json.JSONDecodeError, ValueError):
                        pass
                item["delivery_skip"] = delivery_skip
                pending_ship.append(item)
    except (json.JSONDecodeError, ValueError):
        pass

    # Enrich pending-ship items with latest comments (#2272)
    _enrich_with_comments(pending_ship)
    _enrich_with_comments(bugs)

    # Version bump info
    ship_threshold = _config_get_int("ship-threshold", 10)
    shipped_since_bump = _config_get_int("shipped-since-bump", 0)
    current_version = _config_get("version") or "0.0.0"

    # Count open issues across all roles
    open_count = 0
    for check_role in ["skill", "pm", "qa", "dm"]:
        result = _run_script("tracker.py", "list-issues", check_role, "--status", "open")
        try:
            if result.returncode == 0 and result.stdout.strip():
                items = json.loads(result.stdout)
                open_count += len(items) if isinstance(items, list) else 0
        except (json.JSONDecodeError, ValueError):
            pass

    version_bump = {
        "ship_threshold": ship_threshold,
        "shipped_since_bump": shipped_since_bump,
        "bump_due": shipped_since_bump >= ship_threshold,
        "open_issues_count": open_count,
        "current_version": current_version,
    }

    config = _read_config_flags()

    return {
        "bugs": bugs,
        "pending_ship": pending_ship,
        "version_bump": version_bump,
        "config": config,
    }


# ---------------------------------------------------------------------------
# Branch setup for skill agent
# ---------------------------------------------------------------------------


# _setup_skill_branch removed (#3296) — replaced by git_ops.py task-begin/task-end


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

ROLE_BUILDERS = {
    "skill": _build_skill_input,
    "pm": _build_pm_input,
    "qa": _build_qa_input,
    "dm": _build_dm_input,
}


def _parse_cli_args(argv):
    """Parse `<role> [--task <number>]` from argv (post-script-name).

    Returns (role, task) where task is a string or None. Kept lightweight
    so cycle_pre stays callable from tests without rebuilding argv.
    """
    if not argv:
        return None, None
    role = argv[0]
    task = None
    i = 1
    while i < len(argv):
        if argv[i] == "--task" and i + 1 < len(argv):
            task = argv[i + 1]
            i += 2
        else:
            i += 1
    return role, task


def _reconcile_ship_counter():
    """#9772 self-heal: restore `Shipped Since Last Bump` if it regressed.

    The counter at `Auto Versioning > Shipped Since Last Bump` in config.md
    can be silently clobbered when a skill PR squash-merges a feature branch
    that branched off main BEFORE a DM ship landed (the branch's stale
    config.md overwrites the bumped counter). DM has had to manually restore
    the value twice (cycles 1120 and 1231), so this helper detects the
    regression in the DM cycle_pre and writes back the correct value.

    Derivation: count distinct issue numbers in `dm`-prefixed and `qa`-prefixed
    commit subject lines containing "ship #N" since the last `v*` tag. If the
    count exceeds the on-disk counter, restore. If git tools are missing or
    config is unreadable, return ``None`` and leave config untouched.

    Returns ``None`` (no action needed / fail-safe) or a dict
    ``{"detected": N, "restored": M, "since_tag": "vX.Y.Z"}`` if a regression
    was healed.

    Gated to DM role only at the callsite — the counter is DM-owned and
    only one writer should touch it.
    """
    import re
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field, set_field
    except Exception:
        return None
    # 1. Find the last v* tag (the last version bump). Counter resets to 0
    #    at each bump, so commits BEFORE the tag are not relevant.
    r = subprocess.run(
        ["git", "describe", "--tags", "--abbrev=0", "--match", "v*"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if r.returncode != 0 or not r.stdout.strip():
        # No version tag yet — can't establish a "since last bump" window.
        return None
    last_tag = r.stdout.strip()
    rev_range = f"{last_tag}..HEAD"
    # 2. Get commit subjects in the range.
    r = subprocess.run(
        ["git", "log", rev_range, "--format=%s"],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
    )
    if r.returncode != 0:
        return None
    # 3. Count distinct issue numbers in dm/qa ship commits. We match BOTH
    #    the DM "ship #N" pattern and the QA "verify+ship #N" pattern. Using
    #    a set deduplicates across the two roles (each shipped issue gets one
    #    DM ship commit + one QA verify+ship commit, but counts once).
    pattern = re.compile(r"#(\d+)")
    shipped_issues = set()
    for line in r.stdout.splitlines():
        low = line.lower()
        # Only commits from the shipping pipeline. Skip skill commits that
        # mention "ship" in passing (e.g. "ship count 7→8" in a working-state
        # commit message would NOT be a ship event — those commits don't have
        # the role prefix at the start).
        if not (low.startswith("dm:") or low.startswith("qa:")):
            continue
        # Require both "ship" and an issue ref. Excludes pure "restore"
        # commits like "dm: restore shipped-since-bump 7→8" which mention
        # neither "#N" nor "ship #" (the restore was triggered by the bug
        # itself; counting it would double-count).
        if "ship #" not in low and "+ship #" not in low:
            continue
        m = pattern.search(line)
        if m:
            shipped_issues.add(m.group(1))
    git_count = len(shipped_issues)
    # 4. Compare against config.md counter.
    try:
        config_raw = get_field("shipped-since-bump") or "0"
        config_count = int(config_raw)
    except (ValueError, SystemExit, Exception):
        return None
    if git_count <= config_count:
        return None  # No regression — config is at-or-ahead of git evidence
    # 5. Regression detected — restore.
    print(
        f"[🦑] WARNING: shipped-since-bump regression detected "
        f"(config={config_count}, git-derived={git_count} since "
        f"{last_tag}); restoring counter to {git_count} (#9772 self-heal)",
        file=sys.stderr,
    )
    try:
        set_field("shipped-since-bump", str(git_count))
    except Exception as e:
        print(f"[🦑] ERROR: failed to restore counter: {e}", file=sys.stderr)
        return None
    return {
        "detected": config_count,
        "restored": git_count,
        "since_tag": last_tag,
    }


def main():
    role, task_id = _parse_cli_args(sys.argv[1:])
    if not role:
        print("Usage: cycle_pre.py <role> [--task <number>]", file=sys.stderr)
        sys.exit(1)
    if role not in ROLE_BUILDERS:
        print(f"ERROR: Unknown role '{role}'. Valid: {list(ROLE_BUILDERS.keys())}",
              file=sys.stderr)
        sys.exit(1)

    ts = _timestamp_short()
    if task_id:
        print(f"[🦑 {ts}] cycle_pre starting for {role} (task #{task_id}, event-driven mode)...")
    else:
        print(f"[🦑 {ts}] cycle_pre starting for {role}...")
    _write_status_bar(role, "pulling", "pull-latest — Syncing with remote...")

    # 1a. Read working state early to determine correct branch (#4942)
    working_state = _read_working_state(role)

    # 1b. Enforce correct branch before pull (#4942, #5208)
    branch_correction = _enforce_branch(role, working_state)

    # 1c. Pull
    pull_result = _do_pull(role)

    # 1d. Ensure merge=ours driver for config.md (#5136)
    _run(["git", "config", "merge.ours.driver", "true"], check=False)

    # 1e. Post-pull config.md version validation (#5136)
    _validate_config_version()

    # 1f. #9772: DM-only self-heal for `Shipped Since Last Bump` clobbers.
    # Runs after pull so the counter check sees the freshest main state.
    ship_counter_repair = None
    if role == "dm" and not task_id:
        ship_counter_repair = _reconcile_ship_counter()

    # 2. Context pressure
    context_pressure = _read_context_pressure(role)

    # 2b. Harness reachability — informational only (#4792 §5.5, Q8).
    # Surfaced in cycle-input.json for agent self-reporting; no gating.
    harness_status = _query_harness_status()

    # 3. Cycle number
    cycle_number = _get_cycle_number(role)
    config_flags = _read_config_flags()

    # 6. Status bar
    _write_status_bar(role, "triaging", "tracker-protocol — Building work queue...")

    # 7. Role-specific input
    # #8701: task mode skips the role-specific work-queue scan. The harness
    # already chose this task; cycle_pre's only forge-side responsibility is
    # to surface the task itself plus the standard branch/state context.
    if task_id:
        role_input = {
            "task": task_id,
            "task_mode": True,
            # Cross-agent health checks intentionally omitted in event-driven
            # mode (per #8701 design: the harness owns liveness).
        }
    else:
        role_input = ROLE_BUILDERS[role](role)

    # 7b. Read event bus (#5622)
    recent_events = []
    try:
        from event_bus_reader import query as _query_events
        last_event_id = working_state.get("last_processed_event_id", None)
        recent_events = _query_events(since=last_event_id, limit=100)
        # Per-role relevance filtering (#5622 — agents keep what they care about)
        recent_events = _filter_events_for_role(recent_events, role)
    except (ImportError, Exception):
        pass

    # 7c. Mechanical reactions (#5622) — high-confidence idempotent patterns
    mechanical_reactions = _run_mechanical_reactions(recent_events, role)

    # 8. Build and write cycle-input.json
    # #8701: in task mode, cycle_number is replaced by `task` + `timestamp`
    # as the unit of work identifier. The numeric counter is kept in the
    # JSON for downstream consumers but flagged as task-mode so cycle_post
    # branches correctly.
    cycle_input = {
        "role": role,
        "cycle_number": cycle_number,
        "timestamp": _timestamp(),
        "pull_result": pull_result,
        "context_pressure": context_pressure,
        "harness_status": harness_status,
        "working_state": working_state,
        "recent_events": recent_events,
        "mechanical_reactions": mechanical_reactions,
    }
    cycle_input.update(role_input)

    # Add branch correction if one was made (#5208)
    if branch_correction:
        cycle_input["branch_correction"] = branch_correction

    # Add ship-counter repair if one was made (#9772)
    if ship_counter_repair:
        cycle_input["ship_counter_repair"] = ship_counter_repair

    # Update quiet_cycle_counter from working state for skill
    if role == "skill":
        cycle_input["quiet_cycle_counter"] = working_state.get("quiet_cycles", 0)

    # Write cycle-input.json
    output_path = SQUID_DIR / role / "cycle-input.json"
    output_path.write_text(
        json.dumps(cycle_input, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # Emit cycle-start event AFTER cycle-input.json is written (#4709)
    try:
        from event_bus import emit as _emit_event
        _emit_event("cycle-start", role, cycle_number=cycle_number)
    except (ImportError, Exception):
        pass

    ts = _timestamp_short()
    print(f"[🦑 {ts}] cycle_pre complete — wrote {output_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
