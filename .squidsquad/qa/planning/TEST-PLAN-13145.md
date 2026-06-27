# TEST-PLAN-13145 — repo_scan.py main() exit-2 contract

**Issue**: #13145 (type:issue, severity:low, role:skill, improvement-scan) — main() doesn't honor documented exit-2 usage contract (my own scan filing).
**PR**: #13146, branch `squidsquad/task/13145` (no closing keyword). **CQ**: none.

## ACs
- **AC1 (F2)** `--path` with no following value → exit 2 + error, not silent REPO_ROOT scan returning 0.
- **AC2 (F1)** --save write failure (OSError) → exit 2 + error, not unhandled traceback.
- **AC3** regression tests for both; no-regression static gate green.

## Test cases
| TC | Input | Expected |
|----|-------|----------|
| TC1 | `--path` (final token) | exit 2, "--path requires an argument" |
| TC2 | `--save` to unwritable target (.squidsquad is a file → mkdir FileExistsError) | exit 2, "Cannot save" |
| TC3 | valid `--path X` | unchanged (scans X) |
| TC4 | nonexistent `--path X` | exit 2 (pre-existing) |

## Method
1. Read repo_scan.py + test diffs.
2. Run test_repo_scan.py.
3. Full static gate.

## Pass condition
Both fixes verified, regression-valid, zero-gap, static gate green.
