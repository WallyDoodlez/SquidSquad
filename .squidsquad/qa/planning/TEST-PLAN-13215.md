# TEST-PLAN-13215 — deploy-pull survives a dirty agent clone

**Derived independently** from the issue body (pm-filed) + dm/skill corroboration comments.

## Expected behavior
The harness deploy sequence's git-pull into a target clone must NOT abort when the clone has an uncommitted change to a file the incoming commit also touches. It must stash-around-merge (like `git_ops.pull`), land the deploy-sync, and re-apply or resolve the dirty change. A genuine merge conflict still fails → §11 recovery, without leaving the clone MERGING.

## ACs (independent)
- AC1 clean tree behind origin → pulls
- AC2 already-up-to-date → ok
- AC3 dirty tree → stash→merge→pop survives (core fix)
- AC4 genuine conflict → (False)+§11 recovery, clone not MERGING (`git merge --abort`)
- AC5 #13167 no-op-stash guard (clean tree, nothing popped)
- AC6 #13045 pop-conflict → resolve to pulled HEAD, drop
- AC7 `merge --abort` precedes stash restore (MEDIUM review fix)

## Method
Real-git integration (`tests/test_feat_13215_deploy_pull_dirty_clone.py`) reproduces the abort and proves survival; skill's mocked `TestSafePullInClone13215` (8 tests) covers the orchestration branches. No-regression: full `tests/test_harness.py`.
