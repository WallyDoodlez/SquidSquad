#!/usr/bin/env python3
"""SquidSquad git operations — deterministic git workflow commands.

Single source of truth for git operations used by agents.

Usage:
    python scripts/git_ops.py pull                      # git pull (merge)
    python scripts/git_ops.py add-all                   # git add -A
    python scripts/git_ops.py commit <role> <message>    # git commit with role prefix
    python scripts/git_ops.py push                      # git push
    python scripts/git_ops.py commit-push <role> <msg>   # add + commit + push
    python scripts/git_ops.py commit-code <role> <branch> <msg>  # code files → branch
    python scripts/git_ops.py commit-state <role> <msg>  # .squidsquad/ files → main
    python scripts/git_ops.py branch-create <name>       # create + checkout branch
    python scripts/git_ops.py branch-switch <name>       # checkout existing branch
    python scripts/git_ops.py branch-exists <name>       # check if branch exists
    python scripts/git_ops.py branch-delete <name>       # delete local + remote branch
    python scripts/git_ops.py current-branch             # print current branch name
    python scripts/git_ops.py pr-create <title> <body>   # create PR via gh
    python scripts/git_ops.py pr-merge <number> [--strategy squash]  # merge PR via gh
    python scripts/git_ops.py task-begin <role> <number>  # checkout task's feature branch
    python scripts/git_ops.py task-end <role> <number>    # return to working branch
    python scripts/git_ops.py has-changes               # check if working tree dirty
    python scripts/git_ops.py last-hash                 # print last commit hash (short)
    python scripts/git_ops.py --help
"""

import io
import json
import subprocess
import sys
from pathlib import Path

# Ensure stdout/stderr can handle UTF-8 on Windows (cp1252 consoles choke on em dashes etc.)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent


def _get_working_branch():
    """Get the configured working branch name. Falls back to 'main'."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        branch = get_field("working-branch")
        return branch if branch else "main"
    except Exception:
        return "main"


def _run(cmd, check=True):
    """Run a shell command from repo root (only for static commands)."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        check=check, cwd=str(REPO_ROOT),
    )


def _run_list(cmd_list, check=True):
    """Run a command from repo root using list form (safe for variable args)."""
    return subprocess.run(
        cmd_list, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
        check=check, cwd=str(REPO_ROOT),
    )


def _log_diagnostic(severity, message):
    """Log a diagnostic entry (silently fails if diagnostics.py unavailable)."""
    try:
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "diagnostics.py"), "log", severity, "git_ops", message],
            capture_output=True, check=False, encoding="utf-8", errors="replace", cwd=str(REPO_ROOT),
        )
    except Exception:
        pass


def _emit(event_type, payload=None, cycle_number=None, role=None):
    """Fire-and-forget event emission (#4709). Role from arg or sys.argv."""
    try:
        from event_bus import emit
        # Use explicit role if provided, otherwise determine from sys.argv
        if role is None:
            role = "unknown"
            args = sys.argv[1:]
            # For commands like: commit-code <role> <branch> <msg>
            # or: task-begin <role> <number>
            if len(args) >= 2 and args[1] in ("pm", "skill", "qa", "dm"):
                role = args[1]
            elif len(args) >= 2 and args[0] in ("commit-code", "commit-state", "commit-push",
                                                 "commit", "task-begin", "task-end"):
                role = args[1]
        emit(event_type, role, payload=payload, cycle_number=cycle_number)
    except (ImportError, Exception):
        pass


