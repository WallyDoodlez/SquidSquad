# TEST-PLAN-13555 — EAD issue-poll --limit 50 silent truncation

**Source**: GitHub issue #13555 body (Observation + Suggested fix (a)+(c)) + skill's Discussion comment confirming the implemented scope.
**Derived without reading the diff.**

## Acceptance Criteria (derived from issue body)

- **AC1**: `ExternalActivityDetector.ISSUE_POLL_LIMIT` raised from 50 to (at least) 500, matching the pre-existing `_emitted_issues` 500-entry dedup eviction cap referenced in the issue as the internal-inconsistency signal.
- **AC2**: The `gh issue list ... --limit <N>` subprocess call actually uses the new limit (not still hard-coded to 50).
- **AC3**: When a poll returns a count `>= ISSUE_POLL_LIMIT` (the cap was hit — truncation may have occurred), a WARNING is logged so a silently-capped scan is no longer invisible (fix (c)).
- **AC4 (non-regression)**: When a poll returns a count below the cap, no spurious warning fires.
- **AC5 (real-world adequacy)**: The live open-`squidsquad`-issue count today is comfortably under the new cap, so no handoff item is currently starved by this limit.

## Test Cases

### TC-1 (covers AC1): Constant raised
- **Steps**: Inspect `harness.ExternalActivityDetector.ISSUE_POLL_LIMIT` live via import.
- **Expected**: `== 500`.
- **Verification command**: `python -c "import sys; sys.path.insert(0,'references/scripts'); import harness; print(harness.ExternalActivityDetector.ISSUE_POLL_LIMIT)"`

### TC-2 (covers AC2): Real --limit arg reflects the new cap
- **Precondition**: n/a.
- **Steps**: Call the real `_check_for_changes()` with only `subprocess.run` mocked (capture the invoked command); inspect the `--limit` argument.
- **Expected**: `--limit 500`, not `--limit 50`.
- **Verification command**: independent ad-hoc script (own fixture, not the worker's).

### TC-3 (covers AC3): Warning fires at cap
- **Steps**: Same harness as TC-2, mocked `gh` response with exactly 500 fake issues (`>= cap`).
- **Expected**: stderr contains `WARNING` and `#13555`.

### TC-4 (covers AC4): No warning below cap, using TODAY'S REAL live count
- **Steps**: Same harness, mocked `gh` response sized to the real live open-`squidsquad`-issue count fetched via `gh issue list --label squidsquad --state open --json number --limit 500 | length` (167 at verification time — deliberately not a round synthetic number, to avoid rederiving the worker's own fixture).
- **Expected**: stderr is empty of `WARNING`.

### TC-5 (covers AC5): Real-world headroom
- **Steps**: `gh issue list --label squidsquad --state open --json number --limit 500` and count.
- **Expected**: count < 500 (comfortable headroom; note the un-limited default of `gh issue list` is only 30, so this command MUST pass `--limit` explicitly to get a true count).

### TC-6: Worker's own regression suite + full test_harness.py + static gate
- **Steps**: `pytest tests/test_harness.py -k 13555`, full `pytest tests/test_harness.py`, `python tests/run_tests.py static`.
- **Expected**: All green.

## Coverage matrix
- AC1 → TC-1
- AC2 → TC-2
- AC3 → TC-3
- AC4 → TC-4
- AC5 → TC-5
- (non-AC) → TC-6

No LLM-consumed instructions touched (harness.py is code) — no Comprehension Questions section required.
