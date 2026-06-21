# QA-RESULTS-13158

**Issue**: #13158 — harness deploy-signal git pull fatals on diverged main (no merge strategy); recurring deploy-error stage=pull
**PR**: #13160 (branch squidsquad/task/13158 @ 01faacba9, base main; harness.py +27/-9 + tests/test_harness_deploy_12912.py +20)
**Verdict**: ✅ **PASS — zero gaps**
**Verified by**: verifier (qa), 2026-06-21 16:20
**Method**: Independent TEST-PLAN; verified on a clean worktree with a revert-the-fix proof.

## AC Walk

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1/AC4 merge fix | ✅ PASS | _run_deploy_sequence: `_git_in_clone(clone_path, ["pull","--no-rebase","--no-edit","origin","main"])` (was ["pull","--ff-only",...]). --no-rebase = MERGE (project rule, #12526 parity); --no-edit non-interactive. Comment notes a genuine merge CONFLICT still fails → §11 recovery (benign divergence reconciled, real conflict still caught) |
| TC2 | AC2 tests pass | ✅ PASS | test_harness_deploy_12912.py: 44 passed incl test_deploy_pull_merges_not_ff_only_13158 (asserts --no-rebase present, --ff-only absent) |
| TC3 | AC2 catches drift | ✅ PASS | Reverted ONLY harness.py → TestRunDeploySequence::test_deploy_pull_merges_not_ff_only_13158 FAILED (`'--no-rebase' not found in ['pull','--ff-only','origin','main']`). Restored → passes. Proves the regression catches the original --ff-only bug |
| TC4 | AC3 no regression | ✅ PASS | `python tests/run_tests.py static`: 4887 gated PASS, 0 fail, 0 error |

## Findings

Correct root-cause fix for the recurring `deploy-error stage=pull` class. The deploy-sequence pull now MERGES a diverged main (`--no-rebase --no-edit`) instead of fataling on `--ff-only`, consistent with the team's always-merge-never-rebase rule and the analogous #12526 launcher fix. Crucially, it does NOT blindly force-merge: a genuine merge conflict still fails the pull → §11 recovery, so the fix reconciles benign (non-overlapping) divergence without masking real conflicts. The push-rejected comment was updated to a consistent narrative (next deploy's merge-pull reconciles). Regression test proven genuine.

**Cross-reference (informational):** this is the root cause behind the deploy-signal/deploy-error condition observed at this session's boot (local 25-behind, deploy-signals lingering). Once shipped + the fleet restarts onto it, the deploy/recompose path reconciles divergence instead of fataling. Does not change my standing decision to defer the currently-pending deploy-signals (operator-paced restart).

## Disposition

Verdict PASS → transition pending-test → pending-ship. Regression test committed in PR (tests/, preserved). Merge + ship deferred to DM. TEST-PLAN-13158 + QA-RESULTS-13158 on qa planning.
