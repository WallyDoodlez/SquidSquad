# TEST-PLAN-13564

Derived independently from `.squidsquad/pm/planning/CONTEXT-13564.md` (authoritative scope) + issue body ACs. First task this session where PM's #13666 fix (CONTEXT.md push-before-approval) visibly worked in production — PM's own Discussion comment noted it explicitly.

## ACs (from CONTEXT-13564.md + issue body)

- **AC1**: Labels appear as bare string arrays in `_gh_fetch`'s output — no id/color/description fields remain.
- **AC2**: `_item_label_names` (confirmed the sole consumer via grep, per the CONTEXT's required Side Effect Mitigation) correctly resolves from the new bare-string shape — role/status routing must not break.
- **AC3**: Comment bodies capped at ~500 chars with an explicit truncation suffix; short bodies unaffected.
- **AC4**: Issue count/ordering unchanged.
- **AC5**: Before/after size measurement reported in the PR — verify independently, live, not just trust the PR's own number.
- **AC6**: No agent-behavior regression — existing transition/pickup-logic tests pass.
- **AC7**: No regressions — new tests pass, full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC2 (live) | Called the real `cycle_pre._gh_fetch('squidsquad', 'open', with_comments=True, limit=500)` against real live GitHub data (150 open issues) — confirmed every label is a bare string, `_item_label_names`/`_item_has_role` resolve correctly against the live shape |
| TC2 | AC5 (live, independent — found a measurement-methodology gap in my own first attempt) | First measured `_gh_fetch()`'s raw return directly: 204,537 bytes — far above the PR's claimed 58KB "after," a real discrepancy. Traced the cause by reading the actual call chain: comment-body capping happens in the pre-existing `_enrich_inline()` (not touched by this diff except for widening its cap), called on the FINAL filtered subsets (pending-test/approved/human-blocked/etc.) — not on `_gh_fetch()`'s raw return. Called the real end-to-end `cycle_pre._build_pm_input('pm')` (the actual function PM's cycle wrapper runs) — final assembled payload: **8,710 bytes (8.5 KB)**, well under the CONTEXT's own <15KB target and the issue's original 29KB baseline. Sanity-checked: no raw `comments` field survives in any item across the whole payload |
| TC3 | AC3 | `tests/test_13564_cycle_input_diet.py::TestCommentBodyCapped13564` (6 cases) |
| TC4 | AC4 | `test_item_order_and_count_unchanged` |
| TC5 | AC6/AC7 | `tests/test_cycle_pre.py` (143 cases, incl. 11 fixtures updated to the new label contract) + `tests/test_13564_cycle_input_diet.py` (12 cases). `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` — clean, no CQ spec needed (pure deterministic-code + data-shape change, consistent with CONTEXT-13564.md's own framing) |

## Note
TC2's discrepancy was a genuine finding worth documenting: my first (flawed) measurement point undersold the fix's real impact by measuring too early in the pipeline. The real, fully-assembled cycle-input.json is even smaller than either number suggested — the fix works, and works better than either raw comparison implied in isolation.
