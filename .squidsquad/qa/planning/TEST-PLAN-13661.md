# TEST-PLAN-13661

Derived independently from the issue body (`ISSUE: cycle_pre.py _gh_fetch() external-triage/pending-ship calls share the #13555/#13660 gh --limit 50 truncation class`). Filed by skill-lead during #13660's implementation — fourth instance of the silent-truncation class, this one also live-active (external-triage fetch silently missing ~100 of 151 open issues).

## ACs derived from the issue

- **AC1**: The three `limit=50` call sites in `cycle_pre.py` (external-triage fetch + 2 pending-ship fetches) are raised to a non-truncating limit — live-verify against the real current open-issue count.
- **AC2**: The cap-hit warning is centralized *inside* `_gh_fetch()` itself (not per-call-site), so every caller — including the pre-existing `limit=200` sites — gets the self-diagnosing behavior for free (per the issue's suggested fix (b), a stronger design than #13555/#13602/#13660's per-call-site warnings).
- **AC3**: No warning fires under normal (non-capped) results.
- **AC4**: Source no longer contains any hardcoded `limit=50` call in `cycle_pre.py`.
- **AC5**: No regressions — new + updated regression tests pass; full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | Ground truth: `gh issue list --state open --limit 1000 --json number` → count (151, no label filter — matches `_gh_fetch(None, "open", ...)`'s unfiltered call). Ran the real unmocked `cycle_pre._gh_fetch(None, "open", with_body=True, limit=500)` on the branch → 151 — exact match |
| TC2 | AC1 (live) | Ran the real unmocked pending-ship query `_gh_fetch("squidsquad,status:pending-ship", "open", with_comments=True, limit=500)` → 0 (correct — nothing pending-ship right now, well under cap, no crash) |
| TC3 | AC2/AC3 | `tests/test_13661_gh_fetch_limit_truncation.py` (7 cases) incl. `test_warning_fires_for_any_limit_value` confirming the warning isn't special-cased to 500 |
| TC4 | AC4 | `test_source_no_longer_hardcodes_limit_50` — source-text regression guard; independently `grep`ed the diff myself to confirm |
| TC5 | AC5 | `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |

## Note
Confirms the architectural fact noted in #13660's own filing: `cycle_pre.py`'s `_gh_fetch(None, "open", with_body=True)` — not `tracker.list_all_open()` — is the actual code path feeding `external_issues` into cycle-input.json for PM's triage-external step.
