# FEAT-PM-3296 Research: Task-Level Branch Boundaries

**Issue**: #3296 — Agents check out PR branch before verification/shipping — task-level branch boundaries
**Date**: 2026-04-26
**Researcher**: Claude Code (research agent)

---

## Summary

The request is to add a **task-level mechanical boundary** — `begin_task(#N)` / `end_task(#N)` hooks — that are separate from the existing cycle-level `cycle_pre.py` / `cycle_post.py` scripts. When branch workflow is enabled, agents (QA, DM) would automatically check out the task's feature branch at task start and return to main at task end, without relying on ad hoc `branch-switch` calls scattered in role instructions.

**Recommendation**: This is feasible and low-risk. The scaffolding to do this already exists in `git_ops.py`. The cleanest implementation is two new commands in `git_ops.py` — `task-begin` and `task-end` — that standardize and centralize what is currently done inconsistently across QA and DM sub-skills. The cycle-level scripts need minor additions to call these hooks when cycle-input identifies a single active task. A separate Python module (`task_boundary.py`) is not needed — extending `git_ops.py` is sufficient and keeps the surface area small.

---

## Current State: How Branches Work Today

### Branch Naming Convention

All feature branches follow: `squidsquad/<role>/<issue-number>`

Examples:
- `squidsquad/skill/3290` (skill agent working on issue #3290)
- `squidsquad/dev/3291`

This convention is documented in `references/sub-skills/common/git-commit.md`, `references/scripts/git_ops.py` (the `pr_merge` function parses `parts = branch_name.split("/")` expecting `[squidsquad, role, NUMBER]`), and implicitly in `cycle_pre.py`'s `_build_qa_input` which auto-derives `branch = f"squidsquad/skill/{num}"`.

### How Skill Creates Branches

Branch creation is handled in `git_ops.py`'s `commit_code()` function. When skill calls `commit-code <role> squidsquad/skill/N <msg>`:
1. If the branch doesn't exist locally, it is created: `git checkout -b <branch>`
2. Only non-state files are staged and committed to the feature branch
3. Branch is pushed: `git push -u origin <branch>`
4. Skill returns to main via `_safe_checkout("main")`

The skill agent triggers this via `cycle-output.json`'s `code_commit` field, which `cycle_post.py` then executes. Skill never stays on the feature branch between cycles — it commits to it, then snaps back to main.

### How cycle_pre.py Handles Branches Today

**For skill** (`_setup_skill_branch`): Reads `working-state.md` → extracts task number → derives branch name → checks out the branch if it exists. This is a cycle-level operation, not task-level — it runs once before the creative phase regardless of how many tasks a cycle touches.

**For QA** (`_build_qa_input`): Checks the **first item** in the verification queue and, if branch workflow is enabled, checks out that first item's branch. This is a crude approximation — it handles only one item and does it at cycle start rather than per-item.

**For DM**: No branch setup at all in `_build_dm_input`. DM is expected to be on main; it merges PRs via `git_ops.py pr-merge` but doesn't check out feature branches to inspect code.

### How QA Currently Finds and Verifies Code on Branches

In `references/sub-skills/qa-specific/verification.md`:
- Step 4 (verify fixed issues): QA reads issue comments, looks for a branch name comment (`squidsquad/` in the text), and manually calls `git_ops.py branch-switch` before testing. Returns to main when done.
- Step 5 (verify pending test tasks): Same pattern — manual branch-switch per task, manual return to main.

This is **agent-driven** (in the creative phase) rather than **script-driven** (mechanical pre/post). It relies on the agent remembering to switch branches and switch back, which is fragile.

The cycle_pre.py `_build_qa_input` function does attempt to pre-switch to the first item's branch, but this is disconnected from the per-item logic in the creative phase and creates a dual-path problem.

### How DM Currently Handles Delivery (Branch Perspective)

DM's `delivery-packaging.md` Step 2c includes a "PR merge gate": if branch workflow is on, DM checks for an open PR and calls `git_ops.py pr-merge`. DM does **not** check out the feature branch — it works entirely on main, and merges the PR programmatically.

This means DM never needs to be on the feature branch to do its work (README updates, CHANGELOG entries are all on main). DM's branch boundary requirement is minimal: just ensure the PR is merged before shipping.

---

## Impact Analysis

### Files That Would Be Touched

| File | Change | Scope |
|---|---|---|
| `references/scripts/git_ops.py` | Add `task-begin` and `task-end` commands | ~60 lines new |
| `references/scripts/cycle_pre.py` | Remove QA's first-item branch checkout hack; QA/DM creative phase instructions reference `task-begin` instead | Minor cleanup |
| `references/sub-skills/qa-specific/verification.md` | Replace ad hoc branch-switch calls with `task-begin`/`task-end` calls | 4-6 lines changed |
| `references/sub-skills/dm-specific/delivery-packaging.md` | Add optional `task-begin` at item pickup if DM ever needs branch code | Minimal / possibly none |
| `references/agent-instructions.md` | Same changes as sub-skills (compiled template) | Mirror of above |
| `tests/` | New test file covering `task-begin` / `task-end` | Required by QA |

### Behavior Changes by Role

**Skill**: No change. Skill's branch management (via `commit_code`) is already mechanical and correct. The existing `_setup_skill_branch` in `cycle_pre.py` handles the cycle-start checkout. Skill doesn't need `task-begin`/`task-end` because it always snaps back to main after `commit_code`.

**QA**: Primary beneficiary. Instead of the agent relying on its own instructions to call `branch-switch`, `task-begin` is called once per item at item pickup (scripted, consistent), and `task-end` is called at item conclusion. Removes the `_build_qa_input` first-item checkout hack from `cycle_pre.py`.

**DM**: Minimal change. DM works on main and merges PRs via `pr-merge`. No branch checkout needed for DM's core work. If DM ever needs to inspect code pre-ship (e.g., read a file from the feature branch), `task-begin` would be available. For now, this is a no-op for DM.

**PM**: No change. PM doesn't check out feature branches.

---

## Proposed Design

### New `git_ops.py` Commands

```python
def task_begin(role, number):
    """Checkout the task's feature branch if branch-workflow is enabled.

    Derives branch name as squidsquad/<role>/<number>.
    If branch doesn't exist (local or remote), stays on main and prints a warning.
    Returns the branch name that was checked out, or 'main' if no branch.
    """

def task_end(role, number):
    """Return to main after task work.

    Stashes any uncommitted changes if needed, switches to main.
    Prints a warning if uncommitted code changes remain on the feature branch.
    """
```

CLI surface:
```
python references/scripts/git_ops.py task-begin <role> <number>
python references/scripts/git_ops.py task-end <role> <number>
```

`task-begin` should:
1. Read `branch-workflow` config flag (if `no`, return immediately — no-op)
2. Derive branch: `squidsquad/<role>/<number>`
3. Check if branch exists locally: `git rev-parse --verify <branch>`
4. If not, check remote: `git rev-parse --verify origin/<branch>`
5. If remote exists: `git checkout -b <branch> origin/<branch>`
6. If local exists: `git checkout <branch>`
7. If neither exists: print warning, stay on main (not an error — branch may not have been created yet)

`task-end` should:
1. Read `branch-workflow` config flag (if `no`, return immediately)
2. Check for uncommitted changes: `git status --porcelain`
3. If changes exist, warn (agent should have committed via `commit_code` before calling `task-end`)
4. Use `_safe_checkout("main")` (already exists in git_ops.py) to return to main

### cycle_pre.py Cleanup

Remove the QA first-item branch checkout block from `_build_qa_input` (lines 631-648). The `branch` field on each item in `verification_queue` should remain — it's useful context for the agent to know which branch to pass to `task-begin`. The actual checkout moves to the creative phase, per-item.

The `_setup_skill_branch` function in `cycle_pre.py` remains unchanged — it's the correct cycle-level setup for skill (resumes from working-state, not per-task).

### verification.md Changes

Replace current per-item branch checkout pattern:
```bash
# BEFORE (agent does this manually, twice per step):
python references/scripts/git_ops.py branch-switch squidsquad/[role]/[number]
# ... do work ...
python references/scripts/git_ops.py branch-switch main
```

With:
```bash
# AFTER (standardized task boundary):
python references/scripts/git_ops.py task-begin [role] [number]
# ... do work ...
python references/scripts/git_ops.py task-end [role] [number]
```

The semantics are identical but `task-begin` adds: config flag check (no-op if branch workflow off), remote branch fetch if needed, and defensive warning if branch doesn't exist rather than a hard error.

---

## Edge Cases

### Branch Doesn't Exist

**When**: Skill hasn't pushed the branch yet (e.g., QA picks up the item in the same cycle skill submitted it, before skill's `cycle_post` ran the `commit_code`).

