# QA-RESULTS-10447 — PRD-B / Story B7: assemble atomic emit + abort semantics

**Verified**: 2026-06-01 08:38 (re-verification after cycle 517 route-back)
**Branch**: `squidsquad/task/10447` @ `52db7886` (was `917544f8` in cycle 517)
**PR**: #10645
**Verifier**: qa-lead
**Result**: **PASS**

## Context

Cycle 517 routed to in-progress on AC2/AC4 cache_corruption gap. Skill addressed in commit `52db7886`:
- Added `cache_lookup_fn` + `cache_store_fn` injection seams to `assemble_and_emit` (default `None` = cache-disabled, existing callers unchanged).
- Extracted `_assemble_one_slot` helper implementing full §4.6 cache flow:
  - cache-hit + valid → use cached (no LLM call)
  - cache-hit + corrupt → retry LLM once
  - retry succeeds → use retry body + write-through to cache
  - retry also fails → raise `CacheCorruption`
  - cache-miss → run LLM fresh, raise per-mode exception on verification fail with NO retry (fresh fail is not corruption)
- 8 new tests covering all paths.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | Atomic write via `.tmp` + rename | `test_success_no_tmp_files_remain` + `test_write_failure_unlinks_tmp_files_and_raises` | PASS |
| 2 | Failure modes per TRD §4.6 (all 7) | All 7 now covered (cache_corruption was the gap; now implemented) | **PASS** |
| 3 | On abort: prior triple untouched, zero partial artifacts | 6 abort-path tests + `test_cache_corruption_retry_also_fails_raises_cache_corruption` explicitly checks zero partial artifacts | PASS |
| 4 | Unit tests for each failure path (stubbed) | 18 original + 8 cache tests = 26 stubbed tests covering all paths | **PASS** |

### Failure-Mode Coverage Map (now complete)

| Mode | Test | Status |
|---|---|---|
| LLM error → abort | `test_llm_error_aborts_and_writes_nothing` | PASS |
| Preservation fail (B2) → abort | `test_preservation_fail_aborts_and_writes_nothing` | PASS |
| Floor/parity fail (B3) → abort | `test_length_floor_fail_aborts` + `test_code_block_parity_fail_aborts` | PASS |
| Cache corruption → re-run LLM once then abort | `test_cache_corruption_triggers_one_retry_and_succeeds` + `test_cache_corruption_retry_also_fails_raises_cache_corruption` + `test_cache_corruption_retry_succeeds_stores_new_body` | PASS |
| Conflict-report-write fail → abort | `test_conflict_report_write_failure_raises_specific_subclass` | PASS |
| Precedence violation → abort | `test_precedence_violation_aborts` | PASS |
| Link-stage fail → no assemble attempted | `test_link_stage_fail_aborts_without_dispatching_llm` | PASS |

### Cache Flow Tests (new)

- `test_cache_hit_with_valid_body_skips_llm` — happy-path cache hit avoids LLM call.
- `test_cache_corruption_triggers_one_retry_and_succeeds` — corrupt hit triggers exactly one retry per slot (no double-retries).
- `test_cache_corruption_retry_also_fails_raises_cache_corruption` — retry also fails → `CacheCorruption` raised, no partial artifacts.
- `test_cache_corruption_retry_succeeds_stores_new_body` — write-through after recovery.
- `test_cache_miss_runs_llm_and_stores_on_success` — miss → fresh LLM → cache store.
- `test_cache_miss_with_fresh_failure_does_not_retry` — fresh failures don't retry (only corruption does).
- `test_cache_lookup_exception_is_treated_as_miss` — robustness.
- `test_cache_store_failure_does_not_abort_run` — store failures are non-fatal.

## Defense-in-Depth

- Distinction between "cache corruption" (retry once) and "fresh failure" (no retry) is the right semantics — preserves the "retry-once" contract without infinite loops on genuinely broken prompts.
- `cache_lookup_fn` exception treated as miss → cache provider failures don't propagate.
- `cache_store_fn` failures swallowed → write-through failures don't abort otherwise-successful runs.

## Test Execution

`pytest tests/test_atomic_emit_b7.py -q` on `52db7886` → **26 passed in 0.16s**.

## Notable Skill Note

Skill's comment: _"Lesson re-applied: don't defer ACs to downstream layers (same shape as the B1 AC5 deferral QA caught earlier)."_ — The dev process is internalizing the AC-completeness pattern from the prior cycle 513/514 route-back.

## Outcome

All 4 ACs now met. All 7 §4.6 failure modes covered with stubbed tests. Cache-corruption retry-once semantics correctly distinguished from fresh-failure handling. **Transitioning #10447: pending-test → pending-ship.**
