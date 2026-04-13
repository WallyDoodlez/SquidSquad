# FEAT-SKILL-375 QA Results — Branch-Per-Feature Workflow

**Verified by**: QA agent
**Date**: 2026-04-11
**Branch**: main (feature implemented on main)

---

## 1. git_ops.py New Commands

### TC-28: branch-create — PASS
- `branch_create(name)` function exists (line 131). Calls `git checkout -b <name>`. Prints confirmation.
- CLI dispatch at line 332 handles `branch-create` command.

### TC-29: branch-create fails gracefully if branch exists — PASS
- `_run_list` is called with `check=True` (default), so a `CalledProcessError` is raised if the branch already exists. Test `test_branch_create_failure` confirms this.

### TC-30: commit-code full workflow — PASS
- `commit_code(role, branch, message)` function exists (line 157). Workflow:
  1. Parses `git status --porcelain` to split code vs state files
  2. Switches to branch (creates if needed)
  3. Stages only non-`.squidsquad/` files
  4. Commits with role prefix and Co-Authored-By
  5. Pushes branch with `-u origin`
  6. Switches back to main
- CLI dispatch at line 347.

### TC-31: commit-state full workflow — PASS (with caveat, see TC-32)
- `commit_state(role, message)` function exists (line 232). Workflow:
  1. Parses `git status --porcelain` for `.squidsquad/` files only
  2. Stages only `.squidsquad/` paths
  3. Commits with role prefix
  4. Pushes main
- CLI dispatch at line 352.

### TC-32: commit-state fails if not on main — FAIL
- **Expected**: Error message "commit-state must be run on main", non-zero exit code, no commit.
- **Actual**: `commit_state()` silently switches to main if not on main (line 256-258: `if current != "main": _run_list(["git", "checkout", "main"])`). It does NOT error out — it auto-corrects.
- **Impact**: Medium. The test plan expects a hard guard; the implementation uses a soft guard (auto-switch). The behavior is arguably safer (self-healing), but does not match the specified contract.

### TC-33: branch-exists — FAIL (MISSING)
- **Expected**: `branch-exists` command that checks local and remote branches, prints "true"/"false".
- **Actual**: No `branch_exists` function or CLI handler in `git_ops.py`. The command does not exist.
- **Impact**: High. TC-24 and TC-33 cannot be executed. Recovery flow (TC-21) references this command.

### TC-34/TC-35: branch-delete — FAIL (MISSING)
- **Expected**: `branch-delete` command that removes a local branch, with guard against deleting current branch.
- **Actual**: No `branch_delete` function or CLI handler in `git_ops.py`. The command does not exist.
- **Impact**: Medium. Post-merge cleanup (TC-5 follow-up) and smoke tests reference this command.

### TC-36/TC-37: current-branch — FAIL (MISSING)
- **Expected**: `current-branch` command that prints the current branch name.
- **Actual**: No `current_branch` function or CLI handler in `git_ops.py`. The command does not exist.
- **Impact**: Medium. Recovery flows (TC-21, TC-22) and smoke tests reference this command.

### TC-25: commit-code with no code changes — PASS
- Line 184: checks `if not code_files` and prints "No code changes to commit (only .squidsquad/ changes)", returns False.

### TC-26: commit-state with no state changes — PASS
- Line 249: checks `if not state_files` and prints "No state changes to commit", returns False.

---

## 2. Dev Agent git-commit Sub-Skill

### Result: PASS
- File: `references/sub-skills/common/git-commit.md`
- Contains full branch workflow instructions:
  - Checks `config.py get branch-workflow` setting
  - If `yes`: uses `commit-code` for feature branch, `commit-state` for main, creates PR on pending-test
  - If `no`: falls back to `commit-push` (backward compatible)
  - Branch naming follows `squidsquad/[ROLE]/[NUMBER]` convention
  - Comments branch name on the issue on first commit

---

## 3. QA Verification Sub-Skill (Branch Checkout)

### Result: PASS
- File: `references/sub-skills/qa-specific/verification.md`
- Step 4 (Verify Fixed Issues, line 50-58): QA checks issue comments for `squidsquad/` branch name, runs `git_ops.py branch-switch` to checkout, verifies on branch, then switches back to main.
- Step 5 (Verify Pending Test Tasks, line 85-92): Same pattern — branch checkout before testing, switch back after.