def pull(role=None):
    """Pull with merge (#5378, #5445).

    Returns True on success, False on failure. Never crashes.
    """
    result = _run("git pull", check=False)
    if result.returncode == 0:
        print("Pulled")
        _emit("git-pull", {"result": "ok"}, role=role)
        return True

    # Check if the failure is "already up to date" or branch divergence
    combined = (result.stdout + result.stderr).lower()
    if "already up to date" in combined or "up to date" in combined:
        print("Pulled (already up to date)")
        _emit("git-pull", {"result": "ok"}, role=role)
        return True

    # Try stash + pull + pop
    stash_result = _run("git stash", check=False)
    if stash_result.returncode != 0:
        print("WARNING: git stash failed -- skipping pull", file=sys.stderr)
        return False

    retry = _run("git pull", check=False)
    if retry.returncode != 0:
        # Restore stashed changes and report failure
        _run("git stash pop", check=False)
        print(f"WARNING: git pull failed after stash -- {retry.stderr.strip()}",
              file=sys.stderr)
        return False

    pop_result = _run("git stash pop", check=False)
    if pop_result.returncode != 0:
        _log_diagnostic("warning", "stash pop failed during pull — possible merge conflict")
        # Drop the failed stash to prevent leak accumulation (#4829)
        _run("git stash drop", check=False)
        print("WARNING: stash pop failed -- dropped stale stash entry.", file=sys.stderr)
        print("Pulled (stash pop conflict -- stale stash dropped)")
        _emit("git-pull", {"result": "stash"}, role=role)
    else:
        print("Pulled (stashed and popped)")
        _emit("git-pull", {"result": "stash"}, role=role)
    return True


def add_all():
    """Stage all changes."""
    _run("git add -A")
    print("Staged all changes")


def _get_alias(role):
    """Get agent alias for Co-Authored-By trailer."""
    try:
        from config import get_alias
        return get_alias(role)
    except Exception:
        return role