**Current behavior**: `branch-switch` fails with a non-zero exit code. Agent may not catch this and proceeds on wrong branch.

**Proposed behavior**: `task-begin` checks both local and remote. If neither exists, prints `WARNING: branch squidsquad/<role>/<N> not found — staying on main` and exits with code 0 (not a fatal error). The agent verifies on main, which is equivalent to the current fallback behavior.

### Agent Is Mid-Task When Cycle Ends

**When**: A cycle's context pressure causes early exit mid-task. The agent writes working-state with status `in-progress` and the task number.

**Current behavior**: On the next cycle, `_setup_skill_branch` reads working-state and restores the branch for skill. QA has no equivalent — it reads working-state to resume work, but the branch checkout is done manually in the creative phase.

**Proposed behavior**: `task-begin` at the start of each resumed item handles the checkout. Since QA's creative phase calls `task-begin` at item pickup (not cycle_pre), resuming from working-state works correctly: the agent reads working-state, identifies the in-progress task number, calls `task-begin <role> <number>`, and proceeds.

This is actually **better** than the current `_build_qa_input` approach which pre-checks out only the first queue item — it's task-aware rather than queue-position-aware.

### Two Agents Need the Same Branch (Concurrent Access)

**When**: Skill is still developing on `squidsquad/skill/N` while QA is trying to verify it. Both are in separate clones (clone isolation architecture).

