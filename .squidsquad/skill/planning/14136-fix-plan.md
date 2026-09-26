# Fix plan -- #14136

_Lineage file (VAULT-ARCH 9.3): the direction a reviewer judges before the
diff. Keep each section to a few lines._

## Root cause

`tests/test_13373_task_begin_local_sync.py` real-git setup runs `git clone`
into tmp_path with no retry. Under the full static gate with 4 agent clones
running, one `clone --bare` exited non-zero with EMPTY stderr (transient
Windows file lock / AV). `_git()` put only stderr in its AssertionError, so
the red carried no diagnosis. Test logic and git_ops are not at fault
(passed alone and on two full reruns).

## Intended direction

`_git()` failure message now carries rc + stdout + stderr. New `_git_clone()`
retries a failed clone once (after removing the partial destination, since
git refuses a non-empty dest) and raises `_git`'s full diagnostic if the
retry also fails. All six setup clones in the #13819 real-git class use it.
No production code changes; assertions under test are untouched.

## Impact

Test-only. Three new unit tests cover the helpers (diagnostic message,
retry-after-empty-stderr with partial-dest cleanup, persistent failure raises).

## Vault context consumed

- [[learning-single-static-gate-red-may-be-flake-rerun-before-reject]] -- the isolation + rerun triage that classified this red as a flake; the fix makes the next such red self-diagnosing instead
- [[learning-tests-must-not-mutate-shared-live-state]] -- confirmed these tests already isolate to tmp_path; the flake is load contention, not shared-state mutation

## Applicable rules

- None matched (searched rules lane: test, flake, git, windows)
