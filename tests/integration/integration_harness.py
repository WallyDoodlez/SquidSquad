"""SquidSquad Integration Test Harness.

Provides create/teardown helpers for GitHub Issues, git branches, and temp files.
All test artifacts are prefixed for easy identification and guaranteed cleanup.
"""

import atexit
import json
import os
import shlex
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

# Prefixes for test artifacts
ISSUE_PREFIX = "[TEST] "
BRANCH_PREFIX = "test/"
TEST_LABEL = "squidsquad-test"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Body markers every harness-created issue starts with -- the unlabeled-leak
# sweep in cleanup_test_issues() matches on these plus ISSUE_PREFIX (#14096).
BODY_MARKER = "Auto-created by"

# Issue numbers this process created (#14096). Cleanup covers these even when
# the TEST_LABEL never landed, and an atexit hook sweeps them on abort paths
# (unittest skips tearDownClass when setUpClass raises).
_CREATED_ISSUES: set[int] = set()

sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))
try:
    from gh_identity import gh_env
except ImportError:  # fail-open: ambient gh identity, as before
    def gh_env(cmd_list):
        return None


def _run(cmd_list, check: bool = True) -> subprocess.CompletedProcess:
    """Run a command from repo root.

    Takes a list (safe for variable args) or a string, which is split with
    shlex so it works off Windows too. gh calls are pinned to the repo's push
    identity (#14096): under a read-only ambient account GitHub silently drops
    issue labels, so TEST_LABEL never landed and label-based cleanup missed
    every issue (20 leaked on 2026-07-20).
    """
    if isinstance(cmd_list, str):
        cmd_list = shlex.split(cmd_list)
    return subprocess.run(
        cmd_list, capture_output=True, text=True, encoding="utf-8",
        errors="replace", check=check, cwd=str(REPO_ROOT),
        env=gh_env(cmd_list),
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
    number = int(url.rstrip("/").split("/")[-1])
    _CREATED_ISSUES.add(number)
    # Labels are dropped silently (no error) when the gh identity lacks
    # triage access. Fail loudly instead of leaving an issue no label-based
    # cleanup can find -- and remove it first, because a raise here in
    # setUpClass means tearDownClass never runs.
    if TEST_LABEL not in get_issue_labels(number):
        delete_test_issue(number)
        raise RuntimeError(
            f"#{number} was created without the {TEST_LABEL!r} label -- the gh "
            f"identity lacks triage access to this repo (labels are dropped "
            f"silently). Removed it; fix the gh identity and re-run (#14096)."
        )
    return number


def close_test_issue(number: int) -> None:
    """Close and label a test issue for cleanup."""
    _run(["gh", "issue", "close", str(number)], check=False)


def delete_test_issue(number: int) -> None:
    """Delete a test issue (requires admin). Falls back to closing."""
    result = _run(["gh", "issue", "delete", str(number), "--yes"], check=False)
    if result.returncode != 0:
        close_test_issue(number)
    _CREATED_ISSUES.discard(number)


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


def _list_json(cmd_list: list) -> list:
    result = _run(cmd_list, check=False)
    if result.returncode != 0 or not (result.stdout or "").strip():
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def _unlabeled_leaks() -> set[int]:
    """Open harness issues that never got TEST_LABEL (#14096).

    Matches strictly on the harness's own markers: title starts with
    ISSUE_PREFIX AND body starts with BODY_MARKER. A search hit alone is not
    enough -- GitHub search tokenizes, so real issues can match the query.
    """
    rows = _list_json(
        ["gh", "issue", "list", "--state", "open", "--limit", "100",
         "--search", f'"{ISSUE_PREFIX.strip()}" in:title "{BODY_MARKER}" in:body',
         "--json", "number,title,body"])
    return {
        r["number"] for r in rows
        if r.get("title", "").startswith(ISSUE_PREFIX)
        and (r.get("body") or "").startswith(BODY_MARKER)
    }


def cleanup_test_issues() -> int:
    """Delete (or close) every harness-created issue. Returns count cleaned.

    Covers three sets (#14096): issues carrying TEST_LABEL, issues this
    process created (registry -- survives a dropped label), and open issues
    matching the harness's title/body markers (sweeps leaks from earlier runs).
    """
    labeled = {
        i["number"] for i in _list_json(
            ["gh", "issue", "list", "--label", TEST_LABEL, "--state", "all",
             "--json", "number", "--limit", "100"])
    }
    targets = labeled | set(_CREATED_ISSUES) | _unlabeled_leaks()
    for number in sorted(targets):
        delete_test_issue(number)
    return len(targets)


def _cleanup_registry_at_exit() -> None:
    """Last-resort sweep of this process's issues (abort paths, #14096)."""
    for number in sorted(_CREATED_ISSUES):
        try:
            delete_test_issue(number)
        except Exception:
            pass


atexit.register(_cleanup_registry_at_exit)


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
        if issues:
            problems.append(f"{len(issues)} test issues still exist")
    leaks = _unlabeled_leaks()
    if leaks:
        problems.append(f"{len(leaks)} unlabeled test issues still open: {sorted(leaks)}")

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
