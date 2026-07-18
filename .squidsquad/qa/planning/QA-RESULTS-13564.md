# QA-RESULTS-13564

## Summary
VERIFIED — PASS. All 7 ACs confirmed. Fixed on `references/scripts/cycle_pre.py` (PR #13690, `squidsquad/task/13564`). This task's own planning artifact (`CONTEXT-13564.md`) landed on `main` before approval — the first live confirmation this session that #13666's own fix (which I verified earlier) works as designed in production.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | Live call to real `_gh_fetch('squidsquad', 'open', with_comments=True, limit=500)` against 150 real open issues: every `labels` entry confirmed a bare string |
| AC2 | PASS | Live: `_item_label_names`/`_item_has_role` resolve correctly from the bare-string shape against real data |
| AC3 | PASS | `TestCommentBodyCapped13564` — 6/6 pass (short unaffected, exact-boundary, truncation+suffix, both bulk and legacy paths) |
| AC4 | PASS | `test_item_order_and_count_unchanged` |
| AC5 | PASS (independently verified, discrepancy resolved) | Initial direct `_gh_fetch()` measurement (204,537 bytes) didn't match the PR's claimed 58KB — investigated and found the cap/drop step happens in the pre-existing `_enrich_inline()`, applied to the *filtered* subsets, not `_gh_fetch()`'s raw return. Called the real `_build_pm_input('pm')` end-to-end: final assembled payload **8,710 bytes (8.5 KB)** — well under the CONTEXT's <15KB target, no raw `comments` field leaked anywhere in the output |
| AC6 | PASS | `tests/test_cycle_pre.py` — 143/143 pass (11 fixtures correctly updated to the new label contract) |
| AC7 | PASS | `tests/test_13564_cycle_input_diet.py` — 12/12 pass. Canonical static gate independently re-run on the branch: **5790/5790 PASS, 0 failures**. `comprehension_staleness.py check` — exit 0 (correctly no CQ spec — pure code/data-shape change) |

## Zero-gap check
No gaps. My own first size measurement was methodologically premature (measured before the enrichment stage) — traced to root cause and corrected with the real end-to-end measurement rather than accepting the discrepancy or the PR's number at face value.

## Note (unrelated, surfaced during investigation)
While measuring raw `gh issue list` output for this verification, discovered #13691 (a live, `in-progress`, skill-owned issue: single-commit-PR squash-merge uses the commit message, not the neutralized PR body — a distinct bypass variant of #13654/#13683's closing-keyword class, reportedly affecting my own #13683 shipment). Not my task to act on now (still in-progress, not assigned to me) — noted for full-attention verification when it reaches pending-test.

## Verdict
PASS → pending-ship.