**Impact**: No conflict. Each agent is in its own clone directory. Branch checkout in one clone has no effect on the other. QA checks out the branch in its clone; skill is on the same branch in its clone. Both can coexist because they're separate filesystem paths.

**Only risk**: If skill force-pushes after QA has fetched. QA's local branch would be stale. `task-begin` uses `git checkout -b <branch> origin/<branch>` which fetches from origin at checkout time — so as long as QA fetches before starting work (which `cycle_pre.py`'s `pull` handles at cycle start), this is mitigated.

### Multiple Tasks in One Cycle (The Core Problem)

**When**: A cycle has 3 items in the verification queue on 3 different branches. The current `_build_qa_input` pre-checks out only the first item's branch.

**Current behavior**: Agent switches to item 2's branch manually mid-cycle, but if it forgot to switch back from item 1, it may run item 2's tests on item 1's branch.

**Proposed behavior**: Per-item `task-begin` / `task-end` calls in the creative phase loop ensure correct branch per item. `task-end` always returns to main before the next `task-begin`.

### Branch Workflow Disabled

`task-begin` and `task-end` are no-ops when `branch-workflow` is `no`. Zero behavioral change for non-branch-workflow setups. The config flag check is the first thing both functions do.

### QA Rebase Scenario

When QA finds a merge conflict and needs to rebase the feature branch (already in `verification.md`), `task-begin` would have put QA on the right branch already. The rebase workflow in the instructions remains unchanged — QA still manually runs `git rebase` commands. `task-end` cleans up afterward.

### DM Delivery on a Branch That Isn't Merged Yet

**When**: DM picks up a `pending-ship` item but the PR hasn't been merged yet (possible if QA transitioned to pending-ship without merging, e.g., via PR Flow `yes` with human review pending).

**Current behavior**: DM's "PR merge gate" in `delivery-packaging.md` checks for an open draft PR and skips if found. Non-draft open PRs are merged via `pr-merge`. This works on main; DM doesn't inspect the feature branch.

**Proposed behavior**: No change for DM. DM calls `pr-merge` which pulls code into main. DM then works on main for delivery artifacts. `task-begin` is not needed by DM for its current workflow.

---

## Integration Risks with Existing Cycle Runner

### Stash Conflicts

`_safe_checkout()` in `git_ops.py` already handles the stash-and-retry pattern when files modified by linters/hooks block a bare checkout. `task-begin` and `task-end` should use `_safe_checkout` rather than a bare `git checkout` call. This is a known-good pattern.

### Pull Timing

`cycle_pre.py` runs `git pull --rebase` before the creative phase. By the time `task-begin` runs (in the creative phase), the repo is already synced. Remote branches fetched during pull are available without an additional fetch. The `git rev-parse --verify origin/<branch>` check in `task-begin` works against the already-fetched remote refs.

### State File Commits Always on Main

The `commit_state` function explicitly errors if not on main. Since QA's state changes (working-state.md, qa-log.md, cycle-output.json) go through `cycle_post.py` which calls `commit_push`, and since `task-end` returns to main before the cycle ends, there is no conflict. The sequence is:

1. `cycle_pre` — on main
2. Creative phase: `task-begin` (switch to branch), do work, `task-end` (switch to main)
3. `cycle_post` — on main, commits state

### cycle_post.py's QA Branch Return

`_do_commit_push` for QA already has a "switch back to main before committing" guard (lines 231-238 in `cycle_post.py`). This guard was the previous mitigation for agents forgetting to return to main. With `task-end` enforcing the return, this guard becomes redundant but harmless. It should be kept as a safety net.

### PR Flow Interaction

When PR Flow is `yes`, QA converts draft PRs to ready via `gh pr ready`. This does not require being on the feature branch — it's a GitHub API call. `task-begin`/`task-end` don't interfere.

---

## Side Effects and Risks

### Low Risk

