#!/usr/bin/env python3
"""SquidSquad state bus — manage state branch worktree for agent state.

Provides read/write operations for agent state on the dedicated state
branch via a git worktree at .squidsquad-state/.

Usage:
    python scripts/state_bus.py init              # Create state branch + worktree
    python scripts/state_bus.py read <path>       # Read file from state worktree
    python scripts/state_bus.py write <path>      # Write stdin to state worktree
    python scripts/state_bus.py commit <message>  # Commit and push state changes
    python scripts/state_bus.py status            # Show state branch info
    python scripts/state_bus.py --help

Exit codes:
    0 — success
    1 — operation failed
    2 — usage error
"""

import json
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_MD = REPO_ROOT / ".squidsquad" / "config.md"
STATE_WORKTREE = REPO_ROOT / ".squidsquad-state"

DEFAULT_WORKING_BRANCH = "stag"
DEFAULT_STATE_BRANCH = "squid-squad"


def _run(cmd, check=True, cwd=None):
    """Run a git command. Returns CompletedProcess."""
    return subprocess.run(
        cmd, capture_output=True, text=True, check=check,
        cwd=cwd or str(REPO_ROOT),
    )


def _read_branch_config():
    """Read branch names from config.md. Returns (working, state)."""
    if not CONFIG_MD.exists():
        return DEFAULT_WORKING_BRANCH, DEFAULT_STATE_BRANCH
    try:
        text = CONFIG_MD.read_text(encoding="utf-8")
        working = DEFAULT_WORKING_BRANCH
        state = DEFAULT_STATE_BRANCH
        m = re.search(r"Working Branch\*\*:\s*(\S+)", text)
        if m:
            working = m.group(1)
        m = re.search(r"State Branch\*\*:\s*(\S+)", text)
        if m:
            state = m.group(1)
        return working, state
    except Exception:
        return DEFAULT_WORKING_BRANCH, DEFAULT_STATE_BRANCH


def _state_branch_exists():
    """Check if the state branch exists (local or remote)."""
    _, state_branch = _read_branch_config()
    result = _run(
        ["git", "rev-parse", "--verify", f"refs/heads/{state_branch}"],
        check=False,
    )
    if result.returncode == 0:
        return True
    # Check remote
    result = _run(
        ["git", "rev-parse", "--verify", f"refs/remotes/origin/{state_branch}"],
        check=False,
    )
    return result.returncode == 0


def _worktree_exists():
    """Check if the state worktree exists."""
    return STATE_WORKTREE.exists() and (STATE_WORKTREE / ".git").exists()


def init():
    """Initialize state branch and worktree. Idempotent."""
    _, state_branch = _read_branch_config()

    # Create orphan branch if it doesn't exist
    if not _state_branch_exists():
        print(f"Creating orphan state branch '{state_branch}'...")

        # Capture current branch so we can restore on failure (#3290)
        current_ref = _run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"], check=False
        )
        original_branch = current_ref.stdout.strip() if current_ref.returncode == 0 else None

        readme_path = REPO_ROOT / "README.md"
        try:
            # Create orphan branch with an initial commit
            _run(["git", "checkout", "--orphan", state_branch])
            _run(["git", "rm", "-rf", "--cached", "."], check=False)
            _run(["git", "clean", "-fd"], check=False)

            # Create initial structure — write directly to repo root
            # (orphan branch has a clean working tree after rm + clean)
            readme_path.write_text(
                "# SquidSquad State Bus\n\n"
                "This branch stores agent state. Never merge into main.\n",
                encoding="utf-8",
            )
            _run(["git", "add", "README.md"])
            _run(["git", "commit", "-m", "init: state bus branch"])
            _run(["git", "push", "-u", "origin", state_branch], check=False)
        finally:
            # Always restore the original branch (#3290)
            if original_branch and original_branch != state_branch:
                result = _run(["git", "checkout", original_branch], check=False)
                if result.returncode != 0:
                    # Last resort: try the configured working branch
                    working_branch, _ = _read_branch_config()
                    _run(["git", "checkout", working_branch], check=False)
    else:
        print(f"State branch '{state_branch}' already exists.")

    # Create worktree if it doesn't exist
    if not _worktree_exists():
        print(f"Creating worktree at {STATE_WORKTREE}...")
        _run([
            "git", "worktree", "add",
            str(STATE_WORKTREE), state_branch,
        ], check=False)

        # Add to .gitignore if not already there
        gitignore = REPO_ROOT / ".gitignore"
        if gitignore.exists():
            content = gitignore.read_text(encoding="utf-8")
            if ".squidsquad-state/" not in content:
                with open(gitignore, "a", encoding="utf-8") as f:
                    f.write("\n.squidsquad-state/\n")
        print("Worktree created.")
    else:
        print("Worktree already exists.")

    return 0


