# QA-RESULTS-10442 — PRD-B / Story B3: length floor + code-block parity verifier

**Verified**: 2026-06-01 03:08
**Branch**: `squidsquad/task/10442` @ `321dd146`
**PR**: #10636
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

Single feature commit `321dd146` touches exactly 2 files:
- `references/scripts/assemble_verifier.py` (+83) — adds B3 functions alongside B2's `verify_preservation`
- `tests/test_assemble_verifier.py` (+145) — adds 20 B3 unit tests

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | `check_length_floor(linked, assembled, floor=0.8) -> bool` | Live signature: `check_length_floor(linked, assembled, floor=0.8)`. Covered by `test_length_floor_*` (7 tests) | PASS |
| 2 | `check_code_block_parity(linked, assembled, tolerance=0.1) -> bool` | Live signature: `check_code_block_parity(linked, assembled, tolerance=0.1)`. Covered by `test_code_block_parity_*` (13 tests) | PASS |
| 3 | Both functions in `assemble_verifier.py` alongside `verify_preservation` | Same module; live import + signature confirmed for all 3 functions | PASS |
| 4a | Empty assembled fails floor | `test_length_floor_empty_assembled_with_nonempty_linked_fails` | PASS |
| 4b | Exactly 0.8x passes | `test_length_floor_at_exactly_0_8x_passes` (inclusive boundary) | PASS |
| 4c | 0.79x fails | `test_length_floor_at_0_79x_fails` | PASS |
| 4d | Fenced code block count drops >10% fails | `test_code_block_parity_fenced_drop_just_over_tolerance_fails` (also has `_at_tolerance_passes` boundary) | PASS |
| 4e | Inline backtick count change >10% fails | `test_code_block_parity_inline_drop_just_over_tolerance_fails` + `_inline_spike_just_over_tolerance_fails` | PASS |

## Defense-in-Depth Extras (beyond ACs)

- Cross-counting prevention: `test_code_block_parity_inline_does_not_count_fenced_backticks` — fenced regions are stripped before inline tally, so a code block doesn't double-contribute.
- Custom-threshold pass-through: `test_length_floor_custom_floor_threshold`, `test_code_block_parity_custom_tolerance`.
- Combined dimension: `test_code_block_parity_either_side_failure_fails_combined` — fenced OR inline failure is reportable independently.
- Spike (not just drop) detection: `_spike_over_tolerance_fails` for both fenced + inline — guards against assembled-grew-too-much regressions.
- Language-tag tolerance: `test_code_block_parity_fenced_with_lang_tag_counted` — fences with ```language tags still counted.
- Empty-input behavior: `test_length_floor_empty_linked_empty_assembled_passes` + `_no_blocks_either_side_passes`.

## Test Execution

`pytest tests/test_assemble_verifier.py -v` on `321dd146` (clean worktree) → **40 passed in 0.12s** (20 pre-existing B2 + 20 new B3).

## Outcome

All 4 ACs met with multiple boundary tests per criterion + defense-in-depth extras. Module placement correct (alongside B2 in `assemble_verifier.py`). No LLM dependency. Pure Python. **Transitioning #10442: pending-test → pending-ship.**