- **Agent instructions grow slightly**: Each item pickup in `verification.md` gains two lines (`task-begin`, `task-end`). Net instruction size impact is negligible.
- **`task-begin` is a no-op when no branch**: Defensive design means no regressions for projects with branch workflow disabled or where branches haven't been created yet.
- **DM unaffected**: DM's delivery workflow is entirely on main; adding `task-begin`/`task-end` to DM is optional and not needed for the current feature set.

### Medium Risk

- **`_build_qa_input` cleanup**: Removing the first-item branch checkout from `cycle_pre.py` is a behavior change. If QA's creative phase instructions are not simultaneously updated to call `task-begin`, QA will no longer check out any branch. The two changes (cycle_pre cleanup + verification.md update) must ship together.
- **Working-state resume path**: If an agent resumes from working-state and the resumed task number is in working-state.md, it must call `task-begin` with that number. The verification.md instructions must cover this resume path explicitly, not just the fresh-pickup path.

### Low-Impact Risk

- **Branch not pushed by skill yet**: Edge case where QA picks up an item the same cycle skill submitted. `task-begin` gracefully stays on main. This was always the behavior but now it's explicit and logged.

---

## Upgrade and Migration Impact

- **New installs**: Pick up the new `git_ops.py` commands automatically. `task-begin`/`task-end` are no-ops when `branch-workflow: no`, so no behavior change for setups without branch workflow.
- **Existing installs with branch-workflow: yes**: Will gain correct per-task branch switching in QA. This is a net improvement — previous behavior was inconsistent (relied on QA creative instructions and the cycle_pre first-item checkout hack).
- **Existing installs with branch-workflow: no**: Zero behavior change.
- **CLAUDE.md / sub-skill recompose**: After shipping, PM must trigger a recompose to regenerate any live `CLAUDE.md` files from the updated sub-skills. The compose.py script handles this.
- **Comprehension tests required**: Per team standards, any change to agent instructions requires comprehension test specs in the TEST-PLAN.md. The spec should test that QA agents correctly identify where to call `task-begin`/`task-end` and how to handle the "branch not found" case.

---

## Open Questions for Human Discussion

1. **Should DM call `task-begin` for delivery?** DM currently doesn't need to be on the feature branch — it reads task descriptions from GitHub and writes delivery artifacts to main. If DM ever needs to inspect code on the branch (e.g., read a file, understand implementation), `task-begin` would be the right hook. Is this in scope for #3296?

2. **Task-begin for skill too?** Skill's branch management currently works at the cycle level (`_setup_skill_branch` in `cycle_pre`). Should skill also move to per-task `task-begin`/`task-end` for symmetry? The current approach works correctly for skill (one active task per cycle), but if multi-task cycles become a future requirement, per-task hooks would be needed.

3. **Should `task-begin` be called from `cycle_pre` or the creative phase?** The request calls for "task-level, not cycle-level." For QA this means the creative phase (since QA loops over multiple items). For skill the cycle_pre approach already works. The recommendation is: creative phase for QA (per-item), cycle_pre for skill (single active task). This asymmetry is intentional and correct given each role's usage pattern.

4. **Should `task-begin` fail hard when a branch isn't found, or warn and stay on main?** The recommendation is warn-and-continue, since a missing branch is a normal transient state (skill may not have pushed yet). If the human prefers a hard fail to surface the problem explicitly, `task-begin` can exit non-zero and the agent can decide whether to skip the item.

5. **Should the `_build_qa_input` first-item checkout be removed immediately or kept as a belt-and-suspenders?** Recommendation: remove it as part of this feature. It only applies to the first item in the queue, it conflates cycle-level and task-level concerns, and keeping it creates a dual-path that is harder to reason about. The creative phase `task-begin` is the canonical path.

6. **DM's `cycle_post` also has no branch return guard (unlike QA's)**. Since DM currently stays on main, this is fine. Should a guard be added to DM's `_do_commit_push` as defensive code, symmetrical to QA's? Low priority but worth noting.

---

## Files to Create / Modify (Implementation Checklist)

For the implementing skill agent:

- `references/scripts/git_ops.py` — add `task_begin(role, number)`, `task_end(role, number)`, wire into `main()` as `task-begin` and `task-end` CLI commands
- `references/scripts/cycle_pre.py` — remove the first-item branch checkout block from `_build_qa_input` (lines 631-648); leave `branch` field in queue items intact
- `references/sub-skills/common/git-commit.md` — no change needed (skill-specific, already correct)
- `references/sub-skills/qa-specific/verification.md` — replace ad hoc `branch-switch` calls with `task-begin`/`task-end` in Steps 4 and 5; add note on resume-from-working-state path
- `references/agent-instructions.md` — mirror the `verification.md` changes (this is the compiled output)
- `tests/test_feat_3296_task_boundary.py` — unit tests for `task-begin`/`task-end` behavior: branch exists, branch missing, branch-workflow off, task-end returns to main
