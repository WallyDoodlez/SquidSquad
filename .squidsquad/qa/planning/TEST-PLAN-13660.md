# TEST-PLAN-13660

Derived independently from the issue body (`ISSUE: tracker.py list_issues/list_by_labels/list_all_open silently truncate open-issue results at gh --limit 50`). Filed by pm-lead — third instance of the #13555/#13602 silent-truncation class, this one live-active (150+ open issues, 50-cap hides ~100 of them).

## ACs derived from the issue

- **AC1**: `list_all_open()` returns the real full open-issue set (up to the new cap), not silently capped at 50 — live-verify against the actual current open-issue count.
- **AC2**: `list_issues()` and `list_by_labels()` also raised to the same shared limit (currently latent, but fixed alongside for consistency).
- **AC3**: A cap-hit WARNING fires (self-diagnosing) when a result count equals the limit, so a future truncation is visible rather than silent — per the #13555 precedent.
- **AC4**: No warning fires under normal (non-capped) results.
- **AC5**: `work_queue()` is genuinely untouched — the issue explicitly declares it out of scope (already `--limit 100`, per-role filtered).
- **AC6**: No regressions — new + updated regression tests pass; full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | Ground truth: `gh issue list --label squidsquad --state open --limit 1000 --json number` → count. Then run the real `tracker.list_all_open()` on the fix branch and compare counts directly — not mocked |
| TC2 | AC2/AC6 | `tests/test_13660_list_limit_truncation.py` (17 cases) + `tests/test_tracker.py` (updated) — 87/87 pass |
| TC3 | AC3/AC4 | `TestWarnIfCapped` cases in the new test file — mocked, but the underlying `_warn_if_capped()` logic is a pure function, low-risk to trust from unit coverage alone (no external-tool call, unlike #13654) |
| TC4 | AC5 | Read `work_queue()` directly on the branch — confirmed still `--limit 100`, unmodified |
| TC5 | AC6 | `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |

## Note
#13661 (sibling `cycle_pre.py` instance) correctly declared out of scope by skill and filed separately — not part of this verification.
