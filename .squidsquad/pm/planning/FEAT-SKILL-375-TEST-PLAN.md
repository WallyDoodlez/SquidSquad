# FEAT-SKILL-375 Test Plan — Branch-Per-Feature Workflow

## Test Cases

---

### Branch Lifecycle

### TC-1: Dev agent creates feature branch on task pickup
- **Precondition**: Agent is on main, no branch `squidsquad/skill/375` exists
- **Steps**: Run `python references/scripts/git_ops.py branch-create squidsquad/skill/375`
- **Expected**: Branch created locally, agent switched to it, `git branch --show-current` returns `squidsquad/skill/375`
- **Verification**: `git branch --show-current` and `git branch --list squidsquad/skill/375`

### TC-2: Code changes committed to feature branch
- **Precondition**: On branch `squidsquad/skill/375`, a file in `references/` has been modified
- **Steps**: Run `python references/scripts/git_ops.py commit-code skill squidsquad/skill/375 "implement #375"`
- **Expected**: Only files outside `.squidsquad/` are staged and committed to the branch. `.squidsquad/` files remain unstaged.
- **Verification**: `git log -1 --name-only` shows only code paths. `git status` shows `.squidsquad/` files still dirty.

### TC-3: State changes committed to main
- **Precondition**: Agent is back on main after TC-2, `.squidsquad/` files are dirty
- **Steps**: Run `python references/scripts/git_ops.py commit-state skill "state update #375"`
- **Expected**: Only `.squidsquad/` paths are staged and committed to main. No code files touched.
- **Verification**: `git log -1 --name-only` shows only `.squidsquad/` paths. `git branch --show-current` returns `main`.

### TC-4: Dev marks pending-test on branch
- **Precondition**: Code committed to `squidsquad/skill/375`, state committed to main
- **Steps**: Agent transitions issue #375 to `pending-test` via tracker.py, records branch name in working-state.md
- **Expected**: Issue status updated, working-state.md on main references the branch name
- **Verification**: `python references/scripts/tracker.py get-state 375` shows `pending-test`. `cat .squidsquad/skill/working-state.md` contains branch name.

### TC-5: Branch merges to main after QA pass
- **Precondition**: QA has verified the branch (TC-11 through TC-14 passed), status is `pending-ship`
- **Steps**: `git checkout main && git merge squidsquad/skill/375`
- **Expected**: Code from branch lands on main. No conflicts with `.squidsquad/` files (they were never on the branch).
- **Verification**: `git log --oneline -5` shows merge commit. Code files from branch present on main. `.squidsquad/` state intact.

### TC-6: PM recomposes after merge that touched references/
- **Precondition**: Branch `squidsquad/skill/375` just merged, it touched files under `references/`
- **Steps**: PM detects merge via `git log`, checks diff for `references/` paths, runs `python references/scripts/compose.py deploy all`
- **Expected**: `.squidsquad/*/CLAUDE.md` regenerated from updated `references/` templates
- **Verification**: `.squidsquad/skill/CLAUDE.md` mtime updated. Content reflects merged template changes.

---

### Commit Split

### TC-7: Code and state split into separate commits without data loss
- **Precondition**: Agent has modified both `references/scripts/git_ops.py` and `.squidsquad/skill/working-state.md`
- **Steps**:
  1. `git_ops.py commit-code skill squidsquad/skill/375 "code changes"`
  2. `git_ops.py commit-state skill "state update"`
- **Expected**: Two separate commits — one on branch with code, one on main with state. No file lost between commits.
- **Verification**: On branch: `git log -1 --name-only` shows code files only. On main: `git log -1 --name-only` shows `.squidsquad/` only. `git status` clean on both.

### TC-8: commit-code stages only code paths, not .squidsquad/
- **Precondition**: Both code files and `.squidsquad/` files dirty on working tree
- **Steps**: Run `git_ops.py commit-code skill squidsquad/skill/375 "code only"`
- **Expected**: `git diff --cached --name-only` (after staging, before commit) contains zero `.squidsquad/` paths
- **Verification**: Inspect commit contents — no `.squidsquad/` files present

### TC-9: commit-state stages only .squidsquad/ paths, not code
- **Precondition**: On main, code files and `.squidsquad/` files both dirty
- **Steps**: Run `git_ops.py commit-state skill "state only"`
- **Expected**: `git diff --cached --name-only` contains only `.squidsquad/` paths. Code files remain unstaged.
- **Verification**: `git log -1 --name-only` shows only `.squidsquad/`. `git status` still shows code files as modified.

