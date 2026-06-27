# TEST-PLAN-12846 — wizard cmd_scan_summary fail-closed

**Issue**: #12846 (type:issue, severity:low, role:skill) — cmd_scan_summary reads .repo-scan.json without try/except (crashes on malformed/unreadable).
**PR**: #13141, branch `squidsquad/task/12846`. **CQ**: none (deterministic code).

## ACs
- **AC1** `cmd_scan_summary` wraps the `.repo-scan.json` `json.loads` in `try/except (json.JSONDecodeError, OSError)` with graceful fallback (fresh on-the-fly scan), matching sibling guarded readers.
- **AC2** valid cache still used (no wasteful rescan) — happy path preserved.
- **AC3** regression test: malformed cache → no crash, rc 0 (would fail pre-fix).
- **AC4** no-regression: full static gate green.

## Test cases
| TC | Input | Expected |
|----|-------|----------|
| TC1 | malformed `.repo-scan.json` (`{not valid json`) | no crash, rc 0, falls back to fresh scan |
| TC2 | valid cache | used, no rescan, rc 0 |
| TC3 | absent cache | on-the-fly scan (pre-existing behavior) |

## Method
1. Read wizard.py + test diffs — confirm guard matches sibling pattern.
2. Run test_wizard.py ScanSummary + 12846 classes.
3. Confirm pre-fix main has bare json.loads (regression validity).
4. Full static gate.

## Pass condition
All ACs PASS; zero-gap; static gate green.