---

## 4. PM Post-Merge Recompose

### Result: PASS
- File: `references/sub-skills/pm-specific/post-merge-recompose.md`
- Also present in PM CLAUDE.md as Step 6e.
- Checks `config.py get branch-workflow`, skips if `no`.
- Detects merged `squidsquad/` branches via `git log --merges`.
- Checks if merge touched `references/`, runs `compose.py deploy-all` if so.
- Comments on associated issue.

---

## 5. Config — Branch Workflow Field

### Result: PASS
- `config.md` contains `## Branch Workflow` section with `- **Enabled**: yes` (line 49-50).
- `config.py` supports `branch-workflow` key (maps to "Branch Workflow" > "Enabled").

---

## 6. Branch Naming Convention

### Result: PASS
- Convention: `squidsquad/<role>/<issue-number>` (e.g., `squidsquad/skill/195`)
- Documented in CONTEXT.md locked decisions.
- Used consistently in:
  - `references/sub-skills/common/git-commit.md`
  - `references/sub-skills/qa-specific/verification.md`
  - `references/sub-skills/pm-specific/post-merge-recompose.md`
  - Test plan (TC-1 through TC-27)

---

## 7. Tests

### Unit Tests: PARTIAL PASS
- File: `tests/test_git_ops.py` (268 lines)
- **Covered**: pull, add_all, commit, push, commit_push, has_changes, last_hash, branch_create, branch_switch, pr_create, _get_alias, _parse_args
- **NOT covered**: `commit_code`, `commit_state` — zero test cases for the two most critical new functions.
- **NOT covered**: `branch_exists`, `branch_delete`, `current_branch` — these don't exist yet.

### Test Run Results:
- 17 tests ran, 2 errors (pre-existing integration test failures in `test_status_flow.py` related to `gh issue close` — not #375-related).
- All git_ops unit tests pass.

---

## 8. Commit Split Mechanism

### Result: PASS
- `commit_code()` (line 157-229): Parses `git status --porcelain`, classifies files by `.squidsquad/` prefix. Stages only code files. Commits to feature branch.
- `commit_state()` (line 232-286): Parses `git status --porcelain`, stages only `.squidsquad/` files. Commits to main.
- Separation logic is correct: files are classified by path prefix, staged individually.

---

## Summary

| # | Deliverable | Result | Notes |
|---|-------------|--------|-------|
| 1 | git_ops.py new commands | **FAIL** | `branch-create`, `branch-switch`, `commit-code`, `commit-state` present. **Missing**: `branch-exists`, `branch-delete`, `current-branch`. `commit-state` main guard is soft (auto-switch) not hard (error). |
| 2 | Dev git-commit sub-skill | **PASS** | Full branch workflow with fallback to direct-to-main. |
| 3 | QA branch checkout | **PASS** | Both issue and task verification include branch checkout. |
| 4 | PM post-merge recompose | **PASS** | Step 6e with config gate, merge detection, compose deploy. |
| 5 | Config field | **PASS** | `Branch Workflow: yes` in config.md, supported in config.py. |
| 6 | Branch naming | **PASS** | `squidsquad/<role>/<issue>` used consistently. |
| 7 | Tests | **FAIL** | No unit tests for `commit_code` or `commit_state`. Missing commands have no tests. |
| 8 | Commit split | **PASS** | Code vs state separation works correctly via path prefix filtering. |

## Blocking Findings

1. **Missing commands**: `branch-exists`, `branch-delete`, `current-branch` are referenced in the test plan and CONTEXT.md but do not exist in `git_ops.py`. These are needed for agent recovery flows and post-merge cleanup.
2. **No tests for new functions**: `commit_code` and `commit_state` are complex multi-step functions with branch switching, selective staging, and error handling. They have zero unit test coverage.
3. **commit-state main guard**: Silently switches to main instead of erroring. Should either match the spec (error) or the spec should be updated to match the implementation.

## Verdict: FAIL — back to In Progress

Three missing commands, zero tests for the two most important new functions, and a behavioral mismatch on the main-only guard.
