# TEST-PLAN-13132 — tracker.py gh-CLI fallback fail-closed

**Issue**: #13132 (type:issue, severity:low, role:skill) — gh-CLI fallback paths skip the file's fail-closed error pattern.
**PR**: #13135, branch `squidsquad/task/13132`.
**Derived independently from the issue ACs** (Finding 1, Finding 2, Tests section) — not from the PR diff.
**CQ**: none — tracker.py is deterministic code, not LLM-consumed instruction.

## Acceptance criteria (from issue body)

- **AC-F1a** `get_labels` CLI fallback must not crash on gh failure → fail closed to `[]`.
- **AC-F1b** `get_state` CLI fallback must not crash on gh failure → fail closed to `"UNKNOWN"`.
- **AC-F2** `_check_unread_feedback` must return the fail-closed sentinel `[("unknown (API error)","unknown")]` on a malformed exit-0 response (not raise).
- **AC-T** Regression tests exercise non-zero returncode / empty / malformed-JSON branches that had no coverage; tests would have caught the original bug.

## Test cases

| TC | Function | Input (CLI fallback, adapter=None) | Expected |
|----|----------|-----------|----------|
| TC1 | get_labels | returncode=1 | `[]`, no raise |
| TC2 | get_labels | rc=0, stdout="" | `[]` |
| TC3 | get_labels | rc=0, stdout=malformed JSON | `[]` |
| TC4 | get_labels | rc=0, label dict missing "name" | nameless dropped, not `""` injected |
| TC5 | get_state | returncode=1 | `"UNKNOWN"`, no raise |
| TC6 | get_state | rc=0, stdout="" | `"UNKNOWN"` |
| TC7 | get_state | rc=0, malformed JSON | `"UNKNOWN"` |
| TC8 | get_state | rc=0, JSON missing "state" key | `"UNKNOWN"` (was KeyError) |
| TC9 | _check_unread_feedback | rc=0, malformed JSON | sentinel `[("unknown (API error)","unknown")]` |
| TC10 | _check_unread_feedback | returncode=1 | sentinel (existing guard, regression) |
| TC11 | get_labels/get_state/_check_unread_feedback | valid success JSON | happy path unchanged (no regression) |

## Execution method

1. Run `tests/test_tracker.py` on the branch (full file) — all must pass.
2. Independent runtime probe: import **main (pre-fix)** tracker, mock `_run_list`, confirm each function RAISES (proves the regression tests are genuine — they would have caught the original bug).
3. Full static gate (`tests/run_tests.py static`) — fail-closed, 0 failures.

## Pass condition

All ACs PASS with observable evidence + zero-gap (no failed TC, no coverage gap) + static gate green.
