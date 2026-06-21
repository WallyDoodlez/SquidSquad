# TEST-PLAN-13133 — scan_index.rebuild() finding double-count

**Issue**: #13133 (type:issue, severity:low, role:skill, improvement-scan) — rebuild() double-counts findings across multi-file scans.
**PR**: #13138, branch `squidsquad/task/13133`. **CQ**: none (deterministic code).
**Derived from**: the filed finding's fix-direction (move INSERT out of per-file loop, attribute to files[0], tighten test).

## ACs
- **AC1** `rebuild()` inserts each finding exactly ONCE per entry, attributed to `entry["files"][0]` (matching `record_scan`'s `files[0]` default).
- **AC2** `file_coverage` finding_count not inflated: only files[0] of a multi-file scan carries the finding; other files stay 0.
- **AC3** regression test asserts exact counts (`findings == 1`, per-file finding_count) — would fail on pre-fix.
- **AC4** no-regression: full static gate green.

## Test cases
| TC | Check | Expected |
|----|-------|----------|
| TC1 | rebuild fixture (2-file/1-finding scan #100) → total findings rows | exactly 1 |
| TC2 | the 1 row's file_path | files[0] = tracker.py |
| TC3 | file_coverage finding_count(tracker.py) | 1 |
| TC4 | file_coverage finding_count(compose.py) | 0 (pre-fix: 1) |
| TC5 | scan rows unaffected | still 4 (1 per file) |
| TC6 | record_scan path | unchanged (already 1-row) |

## Method
1. Read scan_index.py diff — confirm INSERT moved out of per-file loop, files[0] attribution, fallback handled.
2. Run test_scan_index.py (branch) — all pass.
3. Confirm pre-fix main nests the INSERT (regression validity).
4. Full static gate.

## Pass condition
All ACs PASS; zero-gap; static gate green.
