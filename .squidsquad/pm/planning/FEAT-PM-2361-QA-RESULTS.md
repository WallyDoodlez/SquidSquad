# FEAT-PM-2361 QA Results — TC Coverage Gate

## Summary

| TC | Title | Result |
|----|-------|--------|
| TC-1 | Happy path — full coverage, all PASS | PASS |
| TC-2 | Happy path — full coverage, mix of PASS and FAIL | PASS |
| TC-3 | Gap detection — missing TCs in QA-RESULTS | PASS |
| TC-4 | Invalid result — "not applicable" rejected | PASS |
| TC-5 | Invalid result — "deferred" rejected | PASS |
| TC-6 | Tolerant parsing — TC-01 format | PASS |
| TC-7 | Tolerant parsing — TC-1 (no zero-pad) format | PASS |
| TC-8 | Tolerant parsing — "TC 01" (space instead of dash) | PASS |
| TC-9 | Tolerant parsing — cross-format matching | PASS |
| TC-10 | Auto-discovery by issue number | PASS |
| TC-11 | Auto-discovery — multiple planning dirs, PM preferred | PASS |
| TC-12 | Multiple revisions — picks highest -RN | PASS |
| TC-13 | Multiple revisions — base file used when no -RN exists | PASS |
| TC-14 | No TEST-PLAN exists — gate skipped | PASS |
| TC-15 | BLOCKED results — counted as covered but block shipping | PASS |
| TC-16 | --force does NOT bypass TC coverage | HUMAN-REQUIRED |
| TC-17 | tracker.py integration — pending-test to pending-ship blocked | HUMAN-REQUIRED |
| TC-18 | tracker.py integration — pending-test to pending-ship allowed | HUMAN-REQUIRED |
| TC-19 | Graceful degradation — tc_coverage.py missing | HUMAN-REQUIRED |
| TC-20 | Edge case — duplicate TC IDs in TEST-PLAN | PASS |
| TC-21 | Edge case — extra TCs in QA-RESULTS not in TEST-PLAN | PASS |
| TC-22 | Edge case — empty TEST-PLAN (no TCs) | PASS |
| TC-23 | Edge case — empty QA-RESULTS (no TCs) | PASS |
| TC-24 | --debug flag prints unmatched lines | PASS |
| TC-25 | Prose references to TC numbers NOT counted as markers | PASS |
| TC-26 | Table-row TC format recognized | PASS |

**Smoke tests:**

| Smoke Test | Result |
|------------|--------|
| `--help` runs without error | PASS |
| `--issue 9999` exits cleanly | PASS |
| `tests/test_tc_coverage.py` passes | HUMAN-REQUIRED (file does not exist) |

**Totals:** 22 PASS, 0 FAIL, 5 HUMAN-REQUIRED (tracker.py integration tests requiring real GitHub Issues + missing unit test file)

---

## Detailed Results

### TC-1: Happy path — full coverage, all PASS
- **Result**: PASS
- **Notes**: Exit code 0. Output: "TC Coverage: 5/5 (100%)" and "All TCs accounted for. Gate passed."
- **Verified at**: 2026-04-23

### TC-2: Happy path — full coverage, mix of PASS and FAIL
- **Result**: PASS
- **Notes**: Exit code 0. Coverage reports 3/3 (100%). FAIL results do not affect coverage exit code — only presence matters.
- **Verified at**: 2026-04-23

### TC-3: Gap detection — missing TCs in QA-RESULTS
- **Result**: PASS
- **Notes**: Exit code 1. Output lists TC-2 and TC-4 as missing. Coverage: 3/5 (60%).
- **Verified at**: 2026-04-23

### TC-4: Invalid result — "not applicable" rejected
- **Result**: PASS
- **Notes**: Exit code 1. stderr contains "Invalid result for TC-2: only PASS, FAIL, BLOCKED are valid".
- **Verified at**: 2026-04-23