### TC-10: Dirty working tree handled correctly during branch switch
- **Precondition**: On branch `squidsquad/skill/375`, `.squidsquad/` files are dirty (not staged)
- **Steps**: `git_ops.py commit-code` commits code on branch, then switches to main
- **Expected**: Switch to main succeeds. `.squidsquad/` dirty files carry over (they exist on both branches). No stash needed for files that are identical across branches.
- **Verification**: `git branch --show-current` returns `main`. `git status` shows `.squidsquad/` files still dirty. No data loss.

---

### QA on Branches

### TC-11: QA checks out a feature branch
- **Precondition**: QA is on main, branch `squidsquad/skill/375` exists with code commits
- **Steps**: `git_ops.py branch-switch squidsquad/skill/375`
- **Expected**: QA is now on the feature branch, sees code changes from dev agent
- **Verification**: `git branch --show-current` returns `squidsquad/skill/375`. Code changes visible in working tree.

### TC-12: QA runs tests on the branch
- **Precondition**: QA is on `squidsquad/skill/375`
- **Steps**: Run configured test command (e.g., `python -m pytest tests/`)
- **Expected**: Tests execute against branch code. Results reflect branch state, not main.
- **Verification**: Test output references branch-specific code. No test imports stale main code.

### TC-13: QA switches back to main cleanly
- **Precondition**: QA is on `squidsquad/skill/375`, no uncommitted changes
- **Steps**: `git_ops.py branch-switch main`
- **Expected**: QA is back on main. Working tree matches main HEAD.
- **Verification**: `git branch --show-current` returns `main`. `git status` clean (no leftover branch artifacts).

