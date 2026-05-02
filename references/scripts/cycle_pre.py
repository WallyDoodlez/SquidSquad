#!/usr/bin/env python3
"""SquidSquad cycle_pre — pre-cycle mechanical operations.

Runs before the agent's creative phase. Handles git pull, context pressure,
working state, triage, branch setup, and writes cycle-input.json.

Usage:
    python references/scripts/cycle_pre.py <role>
    python references/scripts/cycle_pre.py skill
    python references/scripts/cycle_pre.py pm
    python references/scripts/cycle_pre.py qa
    python references/scripts/cycle_pre.py dm

Exit codes:
    0 — success (cycle-input.json written, possibly degraded)
    1 — fatal error (cannot continue)
"""

import json
import shlex
import subprocess
import sys
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


def _run(cmd, check=False):
    """Run a command from repo root."""
    return subprocess.run(
        cmd, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        check=check, cwd=str(REPO_ROOT),
    )


def _run_script(script, *args, check=False):
    """Run a Python script in references/scripts/."""
    return _run([sys.executable, str(SCRIPT_DIR / script)] + list(args), check=check)


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


def _do_pull():
    """Run git pull. Returns pull_result string."""
    result = _run_script("git_ops.py", "pull")
    stdout = result.stdout.strip().lower()
    if result.returncode != 0:
        return "error"
    if "stash pop conflict" in stdout or "stash_conflict" in stdout:
        return "stash_conflict"
    if "conflict" in stdout:
        return "conflict"
    return "ok"


def _enforce_branch(role, working_state):
    """Ensure the agent is on the correct branch before pull (#4942).

    If working-state has an active task, call task-begin to ensure the
    correct feature branch. Otherwise, ensure the agent is on the
    working branch (main).
    """
    branch_workflow = _config_get("branch-workflow").lower() in ("yes", "true", "1")
    if not branch_workflow:
        return

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
    else:
        # No active task — ensure on working branch
        working = _config_get("working-branch") or "main"
        current = _run(["git", "branch", "--show-current"], check=False)
        current_branch = current.stdout.strip() if current.returncode == 0 else ""
        if current_branch and current_branch != working:
            _run(["git", "checkout", working], check=False)


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



def _read_config_flags():
    """Read common config flags."""
    return {
        "branch_workflow": _config_get("branch-workflow").lower() == "yes",
        "pr_flow": _config_get("pr-flow").lower() == "yes",
        "improvement_scanning": _config_get("improvement-scanning").lower() == "yes",
        "vault_remember": _config_get("vault-remember").lower() == "yes",
        "vault_optimize": _config_get("vault-optimize").lower() == "yes",
    }


def _dir_exists(role):
    """Check if a role's directory exists."""
    return (SQUID_DIR / role).is_dir()


def _get_verifiable_roles():
    """Return all roles whose items QA/PM should verify (pending-test).

    Reads dev-agents from config (e.g. 'designer, qa, skill') and adds
    dm and pm — any role can potentially have pending-test items.
    Deduplicates and returns a sorted list.
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
    # Always include dm and pm — they can have pending-test items too
    roles.add("dm")
    roles.add("pm")
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
    # Check agent presence
    qa_present = _dir_exists("qa")
    dm_present = _dir_exists("dm")

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

    # Pending ship
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
    config["ship_threshold"] = int(_config_get("ship-threshold") or "10")
    config["shipped_since_bump"] = int(_config_get("shipped-since-bump") or "0")
    # Boot detection — DEPRECATED (#3807). PM no longer auto-boots agents.
    # Wrapper handles all respawning via .stop-after-cycle sentinel.
    # Field kept as empty list for backward compat until all agents redeployed.
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
                        interval = int(_config_get("interval") or "30")
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
        "qa_present": qa_present,
        "dm_present": dm_present,
        "e2e_test_result": None,  # PM runs E2E during creative phase if QA absent
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
                    branch = f"squidsquad/{query_role}/{num}" if num else ""
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
                    branch = f"squidsquad/{query_role}/{num}" if num else ""
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
    config["iteration_interval"] = int(_config_get("interval") or "30")

    # E2E test result (run if configured)
    e2e_result = {"result": "skipped", "tests_run": 0, "failures": []}
    e2e_cmd = _config_get("e2e-tests")
    if e2e_cmd and e2e_cmd.strip() and e2e_cmd.strip().lower() not in ("(none)", "none", ""):
        test_run = _run(shlex.split(e2e_cmd), check=False)
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

    # Pending ship items
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
    ship_threshold = int(_config_get("ship-threshold") or "10")
    shipped_since_bump = int(_config_get("shipped-since-bump") or "0")
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


def main():
    if len(sys.argv) < 2:
        print("Usage: cycle_pre.py <role>", file=sys.stderr)
        sys.exit(1)

    role = sys.argv[1]
    if role not in ROLE_BUILDERS:
        print(f"ERROR: Unknown role '{role}'. Valid: {list(ROLE_BUILDERS.keys())}",
              file=sys.stderr)
        sys.exit(1)

    ts = _timestamp_short()
    print(f"[🦑 {ts}] cycle_pre starting for {role}...")
    _write_status_bar(role, "pulling", "pull-latest — Syncing with remote...")

    # 1a. Read working state early to determine correct branch (#4942)
    working_state = _read_working_state(role)

    # 1b. Enforce correct branch before pull (#4942)
    _enforce_branch(role, working_state)

    # 1c. Pull
    pull_result = _do_pull()

    # 2. Context pressure
    context_pressure = _read_context_pressure(role)

    # 3. Cycle number
    cycle_number = _get_cycle_number(role)
    config_flags = _read_config_flags()

    # 6. Status bar
    _write_status_bar(role, "triaging", "tracker-protocol — Building work queue...")

    # 7. Role-specific input
    role_input = ROLE_BUILDERS[role](role)

    # 8. Build and write cycle-input.json
    cycle_input = {
        "role": role,
        "cycle_number": cycle_number,
        "timestamp": _timestamp(),
        "pull_result": pull_result,
        "context_pressure": context_pressure,
        "working_state": working_state,
    }
    cycle_input.update(role_input)

    # Update quiet_cycle_counter from working state for skill
    if role == "skill":
        cycle_input["quiet_cycle_counter"] = working_state.get("quiet_cycles", 0)

    # Write cycle-input.json
    output_path = SQUID_DIR / role / "cycle-input.json"
    output_path.write_text(
        json.dumps(cycle_input, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    ts = _timestamp_short()
    print(f"[🦑 {ts}] cycle_pre complete — wrote {output_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
