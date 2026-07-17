# TEST-PLAN-13373 — git_ops.py task-begin local-branch stale-tip sync

**Source**: GitHub issue #13373 Acceptance Criteria (issue body "Suggested fix" + regression-test clause). Filed by verifier improvement-scan.
**Derived without reading the worker's test file (tests/test_13373_task_begin_local_sync.py).**

## Acceptance Criteria (extracted from issue body)

- **AC1** — Local task branch strictly BEHIND origin: task-begin fetches and fast-forwards; the checked-out tip equals origin's head (the fix commit is present).
- **AC2** — Local and origin DIVERGED (neither ancestor of the other): fail loudly — non-zero exit, BOTH SHAs printed to stderr; never silently verify an unsynced tip.
- **AC3** (implied, "keep unpushed work") — Local strictly AHEAD of origin: keep local unpushed work; no-op, local tip unchanged.
- **AC4** (implied, "origin absent") — Branch never pushed to origin: no-op, no error, local tip unchanged.
- **AC5** — Regression test exists covering the behind and diverged cases (behind -> lands on origin head; diverged -> non-zero exit + both SHAs).

## Test Cases (exercised against real git repos via the real _sync_local_branch_to_origin)

Harness: build a bare `origin` repo + a working clone in a tmp dir; drive each scenario with real `git`; invoke the REAL function in-process (chdir into the clone, on the task branch) via a subprocess `python -c "import git_ops; git_ops._sync_local_branch_to_origin(branch)"` so exit code + stderr are captured exactly as task-begin would surface them.

### TC-1 (covers AC1): behind -> fast-forward to origin head
- **Precondition**: origin/<branch> has commit O2; local <branch> at O1 (O1 is ancestor of O2).
- **Steps**: chdir clone, checkout branch at O1, run _sync.
- **Expected**: exit 0; local HEAD now == O2 (origin head); stdout mentions fast-forward.
- **Verification**: `git rev-parse HEAD` == origin O2 SHA.

### TC-2 (covers AC2): diverged -> fail loudly, both SHAs, non-zero exit
- **Precondition**: local has commit L (on top of base), origin has commit O (on top of base); neither ancestor of the other.
- **Steps**: chdir clone, checkout diverged local branch, run _sync.
- **Expected**: exit != 0; stderr contains BOTH the local short-SHA and the origin short-SHA and the word DIVERGED.
- **Verification**: returncode == 1; both SHAs substring-present in stderr.

### TC-3 (covers AC3): ahead -> keep local, no-op
- **Precondition**: local <branch> at L2 (ahead), origin/<branch> at L1 (L1 ancestor of L2).
- **Steps**: chdir clone, checkout branch at L2, run _sync.
- **Expected**: exit 0; local HEAD unchanged == L2; local commit not lost.
- **Verification**: `git rev-parse HEAD` == L2 SHA.

### TC-4 (covers AC4): origin absent -> no-op, no error
- **Precondition**: local <branch> exists at L1; origin has NO such branch.
- **Steps**: chdir clone, checkout branch, run _sync.
- **Expected**: exit 0; local HEAD unchanged; no crash.
- **Verification**: returncode == 0; HEAD == L1.

### TC-5 (covers AC1/AC2 gate integration): task_begin local path wires the sync
- **Precondition**: source-level — task_begin's local-exists path calls _sync_local_branch_to_origin AFTER checkout, BEFORE returning.
- **Steps**: static assertion the wiring is present (grep-equivalent) so the helper is actually reachable from task-begin, not dead code.
- **Expected**: task_begin body contains `_sync_local_branch_to_origin(branch)` on the local path.

### TC-6 (covers AC5): regression test presence + coverage
- **Precondition**: worker PR ships a regression test.
- **Steps**: assert tests/test_13373_task_begin_local_sync.py exists and references the behind + diverged scenarios.
- **Expected**: file present; contains assertions for fast-forward (behind) and divergence (non-zero + SHAs).

## Coverage matrix
- AC1 -> TC-1, TC-5
- AC2 -> TC-2, TC-5
- AC3 -> TC-3
- AC4 -> TC-4
- AC5 -> TC-6

Every AC is mapped.

## Comprehension Questions
N/A — this task changes executable Python (git_ops.py), not LLM-consumed instructions. No CQ spec required.