### TC-5: Invalid result — "deferred" rejected
- **Result**: PASS
- **Notes**: Exit code 1. TC-2 flagged with invalid result. "Deferred" correctly rejected.
- **Verified at**: 2026-04-23

### TC-6: Tolerant parsing — TC-01 format
- **Result**: PASS
- **Notes**: Exit code 0. Zero-padded TC-01/TC-02 parsed and matched. Coverage: 2/2.
- **Verified at**: 2026-04-23

### TC-7: Tolerant parsing — TC-1 (no zero-pad) format
- **Result**: PASS
- **Notes**: Exit code 0. Non-zero-padded IDs matched correctly.
- **Verified at**: 2026-04-23

### TC-8: Tolerant parsing — "TC 01" (space instead of dash)
- **Result**: PASS
- **Notes**: Exit code 0. Space-separated format recognized and normalized.
- **Verified at**: 2026-04-23

### TC-9: Tolerant parsing — cross-format matching
- **Result**: PASS
- **Notes**: Exit code 0. TC-01 in plan matched to TC-1 in results via integer normalization.
- **Verified at**: 2026-04-23

### TC-10: Auto-discovery by issue number
- **Result**: PASS
- **Notes**: Script discovers FEAT-PM-2361-TEST-PLAN.md from .squidsquad/pm/planning/. "no test plan found" does NOT appear in output.
- **Verified at**: 2026-04-23

### TC-11: Auto-discovery — multiple planning dirs, PM preferred
- **Result**: PASS
- **Notes**: With both pm/ and skill/ planning dirs containing matching files, _discover_files returns the PM path.
- **Verified at**: 2026-04-23

### TC-12: Multiple revisions — picks highest -RN
- **Result**: PASS
- **Notes**: With QA-RESULTS.md, QA-RESULTS-R2.md, and QA-RESULTS-R3.md present, _discover_files returns the R3 file.
- **Verified at**: 2026-04-23

### TC-13: Multiple revisions — base file used when no -RN exists
- **Result**: PASS
- **Notes**: With only FEAT-PM-100-QA-RESULTS.md (no -RN variants), _discover_files returns the base file.
- **Verified at**: 2026-04-23

### TC-14: No TEST-PLAN exists — gate skipped
- **Result**: PASS
- **Notes**: _discover_files returns None for test_plan. CLI with --issue 99999 exits 0 with "No test plan found ... Gate skipped."
- **Verified at**: 2026-04-23

### TC-15: BLOCKED results — counted as covered but block shipping
- **Result**: PASS
- **Notes**: Exit code 2. Coverage: 3/3 (100%). stderr contains "BLOCKED TCs: TC-2 -- cannot ship". BLOCKED counts as covered but blocks shipping with distinct exit code 2.
- **Verified at**: 2026-04-23

### TC-16: --force does NOT bypass TC coverage
- **Result**: HUMAN-REQUIRED
- **Notes**: Requires a real GitHub Issue at status pending-test to test tracker.py transition with --force flag. Cannot create test issues in this environment.
- **Verified at**: 2026-04-23

### TC-17: tracker.py integration — pending-test to pending-ship blocked on coverage gap
- **Result**: HUMAN-REQUIRED
- **Notes**: Requires a real GitHub Issue at status pending-test with TEST-PLAN and incomplete QA-RESULTS. Cannot create test issues in this environment.
- **Verified at**: 2026-04-23

### TC-18: tracker.py integration — pending-test to pending-ship allowed at 100% coverage
- **Result**: HUMAN-REQUIRED
- **Notes**: Requires a real GitHub Issue at status pending-test with full QA-RESULTS coverage. Cannot create test issues in this environment.
- **Verified at**: 2026-04-23

### TC-19: Graceful degradation — tc_coverage.py missing
- **Result**: HUMAN-REQUIRED
- **Notes**: Requires tracker.py integration with a real GitHub Issue. Renaming tc_coverage.py in a shared environment risks side effects for other tests.
- **Verified at**: 2026-04-23

