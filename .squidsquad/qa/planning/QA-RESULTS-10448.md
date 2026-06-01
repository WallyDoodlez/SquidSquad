# QA-RESULTS-10448 — PRD-B / Story B8: assemble golden-file regression tests

**Verified**: 2026-06-01 10:38
**Branch**: `squidsquad/task/10448` @ `034bbbb1`
**PR**: #10648
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

New fixture `tests/compose-fixtures/assemble-contradiction/` with L4 contradiction (L2 "PM coordinates the team" vs L4 "PM does NOT coordinate; verifier coordinates") + 3 goldens (CLAUDE.md, CLAUDE.linked.md, CLAUDE.conflicts.md) + 7-test runner + STATIC_TEST_MODULES registration.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | Fixture with L4 contradiction + golden `CLAUDE.conflicts.md` | Fixture tree present; `CLAUDE.conflicts.md.golden` committed; `test_fixture_has_l4_contradiction_in_responsibility` asserts the structural contradiction is in place | PASS |
| 2 | Suite asserts assembled `CLAUDE.md` matches golden | `test_assembled_claude_md_matches_golden` byte-diff against `CLAUDE.md.golden` | PASS |
| 3 | Suite asserts cache hit on second run (no LLM invocation) | `test_cache_hit_on_second_run_skips_llm` (counts LLM calls = 0 on second pass) + `test_cache_hit_second_run_writes_byte_identical_artifacts` | PASS |
| 4 | Negative test: corrupt a fixture mid-test → suite catches | `test_corrupt_fixture_triggers_preservation_fail` — corrupts a fixture file at runtime and confirms B2 PreservationFail raises (zero partial artifacts contract honored) | PASS |

## Defense-in-Depth

- `test_assembled_claude_conflicts_md_matches_golden` — golden coverage for conflicts file too (AC1 only required a conflicts golden exist, not a matches-golden test).
- `test_conflict_report_names_the_l4_contradiction` — semantic check that L4 was named the winner in the report.
- Cache-hit test counts LLM calls explicitly (not just byte equality) — verifies the actual cache mechanism, not just deterministic stub output.
- Deterministic stub LLM hand-crafted so all 4 non-verbatim slot outputs satisfy B2 preservation + B3 floor/parity + B5 loser-quote-absent — the test exercise touches every preservation gate.

## Test Execution

`pytest tests/test_b8_golden_assemble.py -q` on `034bbbb1` → **7 passed in 0.17s**.

## Outcome

All 4 ACs covered + the assemble pipeline's three §4.6 artifacts (CLAUDE.md, CLAUDE.linked.md, CLAUDE.conflicts.md) all have goldens. The cache-hit test verifies the actual cache mechanism by call-counting, not just deterministic output equality — meaningful regression coverage. **Transitioning #10448: pending-test → pending-ship.**
