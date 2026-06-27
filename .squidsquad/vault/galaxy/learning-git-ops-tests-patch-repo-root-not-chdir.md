---
type: learning
tags: [verification, testing, git_ops]
created: 2026-06-27
author: qa
---

# Real-git tests of git_ops functions must patch `git_ops.REPO_ROOT`, not `os.chdir`

`git_ops._run` / `_run_list` invoke git with `cwd=str(REPO_ROOT)` — a module-level global pinned to the real repo root (`SCRIPT_DIR.parent.parent`). So **`os.chdir(temp_clone)` has no effect** on where `git_ops.pull` / `ensure_main_and_pull` / etc. actually run: they operate on the live repo regardless. A chdir-based "real-git" test of these functions silently runs against the actual working clone — flaky (reflects whatever state the real repo is in) and potentially **side-effecting** (could stash/pull/pop the live tree).

**The correct way** to point a `git_ops` function at a throwaway clone in a test:
```python
with patch.object(git_ops, "REPO_ROOT", str(temp_clone)):
    ok = git_ops.pull()
```
`_run` reads the module global at call time, so the patch redirects every git subprocess into the clone — deterministic and side-effect-free.

**Contrast:** functions that take a `clone_path` **parameter** (e.g. harness `_safe_pull_in_clone(clone_path)`, #13215) are genuinely path-aware and CAN be tested against a real temp clone directly — no patch needed.

**Observed**: 2026-06-27 verifying #13261 (git_ops.pull merge-abort). My first real-git draft used `os.chdir` and was non-deterministic — it was running `git_ops.pull()` against the real SquidSquad-qa repo (returned "already up to date" when clean, "pull failed" on a detached HEAD — neither the intended conflict scenario). Patching `REPO_ROOT` fixed it.

**How to apply**: before writing a real-git integration test for any `references/scripts` function, check whether it pins `cwd=REPO_ROOT` (or any fixed root). If it does, patch that global; if it takes an explicit path arg, pass the clone. Never assume `os.chdir` redirects a subprocess whose `cwd=` is set explicitly.

Related: [[learning-sibling-pr-additive-test-conflict-keep-both]], [[feedback_qa_verification_approach]].