# ---------------------------------------------------------------------------
# Path resolution — state files vs main files (#3664)
# ---------------------------------------------------------------------------

# Directory and file names that belong on the state branch (high-churn agent state).
# Everything else stays on main (code, templates, config, vault, planning).
_STATE_DIRS = {"iterations", "diagnostics"}
_STATE_FILES = {"working-state.md", "scan-history.md"}


def is_state_file(rel_path):
    """Return True if rel_path (relative to .squidsquad/) is a state-branch file.

    Matches directory names and file basenames in path segments, handling
    paths with or without trailing slashes (e.g. "skill/iterations",
    "skill/iterations/iter-1.md", "diagnostics/diagnostic.jsonl").
    """
    rel = str(rel_path).replace("\\", "/").rstrip("/")
    parts = rel.split("/")
    # Check if any path segment is a state directory
    for part in parts:
        if part in _STATE_DIRS:
            return True
    # Check if the filename is a state file
    basename = parts[-1] if parts else ""
    if basename in _STATE_FILES:
        return True
    return False


def state_path(rel_path):
    """Resolve a .squidsquad/ relative path to its actual filesystem location.

    If the path is a state file AND the state worktree exists, returns the
    path under .squidsquad-state/. Otherwise returns the path under
    .squidsquad/ (graceful fallback for old installs or non-state files).

    Args:
        rel_path: path relative to .squidsquad/ (e.g. "skill/iterations/iter-1.md")

    Returns:
        Path object to the resolved location.
    """
    if is_state_file(rel_path) and _worktree_exists():
        return STATE_WORKTREE / rel_path
    return REPO_ROOT / ".squidsquad" / rel_path


def state_dir(rel_path):
    """Like state_path but ensures the parent directory exists."""
    p = state_path(rel_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def read_file(path):
    """Read a file from the state worktree."""
    if not _worktree_exists():
        print("ERROR: State worktree not initialized. Run: state_bus.py init",
              file=sys.stderr)
        return None
    full_path = STATE_WORKTREE / path
    if not full_path.exists():
        return None
    return full_path.read_text(encoding="utf-8")


def write_file(path, content):
    """Write a file to the state worktree."""
    if not _worktree_exists():
        print("ERROR: State worktree not initialized. Run: state_bus.py init",
              file=sys.stderr)
        return False
    full_path = STATE_WORKTREE / path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    return True


def commit_and_push(message, role="unknown"):
    """Commit and push state changes. Retries on conflict."""
    if not _worktree_exists():
        print("ERROR: State worktree not initialized.", file=sys.stderr)
        return False

    _, state_branch = _read_branch_config()
    cwd = str(STATE_WORKTREE)

    # Stage all changes
    _run(["git", "add", "-A"], cwd=cwd)

    # Check if there's anything to commit
    result = _run(["git", "status", "--porcelain"], cwd=cwd)
    if not result.stdout.strip():
        return True  # Nothing to commit

    # Commit — check return code to avoid pushing nothing (#7589)
    commit_result = _run([
        "git", "commit", "-m", f"{role}: {message}",
    ], cwd=cwd, check=False)
    if commit_result.returncode != 0:
        print(f"WARNING: State commit failed: {commit_result.stderr.strip()[:200]}",
              file=sys.stderr)
        return False

    # Push with retry (up to 3 attempts for concurrent conflicts)
    for attempt in range(3):
        result = _run(
            ["git", "push", "origin", state_branch],
            cwd=cwd, check=False,
        )
        if result.returncode == 0:
            return True
        # Pull and retry
        _run(["git", "pull", "origin", state_branch],
             cwd=cwd, check=False)

    print(f"WARNING: State push failed after 3 attempts", file=sys.stderr)
    return False


def status():
    """Show state branch info."""
    _, state_branch = _read_branch_config()
    info = {
        "state_branch": state_branch,
        "branch_exists": _state_branch_exists(),
        "worktree_exists": _worktree_exists(),
        "worktree_path": str(STATE_WORKTREE),
    }
    print(json.dumps(info, indent=2))
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        return 0

    cmd = args[0]

    if cmd == "init":
        return init()
    elif cmd == "read":
        if len(args) < 2:
            print("Usage: state_bus.py read <path>", file=sys.stderr)
            return 2
        content = read_file(args[1])
        if content is None:
            return 1
        print(content, end="")
        return 0
    elif cmd == "write":
        if len(args) < 2:
            print("Usage: state_bus.py write <path>", file=sys.stderr)
            return 2
        content = sys.stdin.read()
        return 0 if write_file(args[1], content) else 1
    elif cmd == "commit":
        msg = args[1] if len(args) > 1 else "state update"
        role = "unknown"
        for i, a in enumerate(args):
            if a == "--role" and i + 1 < len(args):
                role = args[i + 1]
        return 0 if commit_and_push(msg, role) else 1
    elif cmd == "status":
        return status()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
