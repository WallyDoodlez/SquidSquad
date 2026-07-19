# QA-RESULTS-13737

## Summary
PASS -> Pending Ship. My own filed finding, verified to the same bar as any other item. The fix restores the "never bypassed" TC-coverage ship-integrity gate to actual function after ~2 months of silent inertness. Confirmed not just that discovery works, but that the gate genuinely computes and enforces coverage now.

## AC Walk
| AC | Result | Evidence |
|----|--------|----------|
| AC1 (current-convention discovery) | PASS (live) | `_discover_files(13735)` and `_discover_files(13731)` both resolve to real, existing files — previously `(None, None)` for both. |
| AC2 (legacy fallback preserved) | PASS (live) | Constructed a disposable legacy-shaped file pair (`FEAT-PM-88888-TEST-PLAN.md`); `_discover_files()` still resolves it correctly. |
| AC3 (qa/verifier dir preferred) | PASS | Confirmed in the diff — sort key now prefers `qa` over `pm`, matching #9184 ownership. |
| AC4 (gate genuinely computes coverage, not just discovers) | PASS (live, the real gate) | Ran `check_coverage()` directly against real `TEST-PLAN-13735.md`/`QA-RESULTS-13735.md` (predates #13738's TC-results-table fix): correctly reports `0/5 coverage`, exit code 1 — proves the gate does real work now, not a silent pass. |
| AC5 (new hybrid format achieves full coverage) | PASS (live) | Synthetic TEST-PLAN + QA-RESULTS pair using the #13738 hybrid format (AC-Walk + TC-results table): `2/2 (100%)`, exit code 0. |
| AC6 (regression tests) | PASS | `tests/test_tc_coverage.py` — 48/48 PASS, including 5 new tests. |

## TC Results
| TC | Result |
|----|--------|
| TC1 | PASS |
| TC2 | PASS |
| TC3 | PASS |
| TC4 | PASS |
| TC5 | PASS |
| TC6 | PASS |
| TC7 | PASS |

## Sanity checks
- Full static gate: 5892/5892 PASS, matching skill's own reported number exactly.
- This very transition (pending-test -> pending-ship) is the first one genuinely enforced by the restored gate — it correctly blocked on first attempt (missing QA-RESULTS at the time), confirming the fix works end-to-end on live tracker.py usage, not just in isolated function calls.

## Zero-gap check
0 gaps.

## Verdict
PASS -> Pending Ship. PR #13740 merged (commit 470d9cde).
