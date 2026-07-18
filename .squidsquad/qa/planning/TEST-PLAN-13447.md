# TEST-PLAN-13447

Derived independently from the issue body + skill's corrected-diagnosis comment (the issue was mine originally; skill investigated and found the real root cause differed from my initial filing — the fix targets skill's corrected diagnosis, and I verify against that corrected diagnosis, not my own original filing).

## ACs derived from the corrected diagnosis + fix

- **AC1**: After a successful `pr_merge()`, locally-dirtied composed outputs (`.squidsquad/<role>/CLAUDE.md`, `CLAUDE.linked.md`) are reverted to the committed `working`-branch version, so the next checkout doesn't abort with "local changes would be overwritten."
- **AC2**: After a successful merge, local `working` (main) is fast-forwarded to `origin/working` — fail-open (never force-merges on divergence, never raises/blocks on a network hiccup or checkout failure).
- **AC3**: Both new steps run ONLY on the successful-merge path, and are best-effort — a failure in either must never cause `pr_merge()` to report the merge as failed when GitHub already recorded success.
- **AC4 (regression check against #13613, now merged to main)**: This branch's `commit_code()`-touching diff (from before #13613 existed) must not silently clobber #13613's now-merged fast-forward logic in `commit_code()` when reconciled with current main. Verified via a local test three-way merge (not committed) — auto-resolved cleanly, both #13613's `_checkout_and_sync_working` (in `commit_code`) and #13447's `_checkout_and_ff_working_after_merge` (in `pr_merge`) survive intact; they're parallel helpers for different call sites, not competing edits to the same lines.
- **AC5**: New regression tests (`test_13447_pr_merge_post_merge_sync.py`, 13 cases) plus updated `test_git_ops.py`/`test_feat_1074_auto_merge.py` all pass.
- **AC6**: No regressions — comprehension staleness clean (script-only, no CQ spec expected), full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 | Read `_revert_composed_state_contamination`; run its dedicated test cases (dirty CLAUDE.md/CLAUDE.linked.md reverted, unrelated dirty files left alone, multi-role, clean-tree no-op) |
| TC2 | AC2 | Read `_checkout_and_ff_working_after_merge`; run its cases (behind→ff, checkout-failure-never-raises, diverged-never-merges, ff-failure-warns, origin-unreachable-noop) |
| TC3 | AC3 | Run `test_success_path_reverts_then_syncs`, `test_failed_merge_never_syncs`, `test_already_merged_never_syncs` |
| TC4 | AC4 | `git merge origin/main --no-commit --no-ff` on the branch locally; inspect for conflict markers and confirm both helpers' presence post-merge; `git merge --abort` afterward (verification-only, not committed) |
| TC5 | AC5 | Run full `test_13447_pr_merge_post_merge_sync.py` + `test_git_ops.py` + `test_feat_1074_auto_merge.py` (280 total) |
| TC6 | AC6 | `comprehension_staleness.py check`; `tests/run_tests.py static` |
