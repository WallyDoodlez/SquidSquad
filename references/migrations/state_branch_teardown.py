#!/usr/bin/env python3
"""One-time retirement of the state branch + its worktree, per clone (#14144).

The `squid-squad` state branch and its `.squidsquad-state/` worktree are
retired: agent state lives on main under `.squidsquad/<alias>/`. This module
removes both from one clone, backup first:

  1. backup (outside git tracking, under the gitignored `.squidsquad/backups/`):
     a `git bundle` of the local state branch (verified with
     `git bundle verify`) and a byte-for-byte copy of the worktree's files
     (uncommitted diagnostics included). Nothing is pushed anywhere.
  2. teardown: `git worktree remove --force`, `git worktree prune`, delete the
     local branch. A leftover plain directory is removed too.

Idempotent: a clone with no worktree and no local branch is untouched
(action "noop"). If any backup step fails, nothing is removed.

The harness runs this for every clone at boot (harness.py
_retire_state_branch_in_clones); it can also be run by hand:

    python references/migrations/state_branch_teardown.py <clone-root> [...]
"""

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WORKTREE_DIR = ".squidsquad-state"
STATE_BRANCH = "squid-squad"
BACKUP_PARENT = Path(".squidsquad") / "backups"


def _git(root, *args, timeout=120):
    return subprocess.run(["git", *args], cwd=str(root), capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=timeout)


def _worktree_listed(root, wt):
    out = _git(root, "worktree", "list", "--porcelain").stdout
    target = str(wt.resolve()).replace("\\", "/").lower()
    for line in out.splitlines():
        if line.startswith("worktree "):
            path = line[len("worktree "):].strip().replace("\\", "/").lower()
            if path == target:
                return True
    return False


def _branch_exists(root):
    return _git(root, "rev-parse", "--verify", "--quiet",
                f"refs/heads/{STATE_BRANCH}").returncode == 0


def _copy_tree(src, dest):
    """Copy every file under src except the worktree's `.git` pointer file.
    Returns {relative path: size} of what was copied."""
    copied = {}
    for p in sorted(src.rglob("*")):
        rel = p.relative_to(src)
        if rel.parts[0] == ".git" or not p.is_file():
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, target)
        copied[rel.as_posix()] = p.stat().st_size
    return copied


def teardown(clone_root, now=None):
    """Back up, then retire the state branch + worktree in ``clone_root``."""
    root = Path(clone_root)
    wt = root / WORKTREE_DIR
    listed = _worktree_listed(root, wt) if (root / ".git").exists() else False
    has_dir, has_branch = wt.exists(), _branch_exists(root)
    if not (listed or has_dir or has_branch):
        return {"clone": str(root), "action": "noop"}

    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M%S")
    backup = root / BACKUP_PARENT / f"state-branch-{stamp}"
    backup.mkdir(parents=True, exist_ok=True)
    result = {"clone": str(root), "backup": str(backup), "bundle": None, "files": {}}

    if has_branch:
        bundle = backup / f"{STATE_BRANCH}.bundle"
        made = _git(root, "bundle", "create", str(bundle), STATE_BRANCH)
        ok = made.returncode == 0 and _git(root, "bundle", "verify", str(bundle)).returncode == 0
        if not ok:
            return {**result, "action": "error",
                    "error": f"bundle failed: {(made.stderr or '').strip()[:300]}"}
        result["bundle"] = str(bundle)
    if has_dir:
        copied = _copy_tree(wt, backup / "worktree")
        mismatched = [r for r, size in copied.items()
                      if (backup / "worktree" / r).stat().st_size != size]
        if mismatched:
            return {**result, "action": "error", "error": f"copy size mismatch: {mismatched}"}
        result["files"] = copied

    # Backup verified -- now remove.
    if listed:
        _git(root, "worktree", "remove", "--force", str(wt))
    if wt.exists():
        shutil.rmtree(wt, ignore_errors=True)
    _git(root, "worktree", "prune")
    if has_branch:
        _git(root, "branch", "-D", STATE_BRANCH)
    left = {"worktree_listed": _worktree_listed(root, wt), "dir": wt.exists(),
            "branch": _branch_exists(root)}
    if any(left.values()):
        return {**result, "action": "error", "error": f"still present after teardown: {left}"}
    return {**result, "action": "torn-down"}


def main(argv=None):
    roots = list(sys.argv[1:] if argv is None else argv)
    if not roots or roots[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if roots else 2
    results = [teardown(r) for r in roots]
    for r in results:
        if r.get("backup"):
            print(f"backup: {r['backup']}", file=sys.stderr)
    print(json.dumps(results, indent=2))
    return 1 if any(r["action"] == "error" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main())