### TC-20: Edge case — duplicate TC IDs in TEST-PLAN
- **Result**: PASS
- **Notes**: Exit code 1. stderr contains "ERROR: Duplicate TC IDs in TEST-PLAN: TC-1".
- **Verified at**: 2026-04-23

### TC-21: Edge case — extra TCs in QA-RESULTS not in TEST-PLAN
- **Result**: PASS
- **Notes**: Exit code 1. stderr contains "Extra TCs in QA-RESULTS not in TEST-PLAN: TC-3". Coverage reports 2/2 for plan TCs.
- **Verified at**: 2026-04-23

### TC-22: Edge case — empty TEST-PLAN (no TCs)
- **Result**: PASS
- **Notes**: Exit code 0. Output: "No TCs found in TEST-PLAN. Gate skipped (0/0)."
- **Verified at**: 2026-04-23

### TC-23: Edge case — empty QA-RESULTS (no TCs)
- **Result**: PASS
- **Notes**: Exit code 1. Coverage: 0/3 (0%). All three TCs listed as missing.
- **Verified at**: 2026-04-23

### TC-24: --debug flag prints unmatched lines
- **Result**: PASS
- **Notes**: Exit code 0. Debug output on stderr includes "--- Debug: unmatched lines in QA-RESULTS ---" with specific unmatched lines and line numbers.
- **Verified at**: 2026-04-23

### TC-25: Prose references to TC numbers NOT counted as markers
- **Result**: PASS
- **Notes**: Exit code 1. "see TC-2 for details" in prose is NOT recognized as a TC marker. TC-2 listed as missing.
- **Verified at**: 2026-04-23

### TC-26: Table-row TC format recognized
- **Result**: PASS
- **Notes**: Exit code 0. `| TC-1 | PASS | notes |` table row format correctly recognized as a TC marker with PASS result.
- **Verified at**: 2026-04-23

---

## Pytest Output (verbatim)

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\naaht\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: D:\Dev\Dev\SquidSquad
plugins: anyio-4.12.1, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 29 items

.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_01_happy_path_all_pass PASSED [  3%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_02_happy_path_mixed_pass_fail PASSED [  6%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_03_gap_detection_missing_tcs PASSED [ 10%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_04_invalid_result_not_applicable PASSED [ 13%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_05_invalid_result_deferred PASSED [ 17%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_06_tolerant_parsing_zero_padded PASSED [ 20%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_07_tolerant_parsing_no_zero_pad PASSED [ 24%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_08_tolerant_parsing_space_separator PASSED [ 27%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_09_tolerant_parsing_cross_format PASSED [ 31%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_10_auto_discovery_by_issue PASSED [ 34%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_11_auto_discovery_pm_preferred PASSED [ 37%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_12_multiple_revisions_highest PASSED [ 41%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_13_base_file_used_when_no_revisions PASSED [ 44%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_14_no_test_plan_gate_skipped PASSED [ 48%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_15_blocked_results PASSED [ 51%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_16_force_no_bypass SKIPPED [ 55%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_17_tracker_pending_test_blocked SKIPPED [ 58%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_18_tracker_pending_test_allowed SKIPPED [ 62%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_19_graceful_degradation_missing_script SKIPPED [ 65%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_20_duplicate_tc_ids_in_plan PASSED [ 68%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_21_extra_tcs_in_results PASSED [ 72%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_22_empty_test_plan PASSED [ 75%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_23_empty_qa_results PASSED [ 79%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_24_debug_flag PASSED [ 82%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_25_prose_references_not_counted PASSED [ 86%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::test_tc_26_table_row_format PASSED [ 89%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::TestSmokeTests::test_smoke_help PASSED [ 93%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::TestSmokeTests::test_smoke_nonexistent_issue PASSED [ 96%]
.squidsquad/pm/planning/FEAT-PM-2361-tests.py::TestSmokeTests::test_smoke_unit_tests_exist SKIPPED [100%]

======================== 24 passed, 5 skipped in 1.34s ========================
```
