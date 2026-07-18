# QA-RESULTS-13661

## Summary
VERIFIED — PASS. All 5 ACs confirmed. Fourth instance of the #13555/#13602/#13660 silent-truncation class, this one also live-active. Fixed on `references/scripts/cycle_pre.py` (PR #13663, `squidsquad/task/13661`).

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | Live ground truth: `gh issue list --state open --limit 1000` (no label filter) → **151**. Ran the real (unmocked) `cycle_pre._gh_fetch(None, "open", with_body=True, limit=500)` on the branch → **151** — exact match. Also ran the real pending-ship query → 0 (correct, nothing pending-ship right now; no crash under the raised limit) |
| AC2 | PASS | Diff: the `WARNING` block sits inside `_gh_fetch()` itself, after the shared `items = ...` assignment, before caching — applies to every call regardless of the `limit` argument passed |
| AC3 | PASS | `TestGhFetchCapWarning13661::test_no_warning_under_limit` / `test_no_warning_on_empty_result` — confirmed no false-positive warnings |
| AC4 | PASS | `test_source_no_longer_hardcodes_limit_50` (source-text guard) + independently `grep`ed the PR diff myself: all three call sites now read `limit=500` |
| AC5 | PASS | `tests/test_13661_gh_fetch_limit_truncation.py` + `tests/test_cycle_pre.py` — 150/150 pass. Canonical static gate independently re-run on the branch: **5722/5722 PASS, 0 failures**. `comprehension_staleness.py check` — exit 0 |

## Zero-gap check
No gaps.

## Verdict
PASS → pending-ship.
