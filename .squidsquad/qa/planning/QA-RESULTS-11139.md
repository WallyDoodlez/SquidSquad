# QA-RESULTS-11139 — Strip L4-op-syntax H3 headers from L1-L3 source bodies

**Verified at**: 2026-06-05 cycle 947
**PR**: #11141 (squidsquad/task/11139 @ HEAD)

## Verification

- **Root cause correction noted**: issue body assumed L4 op-application machinery was preserving the headers; skill bisected to a different source — the headers leak from L1-L3 source files (authoring convention) through `v2_link_stage._join_bodies`. Fix strips them at link time; L4 ops parsed from `.squidsquad/project/<role>.md` are applied AFTER join and unaffected. Verified by the regression test `test_l4_append_op_body_still_flows_into_composite`.
- **`compose.py deploy-all`** succeeds. Size deltas vs main: dm 1006→998 (-8), pm 1066→1054 (-12), qa 1008→1000 (-8), skill 1268→1256 (-12). Matches skill's claim exactly.
- **AC — zero `^### (append|insert-after|insert-before|replace)\b` matches in any composed CLAUDE.md** — PASS. Manual grep across all 4 role composites returns 0 leaked headers.
- **Regression test `tests/test_l4_op_header_strip_11139.py`** — **13/13 PASS in 0.44s**:
  - `test_no_op_type_headers_in_composed_claude_md` × 4 roles ✓
  - `test_no_op_type_headers_in_linked_intermediate` × 4 roles ✓ (covers `.linked.md` too, not just final)
  - `test_l4_append_op_body_still_flows_into_composite` ✓ — positive test confirming the body content survives the header strip
  - `test_strip_helper_is_idempotent` ✓
  - `test_strip_helper_removes_append_with_trailing_blank` ✓
  - `test_strip_helper_removes_insert_after_step` ✓
  - `test_strip_helper_preserves_non_op_h3_headings` ✓ — negative test confirming non-op H3s aren't over-stripped
- **Wider regression sweep** (15 suites: `test_l4* + test_compose* + test_a3_golden_link_stage + test_d2_link_stage_references + test_link_stage_validator + test_v2_link_stage + test_manifest + test_installer_wiring + test_catalog* + test_event_mode_fragments`) → **825/825 PASS in 7.39s**.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Strong test coverage — positive, negative, idempotency, both `.md` and `.linked.md`. Independent of #11138 (#11137); stacks additively per skill's note.
