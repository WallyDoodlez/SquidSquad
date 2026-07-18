# QA-RESULTS-13373 — git_ops task-begin local-branch stale-tip sync

**Verdict: PASS — zero gaps.**
**Verifier**: qa (verifier-lead). **PR**: #13458 (branch squidsquad/task/13373, head 6040d6aca). **Type**: type:issue (bug, auto-approved).

## Verification approach

Independent test plan (TEST-PLAN-13373.md) derived from the issue-body ACs, NOT the worker diff. Executed the REAL `git_ops._sync_local_branch_to_origin` against REAL temporary git repos (bare origin + working clone), overriding `git_ops.REPO_ROOT` to the temp repo so git runs there (the helpers pin cwd=REPO_ROOT at git_ops.py:142, not process CWD — see Note below).

## AC walk (issue body Acceptance Criteria)

| AC | Criterion | TC | Result |
|----|-----------|----|--------|
| AC1 | local behind origin -> fetch + fast-forward to origin head | TC-1 | PASS |
| AC2 | diverged -> fail loudly, non-zero exit, BOTH SHAs in stderr | TC-2 | PASS |
| AC3 | local ahead -> keep unpushed work (no-op) | TC-3 | PASS |
| AC4 | origin branch absent -> no-op, no error | TC-4 | PASS |
| AC5 | regression test present (behind + diverged) | TC-6 | PASS |
| gate | task_begin local path wires _sync (not dead code) | TC-5 | PASS |

## Test runs

- Independent verifier tests (TEST-13373-tests.py): **6 passed** in 3.86s.
- Worker regression test (tests/test_13373_task_begin_local_sync.py): **7 passed** in 0.10s.
- Full static gate (python tests/run_tests.py): **53 tests OK**, exit 0, artifacts cleaned.

## pytest output (independent tests)

```
test_tc_01_behind_fast_forwards PASSED
test_tc_02_diverged_fails_loudly PASSED
test_tc_03_ahead_keeps_local PASSED
test_tc_04_origin_absent_noop PASSED
test_tc_05_task_begin_wires_sync PASSED
test_tc_06_regression_test_present PASSED
6 passed in 3.86s
```

## Note (test-harness, not a defect)

First run of TC-1/TC-2 showed false FAILs (exit 0, no-op). Root cause: git_ops `_run`/`_run_list` pin `cwd=str(REPO_ROOT)` (REPO_ROOT = SCRIPT_DIR.parent.parent) rather than the process CWD, so the function operated on the real repo (where local==origin at the PR head -> clean no-op). Corrected the harness by overriding `git_ops.REPO_ROOT` at call time. This is a verifier-harness artifact; the fix itself is sound (manual repro confirmed `git fetch origin <branch>` opportunistically updates refs/remotes/origin/<branch> under the default clone refspec, so the fetch-then-rev-parse logic reads origin's real head).

## Observation (non-blocking, not a gap)

On the divergence path, task_begin `_safe_checkout`s the local ref BEFORE `_sync` fails loudly (sys.exit 1). The working tree is thus left on the diverged local branch at exit. This does NOT violate AC2: the criterion is "fail loudly rather than SILENTLY check out" — the loud stderr (both SHAs + DIVERGED) plus the non-zero exit is the gate that stops the verifier from proceeding. Intent met. Recorded for awareness only.

## Decision

All ACs observably satisfied against a live instance; regression tests present and green; full suite green. Zero gaps. -> approve PR #13458 + merge + Pending Ship.
