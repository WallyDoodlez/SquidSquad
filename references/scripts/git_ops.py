#!/usr/bin/env python3
"""SquidSquad git operations — deterministic git workflow commands.

Single source of truth for git operations used by agents.

Usage:
    python scripts/git_ops.py pull                      # git pull --rebase
    python scripts/git_ops.py add-all                   # git add -A
    python scripts/git_ops.py commit <role> <message>    # git commit with role prefix
    python scripts/git_ops.py push                      # git push
    python scripts/git_ops.py commit-push <role> <msg>   # add + commit + push
    python scripts/git_ops.py branch-create <name>       # create + checkout branch
    python scripts/git_ops.py branch-switch <name>       # checkout existing branch
    python scripts/git_ops.py pr-create <title> <body>   # create PR via gh
    python scripts/git_ops.py has-changes               # check if working tree dirty
    python scripts/git_ops.py last-hash                 # print last commit hash (short)
    python scripts/git_ops.py --help
"""

import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent


def _run(cmd, check=True):
    """Run a shell command from repo root (only for static commands)."""
    return subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        check=check, cwd=str(REPO_ROOT),
    )


def _run_list(cmd_list, check=True):
    """Run a command from repo root using list form (safe for variable args)."""
    return subprocess.run(
        cmd_list, capture_output=True, text=True,
        check=check, cwd=str(REPO_ROOT),
    )


def _log_diagnostic(severity, message):
    """Log a diagnostic entry (silently fails if diagnostics.py unavailable)."""
    try:
        subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "diagnostics.py"), "log", severity, "git_ops", message],
            capture_output=True, check=False, cwd=str(REPO_ROOT),
        )
    except Exception:
        pass


def pull():
    """Pull with rebase."""
    result = _run("git pull --rebase", check=False)
    if result.returncode != 0:
        # Try stash + pull + pop
        _run("git stash")
        _run("git pull --rebase")
        pop_result = _run("git stash pop", check=False)
        if pop_result.returncode != 0:
            _log_diagnostic("warning", "stash pop failed during pull — possible merge conflict")
            print("WARNING: stash pop failed (possible conflict). Changes remain in stash.", file=sys.stderr)
            print("Pulled (stash pop conflict — run 'git stash show' to inspect)")
        else:
            print("Pulled (stashed and popped)")
    else:
        print("Pulled")
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
        capture_output=True, text=True, check=False, cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        if "nothing to commit" in result.stdout + result.stderr:
            print("Nothing to commit")
            return False
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        return False
    print(f"Committed: {full_msg}")
    return True


def push():
    """Push to remote."""
    result = _run("git push", check=False)
    if result.returncode != 0:
        _log_diagnostic("error", f"push failed: {result.stderr.strip()[:200]}")
        print(f"ERROR: push failed: {result.stderr}", file=sys.stderr)
        return False
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


def pr_create(title, body):
    """Create a PR via gh CLI."""
    result = _run_list(
        ["gh", "pr", "create", "--title", title, "--body", body],
        check=False,
    )
    if result.returncode != 0:
        print(f"ERROR: PR creation failed: {result.stderr}", file=sys.stderr)
        return None
    url = result.stdout.strip()
    print(f"PR created: {url}")
    return url


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
        pull()
    elif cmd == "add-all":
        add_all()
    elif cmd == "commit":
        if len(rest) < 2:
            print("Usage: git_ops.py commit <role> <message>", file=sys.stderr)
            sys.exit(1)
        commit(rest[0], " ".join(rest[1:]))
    elif cmd == "push":
        push()
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
    elif cmd == "has-changes":
        has_changes()
    elif cmd == "last-hash":
        last_hash()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
