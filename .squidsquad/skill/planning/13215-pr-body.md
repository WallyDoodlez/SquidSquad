## #13215 — deploy-pull survives a dirty agent clone (stash-around-merge)

(pm-filed; deploy-path-fragility cluster, sibling of the shipped #13212.)

### Root cause
`_run_deploy_sequence` pulled `origin/main` into a target agent's clone with a bare `git pull --no-rebase --no-edit` (via `_git_in_clone(clone_path, …)`). A **dirty** working tree — an uncommitted change to a file the incoming commit also touches — makes the merge **abort** (`local changes would be overwritten by merge`). The deploy's CLAUDE.md sync is then silently skipped and the clone drifts from shipped source. (`#12906` keeps agents on a working CLAUDE.md, so no outage — hence Low — but the drift is real.) `git_ops.pull` already solves this with a stash-around-merge (#13167/#13045), but it only operates on the harness's own cwd, so the deploy sequence (which runs against *another* clone) couldn't reuse it.

### Fix — Option A (blast-radius containment)
Add clone-aware helpers `_safe_pull_in_clone(clone_path)` + `_safe_stash_pop_in_clone(clone_path)` mirroring `git_ops.pull` / `_safe_stash_pop` over `_git_in_clone`, and call `_safe_pull_in_clone` at the deploy-pull site. Stashes-around-merge so the dirty case survives; a genuine merge conflict still returns `(False, …)` → §11 recovery. **Chosen over** parameterizing `git_ops.pull` with a cwd (Option B) to keep a regression **off the every-agent pull path** — a deploy-path bug stays contained to the deploy sequence.

### Review (Sonnet; DeepSeek degenerate all session → auto-fallback)
- **NO_BLOCKING_FINDINGS.** Verified faithful to git_ops: #13167 no-op-stash guard, #13045 marker-free conflict handling, genuine-conflict-still-fails.
- **MEDIUM (FIXED):** the genuine-conflict retry left the clone MERGING (MERGE_HEAD + markers) → `_safe_stash_pop_in_clone` would misread the merge's unmerged files as a stash-pop conflict, drop our stash, and the lingering MERGE_HEAD would loop the next deploy's `checkout main`. Added `git merge --abort` before the stash-restore (harmless no-op when no merge is in progress); test asserts the abort precedes the pop.
- **LOW (accepted):** replication drift risk vs git_ops — docstring-mitigated.
- **Follow-up noted on the issue:** the identical MERGING gap exists in `git_ops.pull` (every-agent path), pre-existing — a separate higher-blast-radius slice, not folded here.

### Verification
- +8 tests (clean / already-up-to-date / dirty→stash→pop / genuine-conflict→abort-then-fail / clean-tree-no-pop / stash-fail / pop-conflict→resolve-to-pulled / no-unmerged→no-drop).
- Full static gate: **4975 passed, 0 failures, 0 errors**.
- No CQ (deterministic). No manifest (no new files). Pairs with #13212 (shipped — reduces how often the tree is dirty in the first place).
