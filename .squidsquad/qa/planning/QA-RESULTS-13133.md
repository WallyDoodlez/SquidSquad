# QA-RESULTS-13133 — VERDICT: PASS (zero gaps)

**Issue**: #13133 (type:issue, severity:low, role:skill, improvement-scan) — scan_index.rebuild() double-counts findings across multi-file scans.
**PR**: #13138 @ `ef28e8ba0`, branch `squidsquad/task/13133`, `Fixes #13133`.
**Verified by**: verifier, isolated worktree `qa-wt-13133` (removed). **CQ**: none (deterministic code).
**Note**: this is my own cy386 improvement-scan filing — loop closed (filed → skill fixed → verified).

## AC walk — all PASS

| AC | Result | Evidence |
|----|--------|----------|
| AC1 finding inserted once | PASS | rebuild() now collects `file_scan_ids` per file, then inserts each finding ONCE after the per-file loop, attributed to `entry["files"][0]` (first_file/first_sid), matching record_scan's `files[0]` default. Fallback `next(iter(file_scan_ids.values()))` if files[0] absent. (scan_index.py:707-726) |
| AC2 finding_count not inflated | PASS | Test asserts file_coverage finding_count(tracker.py)==1, compose.py==0 (pre-fix: both 1). |
| AC3 regression test exact | PASS | `findings == 1` (was `>= 1`); asserts single row → files[0]=tracker.py, issue #100; per-file finding_count. Confirmed pre-fix main nests the INSERT (the bug) → assertion would fail there. |
| AC4 no-regression | PASS | test_scan_index.py 42 passed; full static gate **PASS — 4856, 0 fail / 0 err**. |

## Notes
- Fix matches the filed fix-direction exactly. record_scan path unchanged (was already 1-row).
- Merge deferred to DM (`Fixes #13133` → DM owns ship + counter). Counter NOT bumped.

**VERDICT: PASS → status:pending-ship (DM).**
