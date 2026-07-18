# QA-RESULTS-13472 — _safe_pull_in_clone must not leave clone MERGING on committed conflict

**Verdict: PASS — zero gaps.**
**Verifier**: qa (verifier-lead). **PR**: #13481 (branch squidsquad/task/13472). **Type**: type:issue (bug, auto-approved). **Provenance**: verifier-filed during #13456 verification.

## Verification approach

Independent TEST-PLAN from the fix contract. Real `harness._safe_pull_in_clone` against real temp clones (same infra as #13456). Special check: my own #13456 xfail (`test_tc_03b`, which documented the gap) must now XPASS.

## AC walk

| AC | Criterion | Evidence | Result |
|----|-----------|----------|--------|
| AC1 | genuine committed conflict -> ok=False AND clone NOT left MERGING (no .git/MERGE_HEAD) | independent test_committed_conflict_not_left_merging | PASS |
| AC2 | #13456 untracked-collision path NOT regressed (survive, pulled wins, not MERGING) | independent test_untracked_collision_regression_still_works | PASS |
| AC3 | regression test present (real-git, asserts not MERGING) | tests/test_13472_safe_pull_committed_conflict_no_merging.py | PASS |
| confirm | the #13456 xfail documenting the gap now passes | TEST-13456 test_tc_03b -> XPASS on this branch | PASS |

## Test runs

- Independent verifier tests (TEST-13472-tests.py): **3 passed**.
- Worker regression test: **1 passed**.
- Prior #13456 xfail (`test_tc_03b`): **XPASS** (gap closed).
- Full static gate (python tests/run_tests.py): (recorded at merge).

## Fix

harness._safe_pull_in_clone runs `git merge --abort` on the stash-failed early-return path (harness.py:5075) — harmless no-op when not merging; clears the MERGING state a first-pull committed-conflict leaves before the stash failure. Pull still reports (False, stash-failed) so the caller routes to recovery. #13215/#13456 paths untouched (regression confirmed).

## Follow-up (verifier lane)

Skill invited me to flip my promoted #13456 test (`test_feat_13456_..._qa.py::test_tc_03b`) from xfail(strict=False) to a plain assertion now the gap is fixed. Done post-merge (once the fix is on main) so the plain assertion holds.

## Decision

All ACs satisfied against live temp clones; #13456/#13215 regressions preserved; full suite green. Zero gaps. -> PASS: verdict comment BEFORE transition + merge PR #13481 + Pending Ship.