def commit(role, message):
    """Commit with role prefix and Co-Authored-By trailer."""
    alias = _get_alias(role)
    full_msg = f"{role}: {message}\n\nCo-Authored-By: {alias} <noreply@squidsquad>"
    result = subprocess.run(
        ["git", "commit", "-m", full_msg],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            print("Nothing to commit")
            return False
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        return False
    print(f"Committed: {full_msg}")
    return True


def push(role=None):
    """Push to remote."""
    result = _run("git push", check=False)
    if result.returncode != 0:
        _log_diagnostic("error", f"push failed: {result.stderr.strip()[:200]}")
        print(f"ERROR: push failed: {result.stderr}", file=sys.stderr)
        return False
    # Determine branch for event payload
    branch_result = _run("git branch --show-current", check=False)
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
    _emit("git-push", {"branch": branch}, role=role)
    print("Pushed")
    return True


def commit_push(role, message):
    """Add all, commit, push — the standard agent workflow."""
    add_all()
    if commit(role, message):
        return push()
    return False


def branch_create(name):
    """Create and checkout a new branch."""
    _run_list(["git", "checkout", "-b", name])
    print(f"Created branch: {name}")


def branch_switch(name):
    """Switch to an existing branch."""
    _run_list(["git", "checkout", name])
    print(f"Switched to: {name}")


def branch_exists(name):
    """Check if a branch exists (local or remote). Prints 'true' or 'false'."""
    result = _run_list(["git", "rev-parse", "--verify", name], check=False)
    exists = result.returncode == 0
    if not exists:
        # Check remote
        result = _run_list(["git", "rev-parse", "--verify", f"origin/{name}"], check=False)
        exists = result.returncode == 0
    print("true" if exists else "false")
    return exists


def branch_delete(name):
    """Delete a local branch (and its remote tracking branch)."""
    # Delete local
    result = _run_list(["git", "branch", "-d", name], check=False)
    if result.returncode != 0:
        # Force delete if not fully merged
        result = _run_list(["git", "branch", "-D", name], check=False)
        if result.returncode != 0:
            print(f"ERROR: could not delete local branch {name}: {result.stderr}", file=sys.stderr)
            return False
    # Delete remote tracking
    _run_list(["git", "push", "origin", "--delete", name], check=False)
    print(f"Deleted branch: {name}")
    return True


def current_branch():
    """Print the name of the current branch."""
    result = _run("git branch --show-current")
    name = result.stdout.strip()
    print(name)
    return name


def pr_create(title, body):
    """Create a draft PR. Uses forge adapter for non-GitHub backends,
    gh CLI for GitHub. PRs start as drafts — QA converts to ready."""
    try:
        from forge_adapter import get_adapter, _read_forge_config
        config = _read_forge_config()
        if config["provider"] not in ("github", ""):
            adapter = get_adapter(config)
            # Need current branch as head
            branch_result = _run_list(["git", "branch", "--show-current"], check=False)
            head = branch_result.stdout.strip() if branch_result.returncode == 0 else "main"
            result = adapter.create_pr(title, body, head=head, draft=True)
            if result:
                print(f"PR created: {result.get('url', '')}")
                return result.get("url", "")
            print("ERROR: PR creation failed via forge adapter", file=sys.stderr)
            return None
    except ImportError:
        pass

    # Default: gh CLI — target the configured working branch
    base_branch = _get_working_branch()
    cmd = ["gh", "pr", "create", "--draft", "--title", title, "--body", body]
    if base_branch != "main":
        cmd.extend(["--base", base_branch])
    result = _run_list(cmd, check=False)
    if result.returncode != 0:
        print(f"ERROR: PR creation failed: {result.stderr}", file=sys.stderr)
        return None
    url = result.stdout.strip()
    # Extract PR number from URL (e.g. https://github.com/.../pull/123)
    pr_num = url.rstrip("/").rsplit("/", 1)[-1] if url else ""
    branch_result = _run("git branch --show-current", check=False)
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
    _emit("pr-create", {"pr_number": pr_num, "title": title[:80], "branch": branch})
    print(f"PR created: {url}")
    return url


def pr_ready(pr_number):
    """Convert a draft PR to ready (#4991 GAP-5). Uses forge adapter pattern."""
    try:
        from forge_adapter import get_adapter, _read_forge_config
        config = _read_forge_config()
        if config["provider"] not in ("github", ""):
            adapter = get_adapter(config)
            adapter.pr_ready(pr_number)
            print(f"PR #{pr_number} converted to ready (via adapter)")
            return True
    except (ImportError, AttributeError, Exception):
        pass

    # Default: gh CLI
    result = _run_list(
        ["gh", "pr", "ready", str(pr_number)], check=False)
    if result.returncode != 0:
        print(f"ERROR: Failed to convert PR #{pr_number} to ready: {result.stderr}",
              file=sys.stderr)
        return False
    print(f"PR #{pr_number} converted to ready")
    return True


def pr_merge(pr_number, strategy="squash"):
    """Merge a PR. Uses forge adapter for non-GitHub backends,
    gh CLI for GitHub. Returns (success, message).

    Checks PR state first — if already merged, returns success.
    On merge conflict or unexpected failure, returns failure with details.
    """
    try:
        from forge_adapter import get_adapter, _read_forge_config
        config = _read_forge_config()
        if config["provider"] not in ("github", ""):
            adapter = get_adapter(config)
            # Check state first via adapter
            pr_data = adapter.view_pr(pr_number)
            if pr_data:
                state = pr_data.get("state", "")
                if state == "MERGED":
                    print(f"PR #{pr_number} already merged")
                    return True, "already merged"
                if state == "CLOSED":
                    print(f"PR #{pr_number} closed without merge", file=sys.stderr)
                    return False, "PR closed without merge"
            success, msg = adapter.merge_pr(pr_number, strategy)
            if success:
                # pr-merge event removed (#6126) — harness emits pr-merged instead
                print(f"PR #{pr_number} merged ({strategy})")
            else:
                print(f"ERROR: PR #{pr_number} merge failed: {msg}", file=sys.stderr)
            return success, msg
    except ImportError:
        pass

    # Default: gh CLI
    # Check PR state first
    state_result = _run_list(
        ["gh", "pr", "view", str(pr_number), "--json", "state"],
        check=False,
    )
    if state_result.returncode == 0:
        try:
            state = json.loads(state_result.stdout.strip()).get("state", "")
            if state == "MERGED":
                print(f"PR #{pr_number} already merged")
                return True, "already merged"
            if state == "CLOSED":
                print(f"PR #{pr_number} closed without merge", file=sys.stderr)
                return False, "PR closed without merge"
        except (json.JSONDecodeError, AttributeError):
            pass

    # Attempt merge
    merge_args = ["gh", "pr", "merge", str(pr_number), f"--{strategy}", "--delete-branch"]
    result = _run_list(merge_args, check=False)
    if result.returncode == 0:
        # pr-merge event removed (#6126) — harness emits pr-merged instead
        print(f"PR #{pr_number} merged ({strategy})")
        # Extract linked issue number from branch name
        branch_result = _run_list(
            ["gh", "pr", "view", str(pr_number), "--json", "headRefName"],
            check=False,
        )
        if branch_result.returncode == 0:
            try:
                branch_name = json.loads(branch_result.stdout.strip()).get("headRefName", "")
                # Branch format: squidsquad/role/NUMBER
                parts = branch_name.split("/")
                if len(parts) >= 2 and parts[0] == "squidsquad" and parts[-1].isdigit():
                    issue_num = parts[-1]
                    print(f"PR linked to #{issue_num} -- GitHub auto-close will handle issue state")
            except (json.JSONDecodeError, AttributeError, IndexError):
                pass
        return True, "merged"
    else:
        error = result.stderr.strip()
        if "merge conflict" in error.lower() or "not mergeable" in error.lower():
            print(f"PR #{pr_number} has merge conflicts", file=sys.stderr)
            return False, "merge conflict"
        print(f"ERROR: PR #{pr_number} merge failed: {error}", file=sys.stderr)
        return False, f"merge failed: {error}"


def _is_state_file(path):
    """Check if a path is a state/ephemeral file that should not appear in feature PRs."""
    STATE_PREFIXES = (".squidsquad/", ".claude/")
    return any(path.startswith(p) for p in STATE_PREFIXES)


def _auto_resolve_state_conflicts():
    """Auto-resolve unmerged state files (#8653).

    cycle_pre's pull can leave unresolved conflicts in ephemeral state files
    (e.g. .squidsquad/.backlog-cache, .squidsquad/.event-state.json). Those
    files are runtime state — the next cycle rewrites them — so picking either
    side is safe. We use --theirs (the incoming branch's version) so the
    resolution matches what's already on the remote.

    Code files outside .squidsquad/ and .claude/ are left untouched and
    reported as unresolved so the caller can fail fast.

    Returns (resolved_paths, unresolved_paths).
    """
    result = _run_list(["git", "ls-files", "--unmerged"], check=False)
    if result.returncode != 0 or not result.stdout.strip():
        return [], []
    paths = set()
    for line in result.stdout.splitlines():
        if "\t" not in line:
            continue
        paths.add(line.split("\t", 1)[1].strip())
    resolved = []
    unresolved = []
    for path in sorted(paths):
        if _is_state_file(path):
            r1 = _run_list(["git", "checkout", "--theirs", "--", path], check=False)
            r2 = _run_list(["git", "add", "--", path], check=False)
            if r1.returncode == 0 and r2.returncode == 0:
                resolved.append(path)
            else:
                unresolved.append(path)
        else:
            unresolved.append(path)
    return resolved, unresolved


def _safe_checkout(target_branch):
    """Switch to target branch, stashing unstaged changes if needed.

    Handles the case where hooks/linters modify files after a commit,
    which would cause a bare `git checkout` to fail.
    """
    current = _run("git branch --show-current", check=False).stdout.strip()
    if current == target_branch:
        return True
    # Try direct checkout first
    result = _run_list(["git", "checkout", target_branch], check=False)
    if result.returncode == 0:
        return True
    # Unstaged changes blocking checkout — stash and retry
    _run("git stash -q", check=False)
    result = _run_list(["git", "checkout", target_branch], check=False)
    if result.returncode != 0:
        # Checkout failed — pop stash to restore original branch state
        _run("git stash pop -q", check=False)
        print(f"ERROR: could not switch to {target_branch}: {result.stderr}", file=sys.stderr)
        return False
    # Checkout succeeded — pop stash on the target branch
    _run("git stash pop -q", check=False)
    return True


def commit_code(role, branch, message):
    """Stage and commit only code files to a feature branch.

    Switches to the feature branch, stages everything EXCEPT state/ephemeral
    files (.squidsquad/, .claude/), commits, pushes the branch, then switches
    back to the configured working branch.
    """
    result = _run("git status --porcelain", check=False)
    if not result.stdout.strip():
        print("Nothing to commit (no changes)")
        return False

    # Get list of changed files
    # Don't strip() the full output — it removes the leading space from
    # the first line's XY status indicator (e.g. " M file.py").
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    code_files = []
    state_files = []
    for line in lines:
        # git status --porcelain format: XY<space>filename (3-char prefix)
        path = line[3:].strip().strip('"')
        # Handle renames: "old -> new"
        if " -> " in path:
            path = path.split(" -> ")[1]
        if _is_state_file(path):
            state_files.append(path)
        else:
            code_files.append(path)

    if not code_files:
        print("No code changes to commit (only state/ephemeral changes)")
        return False

    working = _get_working_branch()

    # Switch to feature branch
    current = _run("git branch --show-current").stdout.strip()
    if current != branch:
        # Check if branch exists
        check = _run_list(["git", "rev-parse", "--verify", branch], check=False)
        if check.returncode == 0:
            _run_list(["git", "checkout", branch])
        else:
            _run_list(["git", "checkout", "-b", branch])

    # Stage only code files
    for f in code_files:
        _run_list(["git", "add", f], check=False)

    # Safety: unstage config.md if it was staged by compose or other tools (#7491).
    # compose.py deploy writes event contracts to config.md, contaminating feature
    # branches. Explicitly revert it to the working branch version.
    _run_list(["git", "checkout", _get_working_branch(), "--",
               ".squidsquad/config.md"], check=False)

    # Commit
    alias = _get_alias(role)
    full_msg = f"{role}: {message}\n\nCo-Authored-By: {alias} <noreply@squidsquad>"
    result = subprocess.run(
        ["git", "commit", "-m", full_msg],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            print("Nothing to commit on branch")
            _safe_checkout(working)
            return False
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        _safe_checkout(working)
        return False

    # Push branch — failure is fatal for branch workflow (#5444)
    push_result = _run_list(["git", "push", "-u", "origin", branch], check=False)
    if push_result.returncode != 0:
        _log_diagnostic("error", f"branch push failed: {push_result.stderr.strip()[:200]}")
        print(f"ERROR: branch push failed: {push_result.stderr}", file=sys.stderr)
        _safe_checkout(working)
        return False

    # Emit git-commit (code) and git-push events (#4709)
    _emit("git-commit", {"message": message[:80], "branch": branch,
                         "files_changed": len(code_files), "commit_type": "code"})
    _emit("git-push", {"branch": branch})

    print(f"Committed code to {branch}: {message}")

    # Switch back to working branch
    _safe_checkout(working)
    return True


def commit_state(role, message):
    """Stage and commit only .squidsquad/ files to the working branch.

    Only stages files under .squidsquad/. Commits and pushes to the
    configured working branch.
    """
    result = _run("git status --porcelain", check=False)
    if not result.stdout.strip():
        print("Nothing to commit")
        return False

    lines = [l for l in result.stdout.splitlines() if l.strip()]
    state_files = []
    for line in lines:
        path = line[3:].strip().strip('"')
        if " -> " in path:
            path = path.split(" -> ")[1]
        if path.startswith(".squidsquad/"):
            state_files.append(path)

    if not state_files:
        print("No state changes to commit")
        return False

    # Must be on working branch — state changes always go there
    working = _get_working_branch()
    current = _run("git branch --show-current").stdout.strip()
    if current != working:
        print(f"ERROR: commit-state requires {working} branch (currently on {current})", file=sys.stderr)
        return False

    # Stage only .squidsquad/ files
    for f in state_files:
        _run_list(["git", "add", f], check=False)

    # Commit
    alias = _get_alias(role)
    full_msg = f"{role}: {message}\n\nCo-Authored-By: {alias} <noreply@squidsquad>"
    result = subprocess.run(
        ["git", "commit", "-m", full_msg],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            print("Nothing to commit")
            return False
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        return False

    # Emit git-commit (state) event (#4709)
    _emit("git-commit", {"message": message[:80], "branch": working,
                         "files_changed": len(state_files), "commit_type": "state"})

    # Push main — failure logged but state is committed locally (#5444)
    push_result = _run("git push", check=False)
    if push_result.returncode != 0:
        _log_diagnostic("error", f"state push failed: {push_result.stderr.strip()[:200]}")
        print(f"WARNING: state push failed: {push_result.stderr}", file=sys.stderr)
        # State push failure is non-fatal — state is committed locally,
        # next cycle's pull will sync. Return True since commit succeeded.
    else:
        _emit("git-push", {"branch": working})

    print(f"Committed state to main: {message}")
    return True


def get_branch_name(role, number):
    """Get the branch name for a task (#5040).

    Reads branch-pattern from config. Default: squidsquad/task/{number} (#6526).
    Pattern supports {role} and {number} placeholders.
    """
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        pattern = get_field("branch-pattern") or ""
    except (SystemExit, Exception):
        pattern = ""
    if not pattern:
        pattern = "squidsquad/task/{number}"
    return pattern.format(role=role, number=number)


def task_begin(role, number):
    """Check out the task's feature branch if branch-workflow is enabled (#3296).

    Uses configured branch pattern (#5040). Prints branch name to stdout
    so callers can capture it.
    If branch-workflow is disabled, this is a no-op (exit 0).
    """
    # Config gate: no-op if branch workflow disabled
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        bw = get_field("branch-workflow") or ""
        if bw.strip().lower() in ("no", "false", "0", ""):
            return
    except Exception:
        return  # Can't read config — treat as disabled

    # Auto-resolve unmerged state files from pull conflicts (#8653). Code
    # conflicts still require manual resolution — fail fast in that case so
    # the agent surfaces the real problem instead of an opaque checkout error.
    resolved, unresolved = _auto_resolve_state_conflicts()
    if resolved:
        print(f"task-begin: auto-resolved state file conflict(s): {', '.join(resolved)}")
    if unresolved:
        print(
            "ERROR: task-begin found unresolved conflicts in non-state files:\n  "
            + "\n  ".join(unresolved),
            file=sys.stderr,
        )
        print("Resolve manually (e.g. `git checkout --ours/theirs <file> && git add <file>`) before retrying task-begin.", file=sys.stderr)
        sys.exit(1)

    branch = get_branch_name(role, number)
    working = _get_working_branch()

    # Check local
    local = _run_list(["git", "rev-parse", "--verify", f"refs/heads/{branch}"], check=False)
    if local.returncode == 0:
        if not _safe_checkout(branch):
            print(f"ERROR: task-begin failed to checkout {branch}", file=sys.stderr)
            sys.exit(1)
        _emit("branch-checkout", {"branch": branch, "task_number": str(number)})
        print(branch)
        return

    # Fetch before checking remote — stale refs cause false negatives in
    # clone isolation (#5013)
    _run_list(["git", "fetch", "origin", branch], check=False)

    # Check remote
    remote = _run_list(["git", "rev-parse", "--verify", f"refs/remotes/origin/{branch}"], check=False)
    if remote.returncode == 0:
        result = _run_list(["git", "checkout", "-b", branch, f"origin/{branch}"], check=False)
        if result.returncode == 0:
            _emit("branch-checkout", {"branch": branch, "task_number": str(number)})
            print(branch)
            return
        print(f"ERROR: task-begin failed to checkout {branch} from origin: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Branch not found — create from origin/<working> to avoid contamination (#5444)
    _run_list(["git", "fetch", "origin", working], check=False)
    origin_ref = f"origin/{working}"
    ref_check = _run_list(["git", "rev-parse", "--verify", origin_ref], check=False)
    if ref_check.returncode == 0:
        result = _run_list(["git", "checkout", "-b", branch, origin_ref], check=False)
    else:
        # Fallback: create from current HEAD if origin unreachable
        result = _run_list(["git", "checkout", "-b", branch], check=False)
    if result.returncode == 0:
        _emit("branch-checkout", {"branch": branch, "task_number": str(number)})
        print(branch)
        return
    print(f"ERROR: task-begin failed to create {branch}: {result.stderr}",
          file=sys.stderr)
    sys.exit(1)


def task_end(role, number):
    """Return to the working branch after task work (#3296).

    If branch-workflow is disabled, this is a no-op.
    Warns if uncommitted changes remain on the feature branch.
    """
    # Config gate
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        bw = get_field("branch-workflow") or ""
        if bw.strip().lower() in ("no", "false", "0", ""):
            return
    except Exception:
        return

    working = _get_working_branch()

    # Safety: revert config.md to working branch version before leaving (#7491).
    # compose.py deploy may have contaminated config.md with event contract diffs.
    _run_list(["git", "checkout", working, "--",
               ".squidsquad/config.md"], check=False)

    # Warn about uncommitted changes
    status = _run("git status --porcelain", check=False)
    if status.stdout.strip():
        print(f"WARNING: uncommitted changes on current branch. "
              f"Commit via commit-code before calling task-end.", file=sys.stderr)

    if not _safe_checkout(working):
        # Fallback to main if working branch checkout fails
        _safe_checkout("main")

    _emit("branch-checkout", {"branch": working, "task_number": str(number)})


def has_changes():
    """Check if working tree has uncommitted changes."""
    result = _run("git status --porcelain")
    dirty = bool(result.stdout.strip())
    print("true" if dirty else "false")
    return dirty


def last_hash():
    """Print short hash of last commit."""
    result = _run("git rev-parse --short HEAD")
    h = result.stdout.strip()
    print(h)
    return h


def _parse_args():
    args = sys.argv[1:]
    if not args or args[0] == "--help":
        print(__doc__)
        sys.exit(0)
    return args[0], args[1:]


def main():
    cmd, rest = _parse_args()

    if cmd == "pull":
        pull(role=rest[0] if rest else None)
    elif cmd == "add-all":
        add_all()
    elif cmd == "commit":
        if len(rest) < 2:
            print("Usage: git_ops.py commit <role> <message>", file=sys.stderr)
            sys.exit(1)
        commit(rest[0], " ".join(rest[1:]))
    elif cmd == "push":
        push(role=rest[0] if rest else None)
    elif cmd == "commit-push":
        if len(rest) < 2:
            print("Usage: git_ops.py commit-push <role> <message>", file=sys.stderr)
            sys.exit(1)
        commit_push(rest[0], " ".join(rest[1:]))
    elif cmd == "branch-create":
        if not rest:
            print("Usage: git_ops.py branch-create <name>", file=sys.stderr)
            sys.exit(1)
        branch_create(rest[0])
    elif cmd == "branch-switch":
        if not rest:
            print("Usage: git_ops.py branch-switch <name>", file=sys.stderr)
            sys.exit(1)
        branch_switch(rest[0])
    elif cmd == "pr-create":
        if len(rest) < 2:
            print("Usage: git_ops.py pr-create <title> <body>", file=sys.stderr)
            sys.exit(1)
        pr_create(rest[0], " ".join(rest[1:]))
    elif cmd == "pr-ready":
        if not rest:
            print("Usage: git_ops.py pr-ready <pr-number>", file=sys.stderr)
            sys.exit(1)
        success = pr_ready(rest[0])
        sys.exit(0 if success else 1)
    elif cmd == "pr-merge":
        if not rest:
            print("Usage: git_ops.py pr-merge <pr-number> [--strategy squash|merge|rebase]", file=sys.stderr)
            sys.exit(1)
        strategy = "squash"
        if "--strategy" in rest:
            idx = rest.index("--strategy")
            if idx + 1 < len(rest):
                strategy = rest[idx + 1]
        success, msg = pr_merge(rest[0], strategy)
        sys.exit(0 if success else 1)
    elif cmd == "commit-code":
        if len(rest) < 3:
            print("Usage: git_ops.py commit-code <role> <branch> <message>", file=sys.stderr)
            sys.exit(1)
        commit_code(rest[0], rest[1], " ".join(rest[2:]))
    elif cmd == "commit-state":
        if len(rest) < 2:
            print("Usage: git_ops.py commit-state <role> <message>", file=sys.stderr)
            sys.exit(1)
        commit_state(rest[0], " ".join(rest[1:]))
    elif cmd == "branch-exists":
        if not rest:
            print("Usage: git_ops.py branch-exists <name>", file=sys.stderr)
            sys.exit(1)
        branch_exists(rest[0])
    elif cmd == "branch-delete":
        if not rest:
            print("Usage: git_ops.py branch-delete <name>", file=sys.stderr)
            sys.exit(1)
        branch_delete(rest[0])
    elif cmd == "current-branch":
        current_branch()
    elif cmd == "task-begin":
        if len(rest) < 2:
            print("Usage: git_ops.py task-begin <role> <number>", file=sys.stderr)
            sys.exit(1)
        task_begin(rest[0], rest[1])
    elif cmd == "task-end":
        if len(rest) < 2:
            print("Usage: git_ops.py task-end <role> <number>", file=sys.stderr)
            sys.exit(1)
        task_end(rest[0], rest[1])
    elif cmd == "has-changes":
        has_changes()
    elif cmd == "last-hash":
        last_hash()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
