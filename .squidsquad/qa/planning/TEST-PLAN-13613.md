# TEST-PLAN-13613

Derived independently from the issue body (`ISSUE: IMPROVEMENT: local main silently drifts behind origin/main across commit-code round-trips`).

## ACs derived from the issue

- **AC1**: `commit_code()`'s post-commit checkout back to the working branch now fast-forwards local `working` to `origin/working` when it's behind.
- **AC2**: On divergence (both branches have unique commits) the sync must NOT merge/force-overwrite — no process exit either (unlike `_sync_local_branch_to_origin`'s loud-fail semantics for feature branches, since this runs after a commit already succeeded).
- **AC3**: If local is ahead (unpushed local commits) — no merge attempted, local state preserved as-is.
- **AC4**: If origin has no such branch (or fetch fails) — silent no-op, never crashes the caller.
- **AC5**: All 4 return sites in `commit_code()` (nothing-to-commit, commit-error, push-failure, success) go through the new sync path, not just the happy path.
- **AC6**: A fast-forward failure (e.g. race) warns to stderr but never raises/exits — commit_code()'s return value/behavior for the caller is otherwise unaffected.
- **AC7**: New regression tests (`test_13613_working_branch_sync.py`, 11 cases) cover all the above scenarios; existing `test_git_ops.py::TestCommitCode` tests still pass with the new sync probe calls tolerated.
- **AC8**: No regressions — comprehension staleness clean (script-only change, no LLM-facing prose, so no new CQ spec expected), full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC2/AC3/AC4 | Read `_sync_working_branch_to_origin`'s logic directly; run `test_13613_working_branch_sync.py`'s behind/diverged/ahead/origin-absent/in-sync cases |
| TC2 | AC5 | Read `commit_code()`'s 4 `_safe_checkout(working)` -> `_checkout_and_sync_working(working)` call sites in the diff |
| TC3 | AC6 | Run `test_ff_failure_warns_never_exits` |
| TC4 | AC7 | Run full `test_13613_working_branch_sync.py` (11 cases) + `test_git_ops.py` (existing suite, confirm still green) |
| TC5 | AC8 | `comprehension_staleness.py check`; `tests/run_tests.py static` |

## Note
This script is one I use directly this session (`task-begin`/`task-end`/`commit-code` calls are part of my own verification workflow, though my `commit-state` path is untouched by this diff — only `commit_code()`'s return sites changed). Verified with that in mind.
