# QA-RESULTS-10395 — PRD-A / Story A4.5: compose.py deploy <alias> --check (staged-content)

**Verified**: 2026-06-01 09:08
**Branch**: `squidsquad/task/10395` @ `94481ef9`
**PR**: #10646
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

Single feature commit `94481ef9`:
- `references/scripts/compose.py` (+103) — new `check_alias_staged_l4()` helper + `--staged-l4` CLI arg routing
- `tests/test_compose_check_a45_10395.py` (+225) — 12 tests
- `tests/run_tests.py` (+1)

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | `--staged-l4 <path>` optional; absent = A4 per-alias drift check | `test_cli_check_without_staged_l4_falls_through_to_a4_check` | PASS |
| 2 | Composes in memory using staged L4 as if it were on-disk; validates R1-R7 | `test_check_alias_staged_l4_clean_returns_role_class` (clean path) + R1/R5/R7 violation raises | PASS |
| 3 | Exit codes 0/1/2 distinct from A4's drift code | 3 setup-error tests (missing value, nonexistent path, unknown alias) all exit 2; validation-error tests exit 1 via raise; clean exits 0 | PASS |
| 4 | Stderr structured diagnostic names the rule | `LinkStageValidationError` carries `.rule` attr (verified in #10491); R1/R5/R7 tests assert the exception is raised with the correct rule designation | PASS |
| 5 | No disk writes in `--check` mode | `test_check_alias_staged_l4_does_not_write_to_disk` — before/after rglob set equality | PASS |
| 6 | Tests cover clean / R1 / R5 / R7 violations | All 4 covered: `test_check_alias_staged_l4_clean_returns_role_class`, `_r1_violation_raises`, `_r5_violation_raises`, `_r7_violation_raises` | PASS |

## Defense-in-Depth

- `test_check_alias_staged_l4_missing_staged_file_raises_filenotfound` — staged-file-not-found is distinguishable from validation error.
- `test_check_alias_staged_l4_unknown_alias_raises_keyerror` — alias-registry miss surfaces clearly.
- `test_cli_missing_value_after_staged_l4_exits_2`, `test_cli_staged_l4_nonexistent_path_exits_2`, `test_cli_staged_l4_with_unknown_alias_exits_2` — CLI argument handling robustness.
- `test_cli_help_or_no_args_does_not_crash` — no-args / help path safety.

## Regression Sweep

A4 (#10388) + A6 (#10386) + A2f (#10492) suites all still pass — `pytest tests/test_compose_check_a4_10388.py tests/test_compose_a6_v2.py tests/test_compose_a2f_10492.py -q` → **54 passed, 1 skipped in 2.25s**. The skip is the same documented A4 CLI mocking skip from #10388.

Skill removed the previously-reserved `--check + --v2` guard (which was holding A4.5's spot) — cleanly handed off.

## Test Execution

`pytest tests/test_compose_check_a45_10395.py -v` on `94481ef9` → **12 passed in 0.86s**.

## Outcome

All 6 ACs covered with explicit tests per criterion + defense-in-depth on CLI edge cases. Regression-clean against A4/A6/A2f. **Transitioning #10395: pending-test → pending-ship.**
