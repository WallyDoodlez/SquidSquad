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


def _do_commit_push(data, role):
    """Handle git commit and push operations."""
    cycle_type = data.get("cycle_type", "quiet")
    commit_msg = data.get("commit_message") or data.get("state_commit_message", "")

    if not commit_msg:
        commit_msg = f"{role}: cycle {data.get('cycle_number', '?')} — {cycle_type}"

    config_flags = data.get("config", {})
    branch_workflow = config_flags.get("branch_workflow", False)

    # Skill agent with branch workflow: split commits
    code_commit = data.get("code_commit")
    if role == "skill" and branch_workflow and code_commit:
        branch = code_commit.get("branch", "")
        code_msg = code_commit.get("message", "code changes")

        if branch:
            result = _run_script("git_ops.py", "commit-code", role, branch, code_msg)
            if result.returncode != 0:
                print(f"WARNING: Code commit failed: {result.stderr.strip()}",
                      file=sys.stderr)
            else:
                print(f"  Code commit to {branch}")

            # Create PR if needed
            if code_commit.get("pr_needed"):
                pr_title = code_commit.get("pr_title", f"{role}: {branch}")
                pr_body = code_commit.get("pr_body", f"Branch: {branch}")
                result = _run_script("git_ops.py", "pr-create", pr_title, pr_body)
                if result.returncode == 0:
                    print(f"  PR created: {result.stdout.strip()}")

        # State commit to main
        state_msg = data.get("state_commit_message", commit_msg)
        # Need to be on main for state commit
        current = _run(["git", "branch", "--show-current"], check=False)
        current_branch = current.stdout.strip() if current.returncode == 0 else ""

        if current_branch != "main":
            _run(["git", "checkout", "main"], check=False)

        result = _run_script("git_ops.py", "commit-state", role, state_msg)
        if result.returncode != 0:
            # Fallback: commit-push everything
            _run_script("git_ops.py", "commit-push", role, state_msg)
        else:
            print(f"  State commit to main")

    elif role == "qa":
        # QA: switch back to main before committing
        current = _run(["git", "branch", "--show-current"], check=False)
        current_branch = current.stdout.strip() if current.returncode == 0 else ""

        if current_branch != "main":
            _run(["git", "checkout", "main"], check=False)

        _run_script("git_ops.py", "commit-push", role, commit_msg)
        print(f"  Committed and pushed (QA → main)")

    else:
        # Default: commit-push on current branch (main)
        _run_script("git_ops.py", "commit-push", role, commit_msg)
        print(f"  Committed and pushed")


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
        import re
        content = re.sub(r'version:\s*[\d.]+', f'version: {new_version}', content, count=1)
        skill_md.write_text(content, encoding="utf-8")

    # Add CHANGELOG entry
    changelog = REPO_ROOT / "CHANGELOG.md"
    if changelog.exists():
        old_content = changelog.read_text(encoding="utf-8")
        date_str = datetime.now().strftime("%Y-%m-%d")
        items_str = "\n".join(f"- #{n}" for n in items)
        new_section = f"## [{new_version}] — {date_str}\n\n### Shipped\n{items_str}\n\n"
        # Insert after first line (title)
        lines = old_content.split("\n", 1)
        if len(lines) > 1:
            new_content = lines[0] + "\n\n" + new_section + lines[1]
        else:
            new_content = old_content + "\n\n" + new_section
        changelog.write_text(new_content, encoding="utf-8")

    # Commit, tag, push
    _run(["git", "add", "-A"])
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
    """Write self-restart sentinel if needed."""
    if not data.get("restart_needed"):
        return False

    reason = data.get("restart_reason", "unknown")
    sentinel = SQUID_DIR / role / ".restart"
    sentinel.write_text(reason, encoding="utf-8")
    print(f"  Restart sentinel written: {reason}")
    return True


def _do_working_state_update(data, role):
    """Update working state file if agent provided update content."""
    update = data.get("working_state_update")
    if not update:
        return

    ws_path = SQUID_DIR / role / "working-state.md"
    ws_path.write_text(update, encoding="utf-8")


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

    # 1. Status transitions (before commits — so tracker reflects reality)
    _do_status_transitions(data, role)

    # 2. Tracker comments
    _do_tracker_comments(data, role)

    # 3. Working state update
    _do_working_state_update(data, role)

    # 4. Iteration log
    _do_iteration_log(data, role)

    # 5. Version bump (DM only)
    if role == "dm":
        _do_version_bump(data, role)

    # 6. Commit and push
    _do_commit_push(data, role)

    # 7. Restart sentinel (after commit — safety rule)
    restarting = _do_restart_sentinel(data, role)

    # 8. Cleanup cycle-output.json
    try:
        output_path.unlink()
    except OSError:
        pass

    # 9. Status bar
    if restarting:
        _write_status_bar(role, "restarting", f"Self-restart — {data.get('restart_reason', '')}")
    else:
        _write_status_bar(role, "idle", "")

    ts = _timestamp_short()
    print(f"[🦑 {ts}] cycle_post complete for {role}")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
