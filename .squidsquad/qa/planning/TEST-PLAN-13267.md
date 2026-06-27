# TEST-PLAN-13267 — git_ops.pull first pull pinned to --no-rebase

**Derived independently** from my filed finding (out of #13261's scope).

## Expected behavior
The first `git pull` in `git_ops.pull` must be `git pull --no-rebase` (consistent with the now-pinned retry), so a `pull.rebase=true` clone cannot leave a REBASE state the #13261 `git merge --abort` recovery can't clear.

## ACs
- AC1 first pull pinned to --no-rebase
- AC2 both pulls --no-rebase; no bare git pull survives
- AC3 regression test for the first pull
- AC4 #13261 retry merge-abort preserved

## Method
Unit: patch `_run`, exercise stash→retry path, assert all `git pull` calls are `--no-rebase` (`tests/test_feat_13267_pull_both_no_rebase.py`) + skill's `test_first_pull_is_no_rebase`. No-regression: full `tests/test_git_ops.py`.
