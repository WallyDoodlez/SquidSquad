# QA-RESULTS-10447 — PRD-B / Story B7: assemble atomic emit + abort semantics

**Verified**: 2026-06-01 08:08
**Branch**: `squidsquad/task/10447` @ `917544f8`
**PR**: #10645
**Verifier**: qa-lead
**Result**: **FAIL — AC2/AC4 cache_corruption gap; routing back to in-progress**

## Scope Check

Single feature commit `917544f8`:
- `references/scripts/atomic_emit.py` (new, ~250 lines) — `assemble_and_emit()` orchestrator + exception hierarchy
- `tests/test_atomic_emit_b7.py` (new) — 18 tests
- `tests/run_tests.py` (+1)

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | Atomic write via `.tmp` + rename for all three artifacts | Module docstring + `test_success_no_tmp_files_remain` + `test_write_failure_unlinks_tmp_files_and_raises` (failure-path cleanup) | PASS |
| 2 | Failure modes per TRD §4.6 table | 6 of 7 modes covered; **cache_corruption gap** — see below | **FAIL** |
| 3 | On any abort: prior triple untouched, zero partial artifacts | `test_write_failure_unlinks_tmp_files_and_raises` + 6 abort-path tests each implicitly verifies no output written | PASS |
| 4 | Unit tests for each failure path (stubbed) | 6 of 7 failure paths tested; **no cache_corruption test** | **FAIL** |

### AC2 Failure-Mode Coverage Map

| Mode | Test | Status |
|---|---|---|
| LLM error → abort | `test_llm_error_aborts_and_writes_nothing` | PASS |
| Preservation fail (B2) → abort | `test_preservation_fail_aborts_and_writes_nothing` | PASS |
| Floor/parity fail (B3) → abort | `test_length_floor_fail_aborts` + `test_code_block_parity_fail_aborts` | PASS |
| **Cache corruption → re-run LLM once then abort** | **NONE** | **GAP** |
| Conflict-report-write fail → abort | `test_conflict_report_write_failure_raises_specific_subclass` | PASS |
| Precedence violation → abort | `test_precedence_violation_aborts` | PASS |
| Link-stage fail → no assemble attempted | `test_link_stage_fail_aborts_without_dispatching_llm` | PASS |

## Gap Analysis

The AC2 text reads: **"cache corruption → re-run LLM once then abort"**. This has two components:
1. Detect cache corruption (cached body failed preservation).
2. Re-run LLM once; if that also fails, abort with `CacheCorruption`.

Skill's comment defers this: "CacheCorruption retry deferred to B6-integration caller (declared, documented)."

Concrete observations:
- The `CacheCorruption` exception class IS declared (line 78-79 of `atomic_emit.py`).
- The module docstring (line 14) reads "Cache corruption → :class:`CacheCorruption` (after one LLM retry)" — semantically claims the retry-once is part of the contract.
- BUT the `assemble_and_emit()` injection-seam signature is `(assemble_slot_fn, parse_output_fn, resolve_fn, emit_report_fn)`. There is **no cache_lookup_fn seam**. The retry-once loop is therefore not implementable through atomic_emit's current API.
- No test exercises the `CacheCorruption` path even via a stubbed fixture.

Per [[feedback_no_ship_with_gaps]] (any QA gap = back to dev, not "noted for follow-up") and AC4 ("unit tests for each failure path"), the missing failure-mode coverage is a fail.

## Suggested Remediation Paths (dev's choice)

1. **Add cache awareness to atomic_emit**: extend the orchestrator with `cache_lookup_fn` + `cache_store_fn` injection seams (defaulting to no-ops). Implement the retry-once loop: on B2 preservation fail of a cached body, mark cache invalid, re-run `assemble_slot_fn`, re-check; if second pass also fails, raise `CacheCorruption`. Add a stubbed test that injects "first call returns bad cached body, second call returns good body" and verifies success; and a test where both fail → `CacheCorruption` raised.
2. **PM scope-shift in issue body**: amend the AC2 list to remove the cache_corruption mode (or move it to a B8/B9 issue body) and re-route pending-test. Make the deferral visible at the AC level, not just in a worker comment.

## Defense-in-Depth (pre-existing, holds)

- 5 success-path tests covering atomicity, file contents, six H2 invariant, verbatim slot pass-through.
- 6 failure-path tests covering aborts + zero-partial-artifact contract.
- `test_aggregates_conflicts_from_multiple_slots` — multi-slot conflict aggregation.
- 3 `test_split_linked_*` tests — canonical-slot-keys parsing helper.

## Test Execution

`pytest tests/test_atomic_emit_b7.py -q` on `917544f8` → **18 passed in 0.12s** (covers all that's implemented; the AC2 cache_corruption mode has no test because the orchestration isn't implemented).

## Outcome

AC1, AC3 PASS. AC2 has 6/7 failure modes covered. AC4 lacks the cache_corruption test (because the orchestration is missing). Routing **#10447: pending-test → in-progress** for AC2/AC4 remediation.
