# TEST-PLAN-13271 — behind-count squash-merge guard

**Derived independently** from the incident report + prevention direction.

## Expected behavior
`git_ops.pr_merge` (squash strategy) must refuse a merge when the PR branch is too far behind base (> threshold), so a stale-tree squash from a deeply-behind clone cannot mass-revert shipped fleet work. Fail-SAFE (refuse only, never mutate main); fail-OPEN when the behind count is undeterminable.

## ACs
- AC1 far-behind squash refused
- AC2 within threshold proceeds
- AC3 exact boundary (> max_behind)
- AC4 undeterminable → fail-open
- AC5 squash-only
- AC6 env-tunable threshold (default 50)
- AC7 refusal before any merge subprocess (no mutation)

## Method
Unit: patch `_pr_behind_by`/`_merge_max_behind`, assert refuse/proceed + no merge subprocess on refusal (`tests/test_feat_13271_merge_behind_guard.py`) + skill's TestPrMerge/TestPrBehindBy. Full `tests/test_git_ops.py`.

## Merge note (self-referential)
The branch is itself behind main → re-verify the squash diff is +additions-only (no #13262/#13267/config.md deletions) before merging, else it re-triggers the very incident it guards. Interim guard; scope-audit auto-revert is a named follow-up — not a reblock.
