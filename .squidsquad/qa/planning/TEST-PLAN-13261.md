# TEST-PLAN-13261 — git_ops.pull merge-abort on a genuine-conflict retry

**Derived independently** from the issue body (skill-filed during #13215 DS-review).

## Expected behavior
`git_ops.pull` (the every-agent cwd pull path) must `git merge --abort` before restoring the stash when the retry pull hits a genuine committed-divergence conflict — otherwise the clone is left MERGING and `_safe_stash_pop` misreads the merge's unmerged paths as a pop conflict and DROPS the stash. Mirror of the #13215 deploy-path fix.

## ACs (independent)
- AC1 retry conflict → `merge --abort` before `_safe_stash_pop`
- AC2 clone NOT left MERGING
- AC3 stashed change preserved (not dropped)
- AC4 no conflict markers leaked
- AC5 pull returns False → recovery

## Method
Real-git integration (`tests/test_feat_13261_pull_merge_abort.py`): dirty file the incoming commit touches (first pull aborts) + committed divergence (retry merge conflicts); chdir into the clone, call `git_ops.pull()`, assert stash preserved + not MERGING. skill's mocked `test_pull_retry_fail_aborts_merge_before_pop` covers call ordering. No-regression: full `tests/test_git_ops.py`.

## Out-of-scope observation
First `git pull` (line 267) still bare vs the now-`--no-rebase` retry — latent under `pull.rebase=true`. Flagged for triage, not a reblock.
