# QA-RESULTS-10387 — PRD-A / Story A3: byte-stability golden-file test suite

**Verified**: 2026-06-01 09:38
**Branch**: `squidsquad/task/10387` @ `da600253`
**PR**: #10647
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

Feature commit `da600253`: two fixture installs under `tests/compose-fixtures/` + golden files + test runner + STATIC_TEST_MODULES registration.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | Fixture covering pm (no L3) + worker-fe (with L3) + all 4 L4 op types | Both fixture trees present (`tests/compose-fixtures/pm/` + `tests/compose-fixtures/worker-fe/`); `test_fixture_l4_uses_all_four_op_types` parametrized × 2 explicitly asserts replace/insert-before/insert-after/append present | PASS |
| 2 | Golden output committed alongside fixture | `CLAUDE.linked.golden.md` present in each fixture root | PASS |
| 3 | Test runner: diff against golden, fail on byte difference | `test_fixture_emit_matches_committed_golden` parametrized × 2 emits via `v2_link_stage.emit_v2_linked`, diffs against `CLAUDE.linked.golden.md`, fails with unified-diff message on any difference | PASS |
| 4 | Tests reachable via existing project test entry point | `test_a3_golden_link_stage` registered in `tests/run_tests.py` STATIC_TEST_MODULES; also runs via pytest direct | PASS |
| 5 | Negative: corrupted L4 op → compose aborts | `test_corrupted_l4_aborts_with_parse_error` (L4ParseError raised) + `test_corrupted_l4_does_not_silently_match_golden` (belt-and-braces: even if parse somehow returns, output != golden) | PASS |
| 6 | CI hook integration out of scope (PRD-E) | Acknowledged; not implemented here | PASS (as specified) |

## Defense-in-Depth

- Structural integrity guards: `test_fixture_pm_has_no_l3_subtree` + `test_fixture_worker_fe_has_l3_subtree` — ensures the test corpus actually exercises the L3 vs no-L3 coverage matrix.
- Belt-and-braces negative test (`test_corrupted_l4_does_not_silently_match_golden`) — even if a future regression makes L4ParseError swallowed, the broken-L4 output would still diverge from golden.
- Cross-platform line-ending safety: per skill comment, golden read uses Python universal newlines.

## Test Execution

`pytest tests/test_a3_golden_link_stage.py -q` on `da600253` → **8 passed in 0.19s**.

## Outcome

All 6 ACs covered with explicit tests per criterion + defense-in-depth structural guards + cross-platform safety. The golden-file harness is now in place for v2 link-stage regressions; future composer changes that drift output will fail loudly. **Transitioning #10387: pending-test → pending-ship.**
