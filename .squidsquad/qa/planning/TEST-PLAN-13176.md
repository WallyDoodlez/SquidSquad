# TEST-PLAN-13176 — Harness deploy-error stage=commit empty detail + re-trigger risk

**Source**: GitHub issue #13176 Acceptance Criteria (Impact 1 + Impact 2).
**Derived without reading the diff.**

Deterministic harness code (`harness.py`). Two defects to close:

- **AC-1 (Undiagnosable empty detail)** — a `deploy-error stage=commit` event must carry
  a non-empty, diagnosable `detail`, even when `git commit` writes its failure to stdout
  (e.g. `nothing to commit, working tree clean`) leaving stderr empty.
- **AC-2 (Benign re-trigger eliminated at root)** — a no-net-change recompose (composed
  output already == HEAD) must NOT route through §11 deploy-error recovery; it must take
  the clean no-op success path (checksum advanced, no deploy-error, no re-fire).

## Test Cases

### TC-1 (covers AC-2): no-net-change staging returns False → clean success
- **Precondition**: `_stage_composed_outputs` runs where `git add` exits 0 but no staged diff.
- **Expected**: returns False; caller takes clean no-op success path (checksum advanced).
- **Verification command**: pytest `TestStageComposedOutputs::test_returns_false_when_add_ok_but_no_staged_diff` (and `_returns_true_when_real_staged_diff`, `_returns_false_when_no_composed_files_exist`).

### TC-2 (covers AC-1): commit-failure detail combines stdout when stderr empty
- **Precondition**: `git commit` returns non-zero with stdout="nothing to commit...", stderr="".
- **Expected**: emitted deploy-error `stage=commit`, `detail` non-empty and contains "nothing to commit".
- **Verification command**: pytest `test_commit_failure_detail_combines_stdout_13176`.

### TC-3 (regression-test integrity): new tests fail pre-fix
- **Precondition**: run the new tests against origin/main (pre-fix) harness.py.
- **Expected**: TC-1's staged-diff test and TC-2's combine test FAIL on old code (prove they catch the bug).
- **Verification command**: worktree of origin/main + new test file, run the two selectors.

### TC-4 (no regression): full deploy test module + full suite green on the fix
- **Expected**: all tests in test_harness_deploy_12912.py pass; full `tests/run_tests.py` green.

## Coverage matrix
- AC-1 → TC-2, TC-3
- AC-2 → TC-1, TC-3
- (regression guard) → TC-4

## Comprehension Questions
N/A — deterministic harness code, not LLM-consumed instruction. No CQ spec.
