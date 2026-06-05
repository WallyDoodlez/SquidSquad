# QA-RESULTS-11066 — test_corrupted_l4_aborts_with_parse_error stale post-#10987

**Verified at**: 2026-06-05 cycle 916
**PR**: #11068 (squidsquad/skill/11066-fix-stale-l4-corrupt-test @ HEAD)
**Scope**: Single-file fixture update in `tests/test_a3_golden_link_stage.py`.

## What changed

The test asserted `L4ParseError` on a non-op-like H3 fixture (`### frobnicate step:cycle/work`), but #10987's prose-H3 path now routes such headings into implicit append silently. Skill picked resolution option B from the issue body: replace the fixture with `### replace garbage` — an *op-like-but-malformed* heading that still trips `_parse_h3_op → L4ParseError`. The sibling test (`test_corrupted_l4_does_not_silently_match_golden`) intentionally keeps the `frobnicate` fixture because it asserts byte-stability through the post-#10987 prose-append path.

## Verification

- `python -m pytest tests/test_a3_golden_link_stage.py -v` → **8/8 PASS in 0.15s** (matches skill's claim).
  - `test_corrupted_l4_aborts_with_parse_error` PASS (previously the lone failure on this suite).
  - `test_corrupted_l4_does_not_silently_match_golden` PASS (still uses `frobnicate`, covers the prose-append path).
- Diff confirmed: only `tests/test_a3_golden_link_stage.py` modified (+13 / -5). Test intent preserved via docstring update referencing #11066 and the `_OP_LIKE_RE` vs `_OP_RE` distinction.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

Minimal, well-explained fix; full suite green; both corruption tests now exercise complementary post-#10987 paths.
