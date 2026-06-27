# TEST-PLAN-13211 — hoist freshen serialization into git_ops.ensure_main_and_pull

**Derived independently** from the finding (verifier-filed, residual from verifying #13197).

## Expected behavior
The freshen serialization that #13197 added watcher-locally must cover BOTH callers of `git_ops.ensure_main_and_pull` — the L4 watcher-burst AND the post-merge deploy-all path — so a watcher burst overlapping a deploy can't collide on `.git/index.lock`. Relocate the lock into `git_ops.ensure_main_and_pull`; retire the watcher-local lock.

## ACs (independent)
- AC1 `_ENSURE_MAIN_LOCK` exists in git_ops; held across checkout+pull
- AC2 watcher-local `_FRESHEN_LOCK` removed
- AC3 no deadlock (non-reentrant, single acquire per path)
- AC4 watcher + deploy paths share the one lock
- AC5 "Never raises" preserved; lock released on exception

## Method
Concurrency tests with a mocked git layer measuring max concurrency (must be 1). QA test (`tests/test_feat_13211_ensure_main_lock.py`) adds lock-release-on-exception (no-deadlock) proof. No-regression: full `tests/test_git_ops.py` + `tests/test_l4_file_watcher_e3.py`.

## Scope note
The no-`timeout=` subprocess gap is filed separately as #13262 — out of scope, not a reblock.
