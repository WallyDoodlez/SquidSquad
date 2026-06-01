# QA-RESULTS-10491 — PRD-A / Story A2e: 7 link-stage validation rules R1-R7

**Verified**: 2026-06-01 05:08
**Branch**: `squidsquad/task/10491` @ `b18aa37b`
**PR**: #10640
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

Single feature commit `b18aa37b`:
- `references/scripts/link_stage_validator.py` (+202) — `validate_link_stage(l4_doc, sources, *, l4_path) -> None` raising `LinkStageValidationError` on first violation.
- `tests/test_link_stage_validator.py` (+269) — 24 tests.
- `tests/run_tests.py` (+1).

## Acceptance Criteria

| Rule | Negative test | Positive boundary | Status |
|---|---|---|---|
| R1 (L4 `## Vault` H2 → abort) | `test_r1_l4_with_vault_h2_aborts` | `test_r1_l4_without_vault_h2_passes` | PASS |
| R2 (L2/L3 `slot: vault` → abort) | `test_r2_l2_source_with_vault_slot_aborts` + `test_r2_l3_source_with_vault_slot_aborts` | `test_r2_l1_source_with_vault_slot_passes` (L1 allowed) | PASS |
| R3 (any L1-L3 `slot: project-context` → abort) | `test_r3_any_l1_l3_source_with_project_context_slot_aborts` parametrized × 3 (L1/L2/L3) | — (rule is unconditional) | PASS |
| R4 (Instructions `append` without sub-skill ref → abort) | `test_r4_instructions_append_without_sub_skill_ref_aborts` | `test_r4_instructions_append_with_sub_skill_ref_passes` + `test_r4_append_under_other_slot_does_not_require_sub_skill_ref` | PASS |
| R5 (unknown step-id → abort named) | `test_r5_unknown_step_id_aborts_and_names_it` | `test_r5_known_step_id_passes` + `test_r5_targetless_op_does_not_trigger` | PASS |
| R6 (whole-slot replace + other op → abort) | `test_r6_whole_slot_replace_with_another_op_in_same_slot_aborts` | `test_r6_solo_whole_slot_replace_passes` + `test_r6_scope_is_per_slot_not_per_file` | PASS |
| R7 (duplicate replace target → abort) | `test_r7_duplicate_replace_target_aborts` | `test_r7_disjoint_replace_targets_pass` + `test_r7_replace_plus_insert_before_same_target_is_legal` | PASS |

| Other AC | Evidence | Status |
|---|---|---|
| Diagnostic names rule + file/step-id | Exception `.rule`, `.file_path`, `.step_id` attrs; R5 test names the offending step-id in the diagnostic | PASS |
| All rules run BEFORE any disk write | Validator is pure (no I/O imports beyond stdlib regex/dataclass); `validate_link_stage(...) -> None` is called pre-emit per design. Intrinsic guarantee since the function performs no writes. | PASS |
| Declaration order R1→R7 | `test_validation_runs_rules_in_declaration_order_r1_first` | PASS |
| Unit test per rule (negative fixture) | 7 negative tests above + multiple positive boundaries | PASS |

## Defense-in-Depth Extras

- `test_empty_l4_and_clean_sources_passes` — clean-input no-op identity.
- `test_validates_against_l4doc_parsed_from_text` + `test_validates_l4_append_without_sub_skill_ref_via_parser` — integration with A2b parser at the actual entry-point shape.
- R2/R3/R4 boundary positives (L1 vault allowed, append outside Instructions allowed, sub-skill ref under Instructions allowed) — guards against over-aborting.

## Test Execution

`pytest tests/test_link_stage_validator.py -q` on `b18aa37b` → **24 passed in 0.07s**.

## Outcome

All 7 rules covered with paired negative+positive tests + diagnostic shape + declaration-order invariant + parser-integration tests. Pre-write contract intrinsic to pure-function design. **Transitioning #10491: pending-test → pending-ship.**
