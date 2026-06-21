---
type: learning
tags: [verification, git-ops, smoke-test, hazard]
created: 2026-06-21
updated: 2026-06-21
owner: verifier
status: active
confidence: high
source: observation
links: [pattern-verify-liveness-lifecycle-with-independent-runtime-probe]
---

# git_ops._run pins cwd=REPO_ROOT — you cannot smoke-test git_ops helpers against a temp repo via chdir

When independently smoke-testing a `references/scripts/git_ops.py` helper (e.g. `_safe_stash_pop`, `pull`, `_safe_checkout`), **do NOT** `import git_ops`, `os.chdir(temp_repo)`, then call the helper. `git_ops._run` / `_run_list` hard-pin `cwd=str(REPO_ROOT)` (REPO_ROOT = `SCRIPT_DIR.parent.parent`), so they **ignore the process cwd** and execute git against the **live clone**, not your temp repo.

**Why it bites (the #13045 verify, 2026-06-21):** a smoke that drove `git_ops._safe_stash_pop()` after chdir ran `git stash pop` + `git stash drop` against the qa clone's **shared stash stack** (worktrees share `refs/stash` with the main repo), producing a false reading AND dropping a few real (ancient) stashes. Working tree stayed clean (the helper checks paths out to HEAD), but it mutated shared state unintentionally.

**Do instead:** replicate the helper's ALGORITHM with raw git commands (`subprocess.run(..., cwd=temp_repo)`) in the temp repo — that verifies the logic without touching the live repo. (Alternative: copy git_ops.py into the temp tree so its REPO_ROOT resolves there — heavier.) This is the same independence discipline as [[pattern-verify-liveness-lifecycle-with-independent-runtime-probe]], applied to git plumbing.

**Tell:** if a verify probe of a git_ops function reports an unexpected result (e.g. "stash not dropped") OR `git diff --diff-filter=U` returns a path that isn't in your temp repo (like `.squidsquad/config.md`), you're hitting the live repo — stop and re-do with raw git.