### TC-14: No dirty state left on either branch after QA cycle
- **Precondition**: QA completed TC-11 through TC-13
- **Steps**: Check `git status` on main. Switch to branch, check `git status`.
- **Expected**: Both branches have clean working trees (no untracked, modified, or staged files from QA's activity)
- **Verification**: `git status --porcelain` is empty on both main and `squidsquad/skill/375`

---

### PM Recompose

### TC-15: PM detects merged branch that touched references/
- **Precondition**: Branch `squidsquad/skill/375` merged to main, branch modified `references/sub-skills/common/git-commit.md`
- **Steps**: PM runs `git log --oneline -5 --diff-filter=M -- references/` after pull
- **Expected**: Merge commit appears in output showing references/ changes
- **Verification**: PM's detection logic identifies the merge and triggers recompose

### TC-16: PM runs compose.py deploy after detecting references/ change
- **Precondition**: TC-15 detected a references/ change
- **Steps**: `python references/scripts/compose.py deploy all`
- **Expected**: All agent CLAUDE.md files regenerated. No errors from compose.py.
- **Verification**: Each `.squidsquad/*/CLAUDE.md` has updated content matching the merged templates

### TC-17: PM does NOT recompose when merged branch did not touch references/
- **Precondition**: Branch `squidsquad/skill/400` merged, only touched `tests/` files
- **Steps**: PM runs merge detection logic
- **Expected**: No recompose triggered. `.squidsquad/*/CLAUDE.md` files unchanged.
- **Verification**: CLAUDE.md mtimes unchanged. No compose.py invocation in cycle log.

### TC-18: Agents get updated CLAUDE.md after recompose
- **Precondition**: TC-16 completed, recomposed CLAUDE.md committed and pushed
- **Steps**: Other agents pull latest on their next cycle
- **Expected**: Agents read updated CLAUDE.md with new instructions from merged templates
- **Verification**: Agent behavior reflects updated instructions in subsequent cycles

---

### Edge Cases

### TC-19: Multiple dev agents on different branches simultaneously
- **Precondition**: skill on `squidsquad/skill/375`, designer on `squidsquad/designer/401`. Both active.
- **Steps**: Both agents run their commit-code / commit-state cycles concurrently
- **Expected**: No interference. Each agent's branch is independent. State commits to main may race but git push/pull resolves via rebase.
- **Verification**: Both branches have correct commits. Main has state from both agents. No lost commits.

### TC-20: Branch with merge conflicts
- **Precondition**: `squidsquad/skill/375` and main both modified `references/scripts/git_ops.py` in overlapping lines
- **Steps**: Attempt `git merge squidsquad/skill/375` on main
- **Expected**: Git reports merge conflict. Merge does not auto-complete.
- **Verification**: `git status` shows conflicted file. Agent or human resolves manually. After resolution, merge completes cleanly.

### TC-21: Agent crash mid-branch-switch (code committed, state not committed)
- **Precondition**: Agent committed code to branch, then crashed before switching to main and committing state
- **Steps**: Agent restarts, reads working-state.md (still on main from last cycle)
- **Expected**: Agent detects branch exists via `branch-exists`, checks `current-branch`, recovers by switching to main (if stuck on branch) and committing pending state changes
- **Verification**: After recovery: agent is on main, state is committed, branch has code. No data loss.

### TC-22: Agent crash mid-branch-switch (on branch, nothing committed)
- **Precondition**: Agent switched to branch but crashed before any commit
- **Steps**: Agent restarts, runs `current-branch`, discovers it is on a feature branch instead of main
- **Expected**: Agent switches back to main, resumes normal cycle. Uncommitted changes from the interrupted cycle are lost (acceptable — they were not committed).
- **Verification**: `git branch --show-current` returns `main`. Agent proceeds with fresh cycle.

### TC-23: Branch deleted before QA verifies
- **Precondition**: Branch `squidsquad/skill/375` pushed, dev marks pending-test, then branch is deleted (locally or remotely)
- **Steps**: QA attempts `branch-switch squidsquad/skill/375`
- **Expected**: `branch-switch` fails with clear error. QA reports failure, issue transitions back to `in-progress`.
- **Verification**: Error message indicates branch not found. Issue status returns to `in-progress` with discussion comment.

### TC-24: branch-exists returns correct result for local, remote, and non-existent branches
- **Precondition**: Branch `squidsquad/skill/375` exists locally and remotely. Branch `squidsquad/skill/999` does not exist.
- **Steps**:
  1. `git_ops.py branch-exists squidsquad/skill/375`
  2. `git_ops.py branch-exists squidsquad/skill/999`
- **Expected**: First returns true (prints "true"), second returns false (prints "false")
- **Verification**: Exit codes and stdout match expected values

### TC-25: commit-code with no code changes (state-only cycle)
- **Precondition**: Agent modified only `.squidsquad/` files, no code files changed
- **Steps**: `git_ops.py commit-code skill squidsquad/skill/375 "no-op"`
- **Expected**: commit-code detects nothing to stage, prints "Nothing to commit", does not create empty commit
- **Verification**: `git log -1` does not show a new commit. No error thrown.

### TC-26: commit-state with no state changes (code-only cycle)
- **Precondition**: Agent modified only code files, `.squidsquad/` is clean
- **Steps**: `git_ops.py commit-state skill "no-op"`
- **Expected**: commit-state detects nothing to stage, prints "Nothing to commit", does not create empty commit
- **Verification**: `git log -1` does not show a new commit. No error thrown.

### TC-27: Concurrent state commits to main (race condition)
- **Precondition**: Two agents both attempt `commit-state` + `push` to main within seconds of each other
- **Steps**: Agent A pushes, Agent B pushes (rejected), Agent B pulls --rebase, Agent B pushes again
- **Expected**: Both state commits land on main. No data loss. Push retry succeeds after rebase.
- **Verification**: `git log --oneline -5` on main shows both agents' state commits

---

### git_ops.py New Commands

### TC-28: branch-create creates and switches to new branch
- **Precondition**: On main, branch `squidsquad/skill/375` does not exist
- **Steps**: `python references/scripts/git_ops.py branch-create squidsquad/skill/375`
- **Expected**: Branch created, agent switched to it, prints "Created branch: squidsquad/skill/375"
- **Verification**: `git branch --show-current` returns `squidsquad/skill/375`

### TC-29: branch-create fails gracefully if branch already exists
- **Precondition**: Branch `squidsquad/skill/375` already exists
- **Steps**: `python references/scripts/git_ops.py branch-create squidsquad/skill/375`
- **Expected**: Error message printed to stderr, non-zero exit code. Does not corrupt existing branch.
- **Verification**: Existing branch unchanged. Agent can recover by calling `branch-switch` instead.

### TC-30: commit-code full workflow (switch, stage, commit, push, return)
- **Precondition**: On main, branch exists, code files modified, `.squidsquad/` files modified
- **Steps**: `python references/scripts/git_ops.py commit-code skill squidsquad/skill/375 "implement feature"`
- **Expected**:
  1. Switches to branch
  2. Stages only code paths (not `.squidsquad/`)
  3. Commits with role prefix
  4. Pushes branch to remote
  5. Switches back to main
- **Verification**: On branch: `git log -1 --name-only` shows code files. On main: `git branch --show-current` returns `main`. `.squidsquad/` files still dirty.

### TC-31: commit-state full workflow (stage .squidsquad/, commit, push)
- **Precondition**: On main, `.squidsquad/` files modified
- **Steps**: `python references/scripts/git_ops.py commit-state skill "state update #375"`
- **Expected**:
  1. Verifies on main (fails if not on main)
  2. Stages only `.squidsquad/` paths
  3. Commits with role prefix
  4. Pushes main
- **Verification**: `git log -1 --name-only` shows `.squidsquad/` only. Push successful.

### TC-32: commit-state fails if not on main
- **Precondition**: Agent is on branch `squidsquad/skill/375`
- **Steps**: `python references/scripts/git_ops.py commit-state skill "should fail"`
- **Expected**: Error: "commit-state must be run on main". Non-zero exit code. No commit made.
- **Verification**: `git log -1` unchanged. Agent must switch to main first.

### TC-33: branch-exists checks local and remote
- **Precondition**: Branch `squidsquad/skill/375` exists locally only. Branch `squidsquad/skill/400` exists remotely only. Branch `squidsquad/skill/999` exists nowhere.
- **Steps**:
  1. `git_ops.py branch-exists squidsquad/skill/375` -> true
  2. `git_ops.py branch-exists squidsquad/skill/400` -> true
  3. `git_ops.py branch-exists squidsquad/skill/999` -> false
- **Expected**: Returns true for local-only, true for remote-only, false for non-existent
- **Verification**: stdout prints "true" or "false" accordingly

### TC-34: branch-delete removes local branch
- **Precondition**: Branch `squidsquad/skill/375` exists locally, agent is on main
- **Steps**: `python references/scripts/git_ops.py branch-delete squidsquad/skill/375`
- **Expected**: Branch deleted locally. Prints confirmation.
- **Verification**: `git branch --list squidsquad/skill/375` returns empty

### TC-35: branch-delete fails if on the branch being deleted
- **Precondition**: Agent is on `squidsquad/skill/375`
- **Steps**: `python references/scripts/git_ops.py branch-delete squidsquad/skill/375`
- **Expected**: Error: cannot delete current branch. Non-zero exit code.
- **Verification**: Branch still exists. Agent must switch to main first.

### TC-36: current-branch returns current branch name
- **Precondition**: Agent is on main
- **Steps**: `python references/scripts/git_ops.py current-branch`
- **Expected**: Prints "main"
- **Verification**: stdout is exactly "main"

### TC-37: current-branch on feature branch
- **Precondition**: Agent is on `squidsquad/skill/375`
- **Steps**: `python references/scripts/git_ops.py current-branch`
- **Expected**: Prints "squidsquad/skill/375"
- **Verification**: stdout is exactly "squidsquad/skill/375"

---

## Smoke Tests

- [ ] `git_ops.py branch-create squidsquad/skill/test` creates branch and switches to it
- [ ] `git_ops.py current-branch` returns correct branch name
- [ ] `git_ops.py branch-exists squidsquad/skill/test` returns true
- [ ] `git_ops.py branch-switch main` returns to main
- [ ] `git_ops.py branch-delete squidsquad/skill/test` removes the branch
- [ ] `git_ops.py branch-exists squidsquad/skill/test` returns false after deletion
- [ ] `git_ops.py commit-code` with no code changes prints "Nothing to commit"
- [ ] `git_ops.py commit-state` with no state changes prints "Nothing to commit"
- [ ] `git_ops.py commit-state` on a feature branch errors out
- [ ] Full cycle: branch-create -> modify code + state -> commit-code -> commit-state -> branch-delete

## Regression Risks

- **Existing commit-push command**: Must continue working unchanged for PM/DM/QA agents who stay on main. Verify `commit-push` still does add-all + commit + push on main.
- **Pull behavior**: `git pull --rebase` must work on both main and feature branches without breaking stash/pop fallback.
- **PR Flow interaction**: If PR Flow is enabled alongside branching, PR creation must target the correct branch. Existing `pr-create` command should work from a feature branch.
- **compose.py deploy**: Must not break when run on main after a merge. Must handle the case where `references/` was not changed (no-op).
- **Agent boot/resume**: Agents reading working-state.md must handle the new branch name field without crashing if the field is absent (backward compatibility for pre-branch installs).
- **Config counter races**: Multiple agents incrementing `Shipped Since Last Bump` on main — same risk as today, branching does not make it worse but does not fix it either.
- **Windows path handling**: Branch names use forward slashes (`squidsquad/skill/375`). Verify git operations work correctly on Windows where path separators differ.
