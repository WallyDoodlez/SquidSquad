#!/usr/bin/env python3
"""SquidSquad cycle_post — post-cycle mechanical operations.

Runs after the agent's creative phase. Reads cycle-output.json and handles
all git commits, pushes, status transitions, iteration logging, and cleanup.

Usage:
    python references/scripts/cycle_post.py <role>

Exit codes:
    0 — success
    1 — fatal error (invalid output, cannot continue)
"""

import json
import re
import subprocess
import sys
import urllib.request
import urllib.error
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

# Import state_bus for path resolution and state-branch commits (#3664)
sys.path.insert(0, str(SCRIPT_DIR))
try:
    from state_bus import state_path as _state_path, is_state_file, commit_and_push as _state_commit, _worktree_exists
except ImportError:
    def _state_path(rel):
        return SQUID_DIR / rel
    def is_state_file(rel):
        return False
    def _state_commit(msg, role="unknown"):
        return True
    def _worktree_exists():
        return False

# Required top-level fields in cycle-output.json
REQUIRED_FIELDS = {"role", "cycle_number", "cycle_type"}
VALID_CYCLE_TYPES = {"active", "quiet", "suppressed"}

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


def _config_get(field):
    """Read a field from config.md. Returns empty string on failure."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        return get_field(field) or ""
    except Exception:
        return ""


def _get_working_branch():
    """Get the configured working branch name. Falls back to 'main'."""
    branch = _config_get("working-branch")
    return branch if branch else "main"


def _run_script(script, *args, check=False):
    """Run a Python script in references/scripts/."""
    return _run([sys.executable, str(SCRIPT_DIR / script)] + list(args), check=check)


def _timestamp_short():
    """Get HH:MM:SS timestamp."""
    return datetime.now().strftime("%H:%M:%S")


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


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_output(data):
    """Validate cycle-output.json structure. Returns list of errors."""
    errors = []

    if not isinstance(data, dict):
        return ["cycle-output.json must be a JSON object"]

    for field in REQUIRED_FIELDS:
        if field not in data:
            errors.append(f"Missing required field: {field}")

    cycle_type = data.get("cycle_type", "")
    if cycle_type and cycle_type not in VALID_CYCLE_TYPES:
        errors.append(f"Invalid cycle_type '{cycle_type}'. Valid: {VALID_CYCLE_TYPES}")

    # Validate status_transitions structure
    for i, t in enumerate(data.get("status_transitions", [])):
        if not isinstance(t, dict):
            errors.append(f"status_transitions[{i}] must be an object")
            continue
        for key in ("number", "from", "to"):
            if key not in t:
                errors.append(f"status_transitions[{i}] missing '{key}'")

    return errors


# ---------------------------------------------------------------------------
# Post-cycle operations
# ---------------------------------------------------------------------------


def _verify_remote_branch(number, role="skill"):
    """Best-effort check that a feature branch exists on remote (#5444, #5526).

    Returns True if branch is on remote, False if not, None if check failed.
    Non-blocking — network failure returns None (proceed with warning).
    """
    try:
        from config import get_field
        bw = (get_field("branch-workflow") or "").strip().lower()
        if bw not in ("yes", "true", "1"):
            return True  # Branch workflow off — no branch expected
        pattern = get_field("branch-pattern") or "squidsquad/task/{number}"
        branch = pattern.replace("{number}", str(number)).replace("{role}", role)
    except Exception:
        return None  # Can't read config

    result = _run(["git", "ls-remote", "--heads", "origin", branch], check=False)
    if result.returncode != 0:
        return None  # Network failure — don't block
    return branch in result.stdout


def _do_status_transitions(data, role):
    """Execute status transitions via tracker.py."""
    transitions = data.get("status_transitions", [])
    role_label = f"{role}-lead"

    for t in transitions:
        number = t.get("number")
        from_status = t.get("from", "")
        to_status = t.get("to", "")

        if not number or not from_status or not to_status:
            print(f"WARNING: Skipping invalid transition: {t}", file=sys.stderr)
            continue

        # Verify remote branch exists before pending-test transition (#5444)
        if to_status == "pending-test" and role in ("skill",):
            remote_ok = _verify_remote_branch(number, role)
            if remote_ok is False:
                print(f"WARNING: #{number} → pending-test blocked: feature branch "
                      f"not found on remote. Push may have failed.", file=sys.stderr)
                continue
            elif remote_ok is None:
                print(f"WARNING: #{number} → pending-test: could not verify remote "
                      f"branch (network?). Proceeding anyway.", file=sys.stderr)

        result = _run_script(
            "tracker.py", "transition",
            str(number), from_status, to_status,
            "--role", role_label,
        )

        if result.returncode != 0:
            print(f"WARNING: Transition #{number} {from_status} → {to_status} failed: "
                  f"{result.stderr.strip()}", file=sys.stderr)
        else:
            print(f"  Transition: #{number} {from_status} → {to_status}")


def _do_tracker_comments(data, role):
    """Post tracker comments."""
    comments = data.get("tracker_comments", [])
    role_label = f"{role}-lead"

    for c in comments:
        number = c.get("number")
        message = c.get("message", "")

        if not number or not message:
            continue

        result = _run_script(
            "tracker.py", "comment",
            str(number), "--role", role_label, "--message", message,
        )

        if result.returncode != 0:
            print(f"WARNING: Comment on #{number} failed: {result.stderr.strip()}",
                  file=sys.stderr)


def _do_iteration_log(data, role):
    """Create iteration log entry."""
    cycle_number = data.get("cycle_number", 0)
    cycle_type = data.get("cycle_type", "quiet")
    summary = data.get("iteration_summary", "")

    if cycle_type == "quiet":
        result = _run_script(
            "cycle.py", "log-iteration", role, str(cycle_number),
            "--quiet", "--notes", summary or "No actionable work",
        )
    else:
        result = _run_script(
            "cycle.py", "log-iteration", role, str(cycle_number),
            "--work", summary or "Active cycle",
            "--notes", "",
        )

    # Cleanup old logs
    _run_script("cycle.py", "cleanup-iterations", role)

    if result.returncode == 0:
        print(f"  Iteration log: iter-{cycle_number}.md")


_AUTOCLOSE_RE = re.compile(
    r'\b(fix(?:e[sd])?|close[sd]?|resolve[sd]?)\s+(#\d+)',
    re.IGNORECASE,
)


def _sanitize_commit_msg(msg: str) -> str:
    """Escape GitHub auto-close keywords in commit messages.

    GitHub interprets 'fixed #123', 'closes #456', 'resolves #789' in commit
    messages pushed to the default branch as directives to close those issues.
    This is harmful for cycle commits that reference issues without intending
    to close them (#4038). Replace the keyword with a hyphenated form that
    preserves readability without triggering auto-close.
    """
    # Insert a zero-width space (U+200B) between keyword and #
    return _AUTOCLOSE_RE.sub(
        lambda m: f"{m.group(1)} \u200b{m.group(2)}", msg
    )


_DISPOSABLE_PATTERNS = [
    "gen_*.py", "migrate_*.py.bak", "*.scratch.py", "*.scratch.md",
    "*.debug.log", "*.debug.json",
]


def _check_disposable_files():
    """Warn if any disposable files are staged for commit (#4081)."""
    result = _run(["git", "diff", "--cached", "--name-only"], check=False)
    if result.returncode != 0:
        return
    staged = result.stdout.strip().splitlines()
    import fnmatch
    warnings = []
    for f in staged:
        name = f.rsplit("/", 1)[-1] if "/" in f else f
        for pat in _DISPOSABLE_PATTERNS:
            if fnmatch.fnmatch(name, pat):
                warnings.append(f)
                break
    if warnings:
        print(
            f"WARNING: Disposable files staged for commit (#4081): "
            f"{', '.join(warnings)}. Consider removing before push.",
            file=sys.stderr,
        )


def _do_commit_push(data, role):
    """Handle git commit and push operations."""
    _check_disposable_files()
    cycle_type = data.get("cycle_type", "quiet")
    commit_msg = data.get("commit_message") or data.get("state_commit_message", "")
    commit_msg = _sanitize_commit_msg(commit_msg)

    if not commit_msg:
        commit_msg = f"{role}: cycle {data.get('cycle_number', '?')} — {cycle_type}"

    # Read branch_workflow from config.md directly — not from agent-written
    # cycle-output.json which may be stale or missing (#5444)
    branch_workflow = False
    try:
        bw = _config_get("branch-workflow")
        branch_workflow = bw.strip().lower() in ("yes", "true", "1")
    except Exception:
        pass

    # Skill agent with branch workflow: split commits
    code_commit = data.get("code_commit")
    if role == "skill" and branch_workflow and code_commit:
        branch = code_commit.get("branch", "")
        code_msg = _sanitize_commit_msg(code_commit.get("message", "code changes"))

        if branch:
            result = _run_script("git_ops.py", "commit-code", role, branch, code_msg)
            combined = (result.stdout + result.stderr).lower()
            if result.returncode != 0:
                # Distinguish nothing-to-commit from push failure (#5444)
                if "nothing to commit" in combined or "no code changes" in combined:
                    # Code already committed by agent (#4837) — try pushing
                    print(f"  Nothing new to commit — ensuring branch is pushed")
                    branch_check = _run(
                        ["git", "rev-parse", "--verify", branch], check=False)
                    if branch_check.returncode == 0:
                        push_result = _run(
                            ["git", "push", "-u", "origin", branch], check=False)
                        if push_result.returncode == 0:
                            print(f"  Branch {branch} pushed (code already committed)")
                        else:
                            print(f"ERROR: Branch push failed: "
                                  f"{push_result.stderr.strip()}", file=sys.stderr)
                else:
                    # Real failure (push failed, commit error, etc.)
                    print(f"ERROR: Code commit/push failed: {result.stderr.strip()}",
                          file=sys.stderr)
            else:
                print(f"  Code commit to {branch}")

            # Create PR if needed — must be on the feature branch (#4837)
            if code_commit.get("pr_needed"):
                pr_title = code_commit.get("pr_title", f"{role}: {branch}")
                pr_body = code_commit.get("pr_body", f"Branch: {branch}")
                # Sanitize PR body — GitHub auto-closes issues when PR body
                # contains "Closes #N" and the PR is merged to default branch.
                # SquidSquad manages issue lifecycle via tracker.py, not PR merges.
                pr_body = _sanitize_commit_msg(pr_body)
                # gh pr create uses the current branch as head — ensure
                # we're on the feature branch before creating the PR.
                cur = _run(
                    ["git", "branch", "--show-current"], check=False)
                cur_branch = cur.stdout.strip() if cur.returncode == 0 else ""
                if cur_branch != branch:
                    _run(["git", "checkout", branch], check=False)
                result = _run_script("git_ops.py", "pr-create", pr_title, pr_body)
                if result.returncode == 0:
                    pr_url = result.stdout.strip().split("PR created: ")[-1].strip()
                    print(f"  PR created: {pr_url}")
                    # Comment PR URL on tracker issue (#4991 GAP-9)
                    issue_number = branch.split("/")[-1] if "/" in branch else ""
                    if issue_number.isdigit() and pr_url:
                        _run_script("tracker.py", "comment", issue_number,
                                    "--role", f"{role}-lead",
                                    "--message", f"PR opened: {pr_url}")
                # Switch back — state commit below needs working branch
                if cur_branch and cur_branch != branch:
                    _run(["git", "checkout", cur_branch], check=False)

        # State commit to working branch
        state_msg = _sanitize_commit_msg(data.get("state_commit_message", commit_msg))
        working = _get_working_branch()
        current = _run(["git", "branch", "--show-current"], check=False)
        current_branch = current.stdout.strip() if current.returncode == 0 else ""

        if current_branch != working:
            _run(["git", "checkout", working], check=False)

        result = _run_script("git_ops.py", "commit-state", role, state_msg)
        if result.returncode != 0:
            # Fallback: commit-push everything
            _run_script("git_ops.py", "commit-push", role, state_msg)
        else:
            print(f"  State commit to {working}")

    elif role == "qa":
        # QA: switch back to working branch before committing
        working = _get_working_branch()
        current = _run(["git", "branch", "--show-current"], check=False)
        current_branch = current.stdout.strip() if current.returncode == 0 else ""

        if current_branch != working:
            _run(["git", "checkout", working], check=False)

        # #8691: scope commit to QA's domain so foreign uncommitted files
        # (other agents' work in the same clone) don't get bundled in.
        _run_script("git_ops.py", "commit-role-scoped", role, commit_msg)
        print(f"  Committed and pushed (QA → main)")

    else:
        # #8691: PM/DM/other roles also commit only their own domain.
        _run_script("git_ops.py", "commit-role-scoped", role, commit_msg)
        print(f"  Committed and pushed")

    # Commit state files to state branch if worktree exists (#3664)
    if _worktree_exists():
        state_msg = f"cycle {data.get('cycle_number', '?')} state"
        _state_commit(state_msg, role)


def _do_version_bump(data, role):
    """Execute version bump sequence (DM only)."""
    bump = data.get("version_bump")
    if not bump or not bump.get("new_version"):
        return

    new_version = bump["new_version"]
    items = bump.get("items_included", [])

    print(f"  Version bump: → {new_version}")

    # Update config.md version
    _run_script("config.py", "set", "version", new_version)

    # Update SKILL.md version (in frontmatter)
    skill_md = REPO_ROOT / "SKILL.md"
    if skill_md.exists():
        content = skill_md.read_text(encoding="utf-8")
        content = re.sub(r'version:\s*[\d.]+', f'version: {new_version}', content, count=1)
        skill_md.write_text(content, encoding="utf-8")

    # DM always handles CHANGELOG entries (#6261). No PM fallback.

    # Commit, tag, push — stage only version-bump files (not git add -A, #3494)
    bump_files = [".squidsquad/config.md", "CHANGELOG.md"]
    if skill_md.exists():
        bump_files.append("SKILL.md")
    _run(["git", "add", "--"] + bump_files)

    # Guard: skip commit/tag/push if nothing was staged (#5126)
    diff_check = _run(["git", "diff", "--cached", "--quiet"])
    if diff_check.returncode == 0:
        print(f"  Version bump v{new_version}: no staged changes — skipping commit/tag/push")
        return

    _run(["git", "commit", "-m", f"chore: bump version to v{new_version}"])

    # Check if tag exists
    tag_check = _run(["git", "tag", "-l", f"v{new_version}"])
    if not tag_check.stdout.strip():
        _run(["git", "tag", f"v{new_version}"])

    _run(["git", "push"])
    _run(["git", "push", "--tags"])

    # Reset counter
    _run_script("config.py", "set", "shipped-since-bump", "0")

    print(f"  Version v{new_version} tagged and pushed")


def _do_restart_sentinel(data, role):
    """Write self-restart sentinel if needed.

    DEPRECATED: Agents should no longer set restart_needed. Context pressure
    restarts are handled by _do_stop_after_cycle_check() and the harness
    intent API (#4966). This function is kept for one version of backward
    compatibility only.
    """
    if not data.get("restart_needed"):
        return False

    reason = data.get("restart_reason", "unknown")
    sentinel = SQUID_DIR / role / ".restart"
    sentinel.write_text(reason, encoding="utf-8")
    print(f"  Restart sentinel written (deprecated): {reason}")
    return True


def _discover_harness_port():
    """Discover harness port — default 7373 + parent-dir walk for .harness-port (#4966).

    Returns port number or None if harness is not discoverable.
    """
    # First try: read .harness-port from this repo's .squidsquad/
    port_file = SQUID_DIR / ".harness-port"
    if port_file.exists():
        try:
            return int(port_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass

    # Second try: walk parent directories to find .squidsquad/.harness-port
    # (clone isolation — agent clone may be a child of the primary repo)
    current = REPO_ROOT.parent
    for _ in range(5):  # max 5 levels up
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

    # Fall back to default port
    return 7373


def _query_harness_intent(role):
    """Query harness API for agent intent (#4966).

    Returns intent string ("running", "stopping", "restarting") or None on failure.
    Safe default on failure: None (caller treats as "continue running").
    """
    port = _discover_harness_port()
    if port is None:
        return None

    url = f"http://127.0.0.1:{port}/agents/{role}"
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("intent")
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        # Safe default: harness unreachable, continue running
        return None


def _do_stop_after_cycle_check(data, role):
    """Check harness intent API and context pressure (#4966).

    Two independent exit triggers:
    1. Harness intent: if intent is "stopping" or "restarting", exit 42
    2. Context pressure: if exceeded, exit 42 (harness will respawn)

    Safe default on API failure: continue running (exit 0).

    Returns True if agent should exit for restart.
    """
    # 1. Query harness API for intent (replaces .stop-after-cycle file check)
    intent = _query_harness_intent(role)
    if intent in ("stopping", "restarting"):
        print(f"  Harness intent={intent}. Agent will exit for {'stop' if intent == 'stopping' else 'restart'}.")
        return True

    # 2. Check context pressure from cycle-input.json
    ctx = data.get("context_pressure", {})
    if not ctx:
        # Try reading from cycle-input.json directly
        input_path = SQUID_DIR / role / "cycle-input.json"
        if input_path.exists():
            try:
                input_data = json.loads(input_path.read_text(encoding="utf-8"))
                ctx = input_data.get("context_pressure", {})
            except (json.JSONDecodeError, OSError):
                pass

    exceeded = ctx.get("exceeded", False)
    used_pct = ctx.get("used_pct", 0)

    if exceeded:
        print(f"  Context pressure at {used_pct}% — agent will exit for restart.")
        return True

    return False


def _do_working_state_update(data, role):
    """Update working state file if agent provided update content."""
    update = data.get("working_state_update")
    if not update:
        return

    ws_path = _state_path(f"{role}/working-state.md")
    ws_path.parent.mkdir(parents=True, exist_ok=True)
    ws_path.write_text(update, encoding="utf-8")


def _advance_event_cursor(data, role):
    """Advance the event bus cursor in working-state.md after successful cycle (#5622).

    Only advances if recent_events were present in cycle-input.json.
    Cursor advances AFTER creative phase (crash safety — if agent crashes,
    events are re-read next cycle).
    """
    # Read cycle-input.json to get the events that were processed
    input_path = SQUID_DIR / role / "cycle-input.json"
    if not input_path.exists():
        return

    try:
        input_data = json.loads(input_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    recent_events = input_data.get("recent_events", [])
    if not recent_events:
        return

    # The last event's ID becomes the new cursor
    last_event_id = recent_events[-1].get("id")
    if not last_event_id:
        return

    # Update working-state.md with the new cursor
    ws_path = _state_path(f"{role}/working-state.md")
    if not ws_path.exists():
        return

    content = ws_path.read_text(encoding="utf-8")

    # Replace existing cursor line or add it
    cursor_line = f"- **Last Processed Event ID**: {last_event_id}"
    if "- **Last Processed Event ID**:" in content:
        content = re.sub(
            r"- \*\*Last Processed Event ID\*\*:.*",
            cursor_line,
            content,
        )
    else:
        # Add after the last header field (Status or Started)
        lines = content.splitlines()
        insert_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("- **Status**:"):
                insert_idx = i + 1
            elif line.strip().startswith("- **Started**:"):
                insert_idx = i + 1
        if insert_idx is not None:
            lines.insert(insert_idx, cursor_line)
            content = "\n".join(lines) + "\n"
        else:
            # Fallback: append after first blank line
            content = content.rstrip() + f"\n{cursor_line}\n"

    ws_path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print("Usage: cycle_post.py <role>", file=sys.stderr)
        sys.exit(1)

    role = sys.argv[1]
    ts = _timestamp_short()

    # Read cycle-output.json
    output_path = SQUID_DIR / role / "cycle-output.json"
    if not output_path.exists():
        print(f"[🦑 {ts}] WARNING: No cycle-output.json found for {role}. "
              "Agent may have crashed. Skipping post-processing.", file=sys.stderr)
        _write_status_bar(role, "idle", "")
        return 0

    try:
        raw = output_path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[🦑 {ts}] ERROR: Invalid JSON in cycle-output.json: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate
    errors = _validate_output(data)
    if errors:
        print(f"[🦑 {ts}] ERROR: Invalid cycle-output.json:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    print(f"[🦑 {ts}] cycle_post starting for {role} (cycle {data.get('cycle_number', '?')})...")
    _write_status_bar(role, "committing", f"git-commit — Post-processing cycle...")

    # 1. Commit and push FIRST — PR must exist before status transitions (#4991 GAP-1)
    #    Status transitions trigger auto-conversion (draft→ready) which needs the PR.
    _do_commit_push(data, role)

    # 2. Status transitions (after commits — PR exists for auto-conversion)
    _do_status_transitions(data, role)

    # 3. Tracker comments
    _do_tracker_comments(data, role)

    # 4. Working state update
    _do_working_state_update(data, role)

    # 4b. Advance event bus cursor (#5622)
    _advance_event_cursor(data, role)

    # 5. Iteration log
    _do_iteration_log(data, role)

    # 6. Version bump (DM only)
    if role == "dm":
        _do_version_bump(data, role)

    # 7. Cleanup cycle-output.json
    try:
        output_path.unlink()
    except OSError:
        pass

    # 8. Emit cycle-end event (#4709)
    try:
        from event_bus import emit as _emit_event
        _emit_event("cycle-end", role, payload={
            "cycle_type": data.get("cycle_type", ""),
            "summary": data.get("iteration_summary", "")[:60],
        }, cycle_number=data.get("cycle_number"))
    except (ImportError, Exception):
        pass

    # 9. Intent + context pressure check (MUST be last — after commit, after log)
    # Queries harness API for intent, checks context pressure. Exit 42 = harness respawns.
    stop_for_restart = _do_stop_after_cycle_check(data, role)

    # 9. Status bar
    if stop_for_restart:
        _write_status_bar(role, "restarting", "Restart — harness intent or context pressure")
    else:
        _write_status_bar(role, "idle", "")

    ts = _timestamp_short()
    print(f"[🦑 {ts}] cycle_post complete for {role}")

    # Exit code 42 signals harness to respawn (#4966)
    if stop_for_restart:
        return 42
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
