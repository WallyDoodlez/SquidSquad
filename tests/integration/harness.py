"""SquidSquad Integration Test Harness.

Provides create/teardown helpers for GitHub Issues, git branches, and temp files.
All test artifacts are prefixed for easy identification and guaranteed cleanup.
"""

import json
import os
import subprocess
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

# Prefixes for test artifacts
ISSUE_PREFIX = "[TEST] "
BRANCH_PREFIX = "test/"
TEST_LABEL = "squidsquad-test"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _run(cmd_list: list, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command from repo root using list form (safe for variable args)."""
    return subprocess.run(
        cmd_list, capture_output=True, text=True,
        check=check, cwd=str(REPO_ROOT),
    )


# --- GitHub Issues ---

def create_test_issue(title: str, labels: str = "", body: str = "Auto-created by test harness.") -> int:
    """Create a GitHub Issue prefixed with [TEST]. Returns issue number."""
    full_title = f"{ISSUE_PREFIX}{title}"
    all_labels = TEST_LABEL
    if labels:
        all_labels += f",{labels}"
    result = _run([
        "gh", "issue", "create",
        "--title", full_title,
        "--body", body,
        "--label", all_labels,
    ])
    # gh issue create returns a URL like https://github.com/owner/repo/issues/72
    url = result.stdout.strip()
    return int(url.rstrip("/").split("/")[-1])


def close_test_issue(number: int) -> None:
    """Close and label a test issue for cleanup."""
    _run(["gh", "issue", "close", str(number)], check=False)


def delete_test_issue(number: int) -> None:
    """Delete a test issue (requires admin). Falls back to closing."""
    result = _run(["gh", "issue", "delete", str(number), "--yes"], check=False)
    if result.returncode != 0:
        close_test_issue(number)


def edit_test_issue(number: int, remove_label: str = "", add_label: str = "") -> None:
    """Edit labels on a test issue."""
    cmd = ["gh", "issue", "edit", str(number)]
    if remove_label:
        cmd.extend(["--remove-label", remove_label])
    if add_label:
        cmd.extend(["--add-label", add_label])
    _run(cmd)


def get_issue_labels(number: int, retries: int = 3, delay: float = 2.0) -> list[str]:
    """Get label names for an issue. Retries to handle GH API race conditions."""
    for attempt in range(retries):
        result = _run(["gh", "issue", "view", str(number), "--json", "labels"])
        data = json.loads(result.stdout)
        labels = [l["name"] for l in data.get("labels", [])]
        if labels or attempt == retries - 1:
            return labels
        time.sleep(delay)


def get_issue_state(number: int) -> str:
    """Get issue state (OPEN/CLOSED)."""
    result = _run(["gh", "issue", "view", str(number), "--json", "state"])
    data = json.loads(result.stdout)
    return data["state"]


def cleanup_test_issues() -> int:
    """Find and close/delete all [TEST] prefixed issues. Returns count cleaned."""
    result = _run(
        ["gh", "issue", "list", "--label", TEST_LABEL, "--state", "all",
         "--json", "number", "--limit", "100"],
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return 0
    issues = json.loads(result.stdout)
    for issue in issues:
        delete_test_issue(issue["number"])
    return len(issues)


# --- Git Branches ---

def create_test_branch(name: str) -> str:
    """Create a test branch prefixed with test/. Returns full branch name."""
    full_name = f"{BRANCH_PREFIX}{name}"
    _run(["git", "branch", full_name], check=False)
    return full_name


def delete_test_branch(name: str) -> None:
    """Delete a local test branch."""
    full_name = name if name.startswith(BRANCH_PREFIX) else f"{BRANCH_PREFIX}{name}"
    _run(["git", "branch", "-D", full_name], check=False)


def cleanup_test_branches() -> int:
    """Delete all test/ prefixed local branches. Returns count cleaned."""
    result = _run(["git", "branch", "--list", "test/*"], check=False)
    if not result.stdout.strip():
        return 0
    branches = [b.strip() for b in result.stdout.strip().split("\n") if b.strip()]
    for branch in branches:
        _run(["git", "branch", "-D", branch], check=False)
    return len(branches)


# --- Temp Files ---

@contextmanager
def temp_test_file(name: str = "test-artifact.md", content: str = "test"):
    """Create a temp file in the repo, yield its path, then clean up."""
    path = REPO_ROOT / ".squidsquad" / f"_test_{name}"
    try:
        path.write_text(content)
        yield path
    finally:
        if path.exists():
            path.unlink()


def cleanup_test_files() -> int:
    """Remove any _test_ prefixed files in .squidsquad/. Returns count cleaned."""
    sqdir = REPO_ROOT / ".squidsquad"
    if not sqdir.exists():
        return 0
    count = 0
    for f in sqdir.glob("_test_*"):
        f.unlink()
        count += 1
    return count


# --- Master Cleanup ---

def cleanup_all() -> dict:
    """Run all cleanup routines. Returns counts per category."""
    return {
        "issues": cleanup_test_issues(),
        "branches": cleanup_test_branches(),
        "files": cleanup_test_files(),
    }


def verify_clean() -> list[str]:
    """Verify no test artifacts remain. Returns list of any found."""
    problems = []

    # Check issues
    result = _run(
        ["gh", "issue", "list", "--label", TEST_LABEL, "--state", "all",
         "--json", "number", "--limit", "10"],
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        issues = json.loads(result.stdout)
        open_issues = [i for i in issues if True]  # all states
        if open_issues:
            problems.append(f"{len(open_issues)} test issues still exist")

    # Check branches
    result = _run(["git", "branch", "--list", "test/*"], check=False)
    if result.stdout.strip():
        problems.append(f"Test branches remain: {result.stdout.strip()}")

    # Check files
    sqdir = REPO_ROOT / ".squidsquad"
    if sqdir.exists():
        test_files = list(sqdir.glob("_test_*"))
        if test_files:
            problems.append(f"Test files remain: {[str(f) for f in test_files]}")

    return problems
