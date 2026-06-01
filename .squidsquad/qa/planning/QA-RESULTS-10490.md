# QA-RESULTS-10490 — PRD-A / Story A2d: Six-slot output emitter

**Verified**: 2026-06-01 04:38
**Branch**: `squidsquad/task/10490` @ `c07a10a0`
**PR**: #10639
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

Single feature commit `c07a10a0`:
- `references/scripts/v2_link_stage.py` (+225) — new module
- `tests/test_v2_link_stage.py` (+290) — 17 tests
- `tests/run_tests.py` (+1) — registration

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | `emit_v2_linked(role_class, l3_domain) -> str` | Live signature: `emit_v2_linked(role_class, l3_domain, *, repo_root=None, l4_path=None)` (kwargs for testability — base contract preserved). `test_emit_v2_linked_returns_string` | PASS |
| 2 | Walks L1-L3 sources, groups by slot, sorts within slot by ordinal | `test_emit_v2_linked_groups_by_slot`, `test_emit_v2_linked_sorts_within_slot_by_ordinal`, plus L3 routing tests: `test_emit_v2_linked_includes_l3_domain_files`, `test_emit_v2_linked_excludes_other_l3_domain_files`, `test_emit_v2_linked_l3_none_excludes_all_l3_files` | PASS |
| 3 | Applies A2c L4 op processing per slot | `test_emit_v2_linked_applies_l4_replace_step_op`, `test_emit_v2_linked_missing_l4_is_noop` | PASS |
| 4 | Exactly six H2 sections in canonical order | `test_emit_v2_linked_emits_exactly_six_h2_sections_in_canonical_order`, `test_canonical_slot_order_is_six`, `test_canonical_slot_order_matches_trd`, `test_emit_v2_linked_emits_empty_section_for_absent_slot` (slot invariant holds even when no content for a slot) | PASS |
| 5 | Byte-stable output across re-runs | `test_emit_v2_linked_byte_stable_across_runs`. Stable sort key includes posix_path tiebreaker per skill's design (deterministic ordering across filesystems) | PASS |
| 6 | Minimal fixture compose → expected | Fixture-driven harness underlies the slot/ordering/L4 tests above | PASS |

## Defense-in-Depth Extras

- `test_emit_v2_linked_skips_files_without_frontmatter` — backward-compatible handling for pre-#10394 files lacking frontmatter.
- `test_emit_v2_linked_respects_roles_extras_filter` — `roles: extras` frontmatter filtering honored.
- `test_strip_frontmatter_removes_block`, `test_strip_frontmatter_no_op_when_absent` — helper unit tests for the frontmatter strip primitive.

## Test Execution

`pytest tests/test_v2_link_stage.py -q` on `c07a10a0` → **17 passed in 0.21s**.

## Outcome

All 6 ACs covered with multiple tests per criterion + defense-in-depth (graceful pre-frontmatter file handling, roles:extras filtering, helper unit tests). Byte-stable design with explicit posix-path tiebreaker is the right call for cross-platform determinism. **Transitioning #10490: pending-test → pending-ship.**
