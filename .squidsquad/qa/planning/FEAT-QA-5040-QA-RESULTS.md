# FEAT-QA-5040 QA Results — Unified Branch Model

**Tested by**: QA agent (claude-sonnet-4-6)
**Date**: 2026-05-02 19:30
**Branch tested**: `main` (commit `255a6ea6`, includes merge `4843c3b4` — #5040)
**Test plan**: `.squidsquad/pm/planning/FEAT-PM-5040-TEST-PLAN.md`

---

## Summary Table

| TC    | Title                                                         | Result       |
|-------|---------------------------------------------------------------|--------------|
| TC-1  | Config field present — factory reads correct pattern         | PASS         |
| TC-2  | Config field absent — factory falls back to default          | PARTIAL FAIL |
| TC-3  | `get_branch_name` factory — task pattern                     | PASS         |
| TC-4  | `get_branch_name` factory — legacy pattern                   | PASS         |
| TC-5  | `task-begin` creates branch, prints to stdout                | PASS         |
| TC-6  | Agent captures `task-begin` output for `commit-code`         | PARTIAL PASS |
| TC-7  | `task-begin` idempotent — second agent checks out existing   | PASS         |
| TC-8  | All construction sites use factory — no hardcoded strings    | PASS         |
| TC-9  | `cycle_pre.py` QA input uses factory for branch field        | PASS         |
| TC-10 | Parsing sites use `parts[-1]` — old-pattern branches parse   | PASS         |
| TC-11 | Parsing sites use `parts[-1]` — new-pattern branches parse   | PASS         |
| TC-12 | PR search wildcard matches new branch pattern                | PASS         |
| TC-13 | PR search wildcard matches old-pattern branches              | PASS         |
| TC-14 | `commit-code` uses explicit branch argument                  | PASS         |
| TC-15 | `cycle_post.py` PR creation uses `code_commit.branch`        | PASS         |
| TC-16 | Status bar shows current branch — PM role                    | FAIL         |
| TC-17 | Status bar shows current branch — QA and dev roles           | FAIL         |
| TC-18 | PM creates branch; dev continues on same branch              | PASS         |
| TC-19 | QA verifies on same shared branch                            | PASS         |
| TC-20 | Single PR merges unified branch — cleanup correct            | PASS         |
| TC-21 | Multi-agent same branch — no commit conflicts                | PASS         |
| TC-22 | `task-end` returns to main                                   | PASS         |
| TC-23 | Agent instructions have no hardcoded role-encoded branches   | PARTIAL FAIL |
| TC-24 | L4 project override sets `squidsquad/task/{number}`          | PASS         |
| TC-25 | `tracker.py` `_check_unmerged_branch` wildcard matches new   | PASS         |
| TC-26 | PR conflict rebase uses config-driven pattern                | PASS         |
| TC-27 | All 5 test files pass                                        | PASS         |

**Totals**: 22 PASS / 2 FAIL / 3 PARTIAL (TC-2 partial fail, TC-6 partial pass, TC-23 partial fail)

**Overall Verdict**: PARTIAL FAIL — core feature is correctly implemented; three gaps remain.

---

## Gap Summary

| Gap | Severity | TC | Description |
|-----|----------|----|-------------|
| `config.py` no fallback for absent `branch-pattern` | Low | TC-2 | CLI exits 1 when field absent; factory-level fallback works |
| Status bar missing branch display | Medium | TC-16, TC-17 | Agent instructions don't include branch name in `current-state` |
| `references/sub-skills/roles/qa/git-commit.md` hardcoded | Low | TC-23 | `squidsquad/skill/[NUMBER]` — stale, not deployed to QA CLAUDE.md |
| `references/sub-skills/roles/pm/pipeline-sentinel.md` example | Low | TC-23 | `squidsquad/skill/475` — documentation example using old pattern |

---

## Detailed Results

---

### TC-1: Config field present — factory reads correct pattern

- **Result**: PASS
- **Notes**: `python references/scripts/config.py get branch-pattern` returns `squidsquad/task/{number}` with exit 0.
- **Evidence**:
  ```
  $ python references/scripts/config.py get branch-pattern
  squidsquad/task/{number}
  EXIT: 0
  ```
  `references/scripts/config.py` line 87: `"branch-pattern": ("Git Branches", "Branch Pattern")`
  `.squidsquad/config.md` line 43: `- **Branch Pattern**: squidsquad/task/{number}`

---

### TC-2: Config field absent — factory falls back to default

- **Result**: PARTIAL FAIL
- **Notes**: The test plan expects `config.py get branch-pattern` to exit 0 with the default value when the field is absent. In practice, `config.py` exits 1 with an error. The factory functions in `git_ops.py` and `cycle_pre.py` both fall back gracefully to `squidsquad/{role}/{number}` — so the factory-level fallback works correctly, but the CLI does not provide a graceful fallback.
- **Evidence**:
  ```
  # With Branch Pattern removed from config.md:
  $ python references/scripts/config.py get branch-pattern
  EXIT: 1   (expected: 0)
  stderr: ERROR: Field 'branch-pattern' not found in config.md

  # git_ops factory fallback (correct):
  git_ops.get_branch_name('skill', 100) -> 'squidsquad/skill/100'  PASS

  # cycle_pre factory fallback (correct):
  cycle_pre._get_branch_name('skill', 100) -> 'squidsquad/skill/100'  PASS
  ```
  `git_ops.py` lines 524–527: catches exception, falls back to `squidsquad/{role}/{number}`.
  `cycle_pre.py` lines 121–123: same fallback pattern.
  `config.py` lines 150–152: exits 1 on missing field — no fallback in CLI.

---

### TC-3: `get_branch_name` factory — task pattern

- **Result**: PASS
- **Notes**: With `branch-pattern: squidsquad/task/{number}` in config, `get_branch_name("skill", 100)` returns `squidsquad/task/100`.
- **Evidence**:
  ```python
  from git_ops import get_branch_name
  get_branch_name('skill', 100) -> 'squidsquad/task/100'
  ```
  `git_ops.py` lines 514–528: reads pattern from config, substitutes `{role}` and `{number}`.
  Unit test `tests/test_git_ops.py::TestTaskBegin::test_uses_configured_branch_pattern` PASSED.

---

### TC-4: `get_branch_name` factory — legacy pattern

- **Result**: PASS
- **Notes**: With `branch-pattern: squidsquad/{role}/{number}`, `get_branch_name("skill", 100)` returns `squidsquad/skill/100`.
- **Evidence**:
  ```python
  # Mock config returning legacy pattern:
  get_branch_name('skill', 100) -> 'squidsquad/skill/100'  PASS
  ```
  `git_ops.py` line 528: `pattern.format(role=role, number=number)` — both placeholders substituted.

---

### TC-5: `task-begin` creates branch, prints to stdout

- **Result**: PASS
- **Notes**: Used number 99999 per instructions. `task-begin` created `squidsquad/task/99999`, checked it out, printed name to stdout. Branch deleted after test.
- **Evidence**:
  ```
  $ python references/scripts/git_ops.py task-begin skill 99999
  squidsquad/task/99999    <- stdout

  $ git branch --show-current
  squidsquad/task/99999    <- confirmed checkout

  # Cleanup:
  $ git checkout main && git branch -D squidsquad/task/99999
  Deleted branch squidsquad/task/99999
  ```

---

### TC-6: Agent captures `task-begin` output for `commit-code`

- **Result**: PARTIAL PASS
- **Notes**: `.squidsquad/skill/CLAUDE.md` line 721 says "use the branch name from task-begin output" and uses `[BRANCH]` placeholder. `cycle_post.py` reads `code_commit.branch` from `cycle-output.json`. The intent is correct; however, instructions do not show an explicit shell capture pattern (`BRANCH=$(...)`) — the `[BRANCH]` placeholder relies on the agent knowing to substitute the stdout value. This is a documentation gap, not a code defect.
- **Evidence**:
  - `.squidsquad/skill/CLAUDE.md` line 721: `"use the branch name from task-begin output"` — correct intent.
  - `.squidsquad/skill/CLAUDE.md` line 723: `commit-code skill [BRANCH]` — uses captured name via placeholder.
  - `cycle_post.py` lines 272–273: reads `code_commit.get("branch", "")`.
  - No `BRANCH=$(python ... task-begin ...)` shell capture pattern shown.

---

### TC-7: `task-begin` idempotent — second agent checks out existing branch

- **Result**: PASS
- **Notes**: Two consecutive calls with the same number (`skill 99999`, then `qa 99999`) — second call found the local branch and checked it out without error. Both printed `squidsquad/task/99999`.
- **Evidence**:
  ```
  $ python references/scripts/git_ops.py task-begin skill 99999
  squidsquad/task/99999
  $ python references/scripts/git_ops.py task-begin qa 99999
  squidsquad/task/99999   <- same branch, no error
  $ git branch --show-current
  squidsquad/task/99999
  ```
  `git_ops.py` lines 552–558: local branch check succeeds on second call → `_safe_checkout` → `print(branch)`.

---

### TC-8: All construction sites use factory — no hardcoded strings

- **Result**: PASS
- **Notes**: All branch construction goes through factory functions. The only `squidsquad/{role}/{number}` literals are the fallback defaults inside the factory functions themselves (correct behavior). No raw f-string construction sites outside factories.
- **Evidence**:
  ```
  grep -n "squidsquad.*{role}" references/scripts/git_ops.py references/scripts/cycle_pre.py
  -> git_ops.py:527: (inside get_branch_name fallback)
  -> cycle_pre.py:123: (inside _get_branch_name fallback)

  All construction calls:
  -> git_ops.py:548: branch = get_branch_name(role, number)
  -> cycle_pre.py:617: branch = _get_branch_name(query_role, num)
  -> cycle_pre.py:640: branch = _get_branch_name(query_role, num)
  ```

---

### TC-9: `cycle_pre.py` QA input uses factory for branch field

- **Result**: PASS
- **Notes**: `cycle_pre._get_branch_name('qa', 300)` returns `squidsquad/task/300` (not `squidsquad/qa/300`) with current config.
- **Evidence**:
  ```python
  from cycle_pre import _get_branch_name
  _get_branch_name('qa', 300) -> 'squidsquad/task/300'  PASS
  _get_branch_name('skill', 300) -> 'squidsquad/task/300'  PASS
  ```
  `cycle_pre.py` lines 119–124: reads config `branch-pattern`, falls back to `squidsquad/{role}/{number}`.

---

### TC-10: Parsing sites use `parts[-1]` — old-pattern branches

- **Result**: PASS
- **Notes**: All 5 parsing sites in `tracker.py` use `parts[-1]` for issue number extraction. For `squidsquad/skill/100`, `parts[-1]` = `"100"` — correct.
- **Evidence**:
  - `tracker.py` lines 681, 712, 731, 751, 775: all use `parts[-1] == str(number)`.
  - No `parts[2]` usage found in `tracker.py`.
  - `'squidsquad/skill/100'.split('/')[-1]` = `'100'` ✓

---

### TC-11: Parsing sites use `parts[-1]` — new-pattern branches

- **Result**: PASS
- **Notes**: For `squidsquad/task/100`, `parts[-1]` = `"100"` — identical to old pattern. Both 3-segment patterns resolve correctly.
- **Evidence**:
  ```python
  'squidsquad/skill/100'.split('/')[-1] == '100'  # True
  'squidsquad/task/100'.split('/')[-1] == '100'   # True
  ```
  No `parts[2]` usage in `tracker.py` — fully migrated to `parts[-1]`.

---

### TC-12: PR search wildcard matches new branch pattern

- **Result**: PASS
- **Notes**: `_check_unmerged_branch()` uses `*squidsquad/*/{number}` glob — matches `squidsquad/task/400`. `_check_unmerged_pr()` uses `--search "squidsquad/ {number}"` which matches any `squidsquad/` branch.
- **Evidence**:
  - `tracker.py` line 668: `["git", "branch", "-a", "--list", f"*squidsquad/*/{number}"]` — wildcard.
  - `tracker.py` line 731: `parts[-1] == str(number)` — validates last segment regardless of middle.
  - Wildcard `*squidsquad/*/{number}` matches both `squidsquad/task/400` and `squidsquad/skill/400`.

---

### TC-13: PR search wildcard matches old-pattern branches

- **Result**: PASS
- **Notes**: Same wildcard logic as TC-12. During cutover, old-pattern PRs are still discovered.
- **Evidence**: Same as TC-12 — `*squidsquad/*/{number}` glob matches `squidsquad/skill/400`.

---

### TC-14: `commit-code` uses explicit branch argument

- **Result**: PASS
- **Notes**: `commit_code(role, branch, message)` accepts branch as positional argument. The caller provides branch name from `task-begin` output; `commit_code` does not construct branch name internally.
- **Evidence**:
  - `git_ops.py` line 375: `def commit_code(role, branch, message):`
  - `git_ops.py` line 12: CLI: `commit-code <role> <branch> <msg>` — branch is explicit argument.
  - `cycle_post.py` line 277: passes `branch` from `code_commit.branch` JSON field.

---

### TC-15: `cycle_post.py` PR creation uses `code_commit.branch`

- **Result**: PASS
- **Notes**: `cycle_post.py` reads `branch = code_commit.get("branch", "")` from `cycle-output.json` and passes it to `commit-code`. Agents populate this from `task-begin` stdout.
- **Evidence**:
  - `cycle_post.py` lines 271–277: reads `code_commit.get("branch", "")`.
  - `cycle_post.py` line 277: `_run_script("git_ops.py", "commit-code", role, branch, code_msg)`.

---

### TC-16: Status bar shows current branch — PM role

- **Result**: FAIL
- **Notes**: The `#5040` commit did NOT add branch name display to the PM status bar. The `current-state` file format is `phase|description` with issue number but NOT the branch name. No PM instruction directs writing the branch name to `current-state`. The TC verification step (`cat .squidsquad/pm/current-state contains squidsquad/task/600`) would fail — no live PM agent is running and the format doesn't include branch.
- **Evidence**:
  - `.squidsquad/pm/CLAUDE.md` status bar examples: `pulling|pull-latest — Syncing...`, `verifying|verification — Verifying #29...` — no branch in format.
  - `git show 4843c3b4 -- .squidsquad/pm/CLAUDE.md` — no changes to status bar format.
  - `cycle.py status_bar()` writes `{phase}|{description}` — no branch field.
  - `.squidsquad/pm/current-state` file: does not exist (PM not active).

---

### TC-17: Status bar shows current branch — QA and dev roles

- **Result**: FAIL
- **Notes**: Same root cause as TC-16. No agent CLAUDE.md includes branch name in status bar format. Live `.squidsquad/qa/current-state` confirms format excludes branch name.
- **Evidence**:
  - `.squidsquad/qa/current-state`: `verifying|verification — Verifying #5040...` — no branch.
  - `.squidsquad/skill/CLAUDE.md` status bar examples: issue number only, no branch.
  - `.squidsquad/qa/CLAUDE.md` status bar examples: same format, no branch.

---

### TC-18: PM creates branch; dev continues on same branch (code inspection)

- **Result**: PASS
- **Notes**: Code inspection confirms `task_begin()` produces the same branch name for any role (since `squidsquad/task/{number}` pattern ignores `{role}`). First call creates; second call checks out existing.
- **Evidence**:
  - `get_branch_name("pm", 700)` → `squidsquad/task/700`
  - `get_branch_name("skill", 700)` → `squidsquad/task/700` (same branch)
  - `git_ops.py` lines 552–558: local check → checkout if exists.
  - `git_ops.py` lines 574–578: create only if neither local nor remote found.
  - TC-7 live test confirmed idempotency.

---

### TC-19: QA verifies on same shared branch (code inspection)

- **Result**: PASS
- **Notes**: `task_begin("qa", 700)` returns `squidsquad/task/700`. QA fetches before checking remote (ensures cross-clone branch visibility). All agents land on the same branch.
- **Evidence**:
  - `git_ops.py` line 562: `_run_list(["git", "fetch", "origin", branch], check=False)` — fetches before remote check.
  - `get_branch_name("qa", 700)` → `squidsquad/task/700`.
  - `.squidsquad/qa/CLAUDE.md` lines 381–390: `task-begin [role] [number]` before verification.

---

### TC-20: Single PR merges unified branch — cleanup correct (code inspection)

- **Result**: PASS
- **Notes**: `pr_merge()` uses `--delete-branch` flag. Issue number extraction uses `parts[-1]` — works for both old and new patterns.
- **Evidence**:
  - `git_ops.py` line 314: `["gh", "pr", "merge", str(pr_number), f"--{strategy}", "--delete-branch"]`
  - `git_ops.py` lines 327–329: `parts[-1].isdigit()` for issue extraction.

---

### TC-21: Multi-agent same branch — no commit conflicts (code inspection)

- **Result**: PASS
- **Notes**: `pull()` uses `git pull --rebase`. Stash + pull + pop pattern for dirty working trees. Sequential commits from multiple agents on same branch are handled via rebase.
- **Evidence**:
  - `git_ops.py` line 86: `git pull --rebase`
  - `git_ops.py` lines 88–95: stash + pull + pop fallback.
  - Shared branch: `squidsquad/task/800` → same for PM and skill → sequential commits work via rebase.

---

### TC-22: `task-end` returns to main

- **Result**: PASS
- **Notes**: Live test confirmed `task-end` returns to `main` (the configured working branch).
- **Evidence**:
  ```
  $ python references/scripts/git_ops.py task-begin skill 99999
  squidsquad/task/99999
  $ python references/scripts/git_ops.py task-end skill 99999
  (WARNING about uncommitted changes — expected with dirty working tree)
  $ git branch --show-current
  main   <- returned to working branch
  ```
  `git_ops.py` lines 600, 608: `working = _get_working_branch()` → `_safe_checkout(working)`.

---

### TC-23: Agent instructions have no hardcoded role-encoded branches

- **Result**: PARTIAL FAIL
- **Notes**: Deployed `.squidsquad/*/CLAUDE.md` files contain zero hardcoded role-encoded branch patterns. However, two source template files in `references/` still have old patterns:
  1. `references/sub-skills/roles/qa/git-commit.md` line 16: `commit-code qa squidsquad/skill/[NUMBER]` — this file is NOT included in QA's `includes.yml` and is not deployed.
  2. `references/sub-skills/roles/pm/pipeline-sentinel.md` line 22: `squidsquad/skill/475` as a documentation example in a comment — not a construction site.
  The deployed agents are clean; the source templates have two stale references.
- **Evidence**:
  ```
  # Deployed CLAUDE.md files: 0 hardcoded branch patterns
  grep -rn 'squidsquad/skill/[0-9]\|squidsquad/qa/[0-9]\|squidsquad/pm/[0-9]' \
    .squidsquad/skill/CLAUDE.md .squidsquad/qa/CLAUDE.md .squidsquad/pm/CLAUDE.md \
    .squidsquad/dm/CLAUDE.md
  -> 0 results

  # Source templates: 2 occurrences
  references/sub-skills/roles/qa/git-commit.md:16:
    commit-code qa squidsquad/skill/[NUMBER]
  references/sub-skills/roles/pm/pipeline-sentinel.md:22:
    squidsquad/skill/475 -> #475  (documentation example)
  ```

---

### TC-24: L4 project override sets `squidsquad/task/{number}`

- **Result**: PASS
- **Notes**: `.squidsquad/config.md` (L4 project config) has `Branch Pattern: squidsquad/task/{number}`. `config.py get branch-pattern` returns this value with exit 0.
- **Evidence**:
  - `.squidsquad/config.md` line 43: `- **Branch Pattern**: squidsquad/task/{number}`
  - `python references/scripts/config.py get branch-pattern` → `squidsquad/task/{number}` (exit 0)

---

### TC-25: `tracker.py` `_check_unmerged_branch` wildcard matches new pattern

- **Result**: PASS
- **Notes**: Uses `git branch -a --list "*squidsquad/*/{number}"` — `*` wildcard matches `squidsquad/task/1000` and `squidsquad/skill/1000`.
- **Evidence**:
  - `tracker.py` line 668: `["git", "branch", "-a", "--list", f"*squidsquad/*/{number}"]`
  - `tracker.py` line 681: validates via `parts[-1] != str(number)`.
  - `tracker.py` docstring line 655: "squidsquad/*/NUMBER pattern" documented.

---

### TC-26: PR conflict rebase uses config-driven pattern

- **Result**: PASS
- **Notes**: Rebase section uses `gh pr list --search "squidsquad/"` — generic prefix, NOT role-encoded. "Only rebase branches for your own tasks" provides task-based ownership check. No `squidsquad/skill/` or `squidsquad/qa/` hardcoded prefix in rebase section.
- **Evidence**:
  - `.squidsquad/skill/CLAUDE.md` line 802: `--search "squidsquad/"` — no role-encoded prefix.
  - `.squidsquad/skill/CLAUDE.md` line 822: "Only rebase branches for your own tasks" — task-based ownership.
  ```
  grep -A5 "rebase" .squidsquad/skill/CLAUDE.md | grep "squidsquad/skill/\|squidsquad/qa/"
  -> 0 results
  ```

---

### TC-27: All 5 test files pass

- **Result**: PASS
- **Notes**: Full suite of 1154 tests pass. All 5 specified test files pass.
- **Evidence**:
  ```
  $ python tests/run_tests.py
  ============================= 1154 passed in 8.36s =============================

  $ python -m pytest tests/test_git_ops.py tests/test_cycle_post.py \
      tests/test_cycle_pre.py tests/test_feat_3296_task_boundary.py \
      tests/test_feat_1074_auto_merge.py -v
  ============================= 183 passed in 5.37s =============================
  ```
  Key regression test: `TestTaskBegin::test_uses_configured_branch_pattern` PASSED.

---

## Smoke Test Results

- [x] `python references/scripts/config.py get branch-pattern` → `squidsquad/task/{number}` (non-empty, exit 0)
- [x] `python references/scripts/git_ops.py task-begin skill 99999` → creates `squidsquad/task/99999`, prints it; cleaned up
- [x] `git branch --show-current` after `task-begin` → `squidsquad/task/99999`
- [x] `python tests/run_tests.py` → exit 0, 1154 tests pass
- [x] `grep -rn 'squidsquad/{role}' references/scripts/git_ops.py` → 0 results outside factory fallback defaults
- [ ] `cat .squidsquad/pm/current-state` contains branch name — NOT verified: PM not active and instructions don't include branch in status bar format (TC-16 FAIL)
