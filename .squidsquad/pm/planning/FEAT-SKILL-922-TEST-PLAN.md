# FEAT-SKILL-922 Test Plan -- SQLite Scan Index

## Test Cases

### TC-1: Happy path -- suggest-targets returns ranked files
- **Precondition**: `scan-index.db` exists with at least 10 files in `file_coverage`, varying `last_scanned_at` dates, and populated `git_churn` and `findings` tables. Multiple roles have scan records.
- **Steps**:
  1. Run `python references/scripts/scan_index.py suggest-targets skill --count 5`
  2. Capture the output list.
- **Expected**: Returns exactly 5 file paths, ordered by composite score (coverage_gap=0.3, churn=0.3, cross_role=0.2, acceptance=0.2). Files with older scans, higher churn, more cross-role findings, and higher acceptance rates appear first. All returned files exist on disk.
- **Verification**: Compare output ranking against manual composite score calculation for the top 5. Verify each returned path exists: `test -f <path>` for each. Verify deleted files are excluded even if present in DB.

### TC-2: Happy path -- record-scan writes to DB and updates file_coverage
- **Precondition**: DB exists with tables created. A file `references/scripts/tracker.py` has not been scanned by role `qa` before.
- **Steps**:
  1. Run `python references/scripts/scan_index.py record-scan --role qa --files "references/scripts/tracker.py,references/scripts/compose.py" --findings '[]'`
  2. Query the `scans` table for role=qa.
  3. Query the `file_coverage` table for `references/scripts/tracker.py`.
- **Expected**: Two new rows in `scans` (one per file, same `scanned_at` timestamp). `file_coverage` row for `references/scripts/tracker.py` shows `total_scan_count >= 1`, `last_scanned_by = 'qa'`, and `last_scanned_at` matches the scan timestamp.
- **Verification**: `sqlite3 .squidsquad/scan-index.db "SELECT * FROM scans WHERE role='qa' ORDER BY id DESC LIMIT 2;"` returns the two new rows. `sqlite3 .squidsquad/scan-index.db "SELECT total_scan_count, last_scanned_by FROM file_coverage WHERE file_path='references/scripts/tracker.py';"` returns expected values.

### TC-3: Happy path -- record-decision updates acceptance rate
- **Precondition**: DB has a finding row with `github_issue_number=100` and `human_decision IS NULL`. The associated file has `finding_count=1, accepted_finding_count=0` in `file_coverage`.
- **Steps**:
  1. Run `python references/scripts/scan_index.py record-decision --issue 100 --accepted true`
  2. Query the `findings` table for issue 100.
  3. Query `file_coverage` for the associated file.
- **Expected**: `findings` row has `human_decision='accepted'` and `decided_at` is set. `file_coverage` row has `accepted_finding_count=1`.
- **Verification**: `sqlite3 .squidsquad/scan-index.db "SELECT human_decision, decided_at FROM findings WHERE github_issue_number=100;"` shows `accepted` and a valid timestamp. Run the same for a rejection case (`--accepted false`) and verify `rejected_finding_count` increments instead.

### TC-4: Happy path -- refresh-churn populates git_churn table
- **Precondition**: DB exists with empty `git_churn` table. Repo has git history with commits in the last 30 and 90 days.
- **Steps**:
  1. Run `python references/scripts/scan_index.py refresh-churn`
  2. Query the `git_churn` table.
- **Expected**: Rows exist for files touched in recent commits. `commit_count_30d` and `commit_count_90d` are populated with correct counts matching `git log --numstat` output. `last_refreshed` is set to current timestamp.
- **Verification**: Run `git log --since="30 days ago" --numstat --format="" | awk '{print $3}' | sort | uniq -c | sort -rn | head -5` and compare the top 5 files and counts against `sqlite3 .squidsquad/scan-index.db "SELECT file_path, commit_count_30d FROM git_churn ORDER BY commit_count_30d DESC LIMIT 5;"`.

### TC-5: Rename detection -- refresh-churn updates DB paths
- **Precondition**: DB has `file_coverage` and `git_churn` entries for a file at its old path (e.g., `old/path.py`). The file was renamed in git history to `new/path.py` (detectable via `git log --follow --diff-filter=R`).
- **Steps**:
  1. Run `python references/scripts/scan_index.py refresh-churn`
  2. Query `file_coverage` for both old and new paths.
  3. Query `git_churn` for both old and new paths.
- **Expected**: `file_coverage` row exists for `new/path.py` with the historical scan counts carried forward. No row for `old/path.py` (or it is marked as deleted/merged). `git_churn` row exists for `new/path.py` with combined commit counts.
- **Verification**: `sqlite3 .squidsquad/scan-index.db "SELECT file_path, total_scan_count FROM file_coverage WHERE file_path IN ('old/path.py','new/path.py');"` shows only the new path with the original scan count preserved.

### TC-6: Rebuild from markdown -- delete DB and reconstruct
- **Precondition**: DB exists with known data. Multiple `scan-history.md` files exist under `.squidsquad/*/scan-history.md` with scan entries including dates, file lists, findings with issue numbers, and rejection notes.
- **Steps**:
  1. Record current DB state: count of rows in `scans`, `findings`, `file_coverage`.
  2. Delete the DB: `rm .squidsquad/scan-index.db`
  3. Run `python references/scripts/scan_index.py rebuild`
  4. Query all tables for row counts and spot-check specific entries.
- **Expected**: DB is recreated. `scans` table contains one row per file per scan entry in scan-history.md. `findings` table contains rows for each finding with `#NNN` issue references parsed. `file_coverage` is populated with correct aggregates. Rejected items from scan-history.md appear in the `rejections` table.
- **Verification**: Compare row counts before deletion vs after rebuild (should match or be very close). Spot-check: pick a specific scan entry from a scan-history.md file and verify its data exists in the rebuilt DB with correct role, timestamp, files, and findings.

### TC-7: Corrupt/missing DB -- graceful fallback
- **Precondition**: No `scan-index.db` file exists (or the file is zero bytes / corrupt binary).
- **Steps**:
  1. Remove or corrupt the DB: `rm -f .squidsquad/scan-index.db` (or `echo "garbage" > .squidsquad/scan-index.db`)
  2. Run `python references/scripts/scan_index.py suggest-targets skill --count 5`
- **Expected**: The command exits with code 0. It either auto-rebuilds from scan-history.md and returns results, or returns an empty list with a warning logged to stderr. It does NOT crash with a traceback or return exit code 1.
- **Verification**: Check exit code: `echo $?` is 0. Check stderr for a warning message (e.g., "DB missing, rebuilding..." or "DB corrupt, falling back to empty results"). If auto-rebuild occurred, verify DB now exists and contains data.

### TC-8: Empty state -- new project with no scan history
- **Precondition**: No `scan-index.db` exists. No `scan-history.md` files exist under `.squidsquad/*/`. The repo has source files tracked in git.
- **Steps**:
  1. Run `python references/scripts/scan_index.py suggest-targets skill --count 5`
- **Expected**: Returns up to 5 source files from the repo, sorted by coverage gap (all files have zero coverage). Files are selected from the project source tree, excluding `.squidsquad/`, `node_modules/`, `.git/`, build directories, and binary files.
- **Verification**: Verify all returned files exist and are source files (not binary or build output). Verify none are from excluded directories. Verify the DB was created with empty `scans` and `findings` tables but `file_coverage` may be empty or populated with zero-count entries.

### TC-9: Sparse PM prompts -- unresolved improvement-scan issues surfaced during check-in
- **Precondition**: Several GitHub Issues exist with label `improvement-scan` and status `status:open` (human has not yet decided). PM is running a Ralph Loop cycle.
- **Steps**:
  1. Observe PM check-in output (Step 2 of Ralph Loop).
  2. Run multiple cycles and observe when improvement-scan items are mentioned.
- **Expected**: PM mentions unresolved improvement-scan issues during check-in, but NOT every cycle. The surfacing is sparse -- only when there are pending decisions that have been open for a while. PM does not nag every 30 minutes about the same items.
- **Verification**: Review PM iteration logs across 3+ cycles. Confirm improvement-scan items appear in check-in notes intermittently, not in every consecutive cycle. Confirm the PM does not auto-approve or auto-reject these items.

### TC-10: GitHub Issue integration -- findings filed with correct labels
- **Precondition**: DB is populated. An improvement scan runs and produces findings.
- **Steps**:
  1. Trigger an improvement scan (3+ quiet cycles with no real work).
  2. Observe the filed GitHub Issues.
  3. Run `python references/scripts/scan_index.py record-decision --issue <N> --accepted true` for one finding.
  4. Run `python references/scripts/scan_index.py record-decision --issue <N> --accepted false` for another.
- **Expected**: Filed issues have labels: `improvement-scan`, `squidsquad`, `priority:low`, the correct `type:issue` or `type:task`, and the correct `role:*` label. Issue body contains `Found by`, `File`, `Finding`, and `Recommendation` fields. After record-decision, the `findings` table reflects the human decision and `file_coverage` acceptance/rejection counts are updated.
- **Verification**: `gh issue view <N> --json labels` confirms correct labels. `sqlite3 .squidsquad/scan-index.db "SELECT human_decision FROM findings WHERE github_issue_number=<N>;"` confirms decision recorded.

### TC-11: Gitignore -- DB file is not committed
- **Precondition**: `.gitignore` has been updated per the research (entries for `scan-index.db`, `scan-index.db-journal`, `scan-index.db-wal`, `scan-index.db-shm`).
- **Steps**:
  1. Run `python references/scripts/scan_index.py rebuild` (creates the DB).
  2. Run `git status` to check if the DB or WAL/SHM files appear as untracked.
  3. Run `git add -A && git status` to verify nothing is staged.
- **Expected**: `scan-index.db`, `scan-index.db-wal`, `scan-index.db-shm`, and `scan-index.db-journal` do NOT appear in `git status` output (neither untracked nor staged).
- **Verification**: `git status --porcelain | grep scan-index` returns empty. `git check-ignore .squidsquad/scan-index.db` returns the path (confirming it is ignored).

### TC-12: Composite scoring -- weights applied correctly
- **Precondition**: DB with known data allowing manual score calculation. Set up files with known values:
  - File A: last scanned 14 days ago, 10 commits in 30d, 3 cross-role findings, 0.8 acceptance rate
  - File B: last scanned 1 day ago, 2 commits in 30d, 0 cross-role findings, 0.5 acceptance rate
  - File C: never scanned, 5 commits in 30d, 1 cross-role finding, no acceptance data (0.0)
- **Steps**:
  1. Insert the test data into the DB.
  2. Run `python references/scripts/scan_index.py suggest-targets skill --count 3`
  3. Manually compute the expected composite scores using the formula: `score = 0.3 * (days_since_scan / max_days) + 0.3 * (commits_30d / max_churn) + 0.2 * (cross_role / max_cross) + 0.2 * acceptance_rate`
- **Expected**: The returned order matches the manual calculation. File C (never scanned, moderate churn) and File A (old scan, high churn, high acceptance) should rank above File B (recently scanned, low churn).
- **Verification**: Compare the script output order against the manually computed ranking. If a `--verbose` or `--debug` flag is available, verify the individual score components printed match expectations.

### TC-13: Side effect regression -- scan-history.md still written alongside DB
- **Precondition**: Existing `scan-history.md` files for multiple roles with prior entries. DB exists.
- **Steps**:
  1. Record the current content/line count of `.squidsquad/skill/scan-history.md`.
  2. Run `python references/scripts/scan_index.py record-scan --role skill --files "some/file.py" --findings '[]'`
  3. Check `.squidsquad/skill/scan-history.md` for a new entry.
  4. Delete the DB and run `python references/scripts/scan_index.py rebuild`.
  5. Verify the rebuilt DB contains the entry from step 2.
- **Expected**: After record-scan, a new `## Scan -- YYYY-MM-DD HH:MM` section is appended to scan-history.md with the scanned files and findings listed. The existing content is untouched. After rebuild, the DB contains this entry with correct role, timestamp, and file path.
- **Verification**: `tail -20 .squidsquad/skill/scan-history.md` shows the new entry with correct format. After rebuild, `sqlite3 .squidsquad/scan-index.db "SELECT * FROM scans WHERE file_path='some/file.py' AND role='skill';"` returns the entry.

### TC-14: Upgrade path -- old install without scan_index.py falls back gracefully
- **Precondition**: A clone that has the updated improvement-scan sub-skill text (referencing `scan_index.py suggest-targets`) but does NOT have `references/scripts/scan_index.py` on disk (simulating a partial upgrade or non-upgraded install).
- **Steps**:
  1. Remove or rename `references/scripts/scan_index.py` temporarily.
  2. Trigger an improvement scan cycle (agent encounters the sub-skill step that calls scan_index.py).
  3. Observe agent behavior.
- **Expected**: The agent detects that `scan_index.py` is missing (command not found or file not found). It falls back to the markdown-based targeting approach: reads `scan-history.md` directly to select files. The scan completes successfully. No crash, no unhandled exception, no stalled cycle.
- **Verification**: Check the agent's iteration log or scan-history.md for a completed scan entry. Verify no error messages in the agent output beyond an informational warning about scan_index.py not being available.

## Smoke Tests

- [ ] `python references/scripts/scan_index.py --help` prints usage with all subcommands (suggest-targets, record-scan, record-decision, refresh-churn, rebuild)
- [ ] `python references/scripts/scan_index.py suggest-targets skill --count 3` returns 0-3 file paths (no crash)
- [ ] `python references/scripts/scan_index.py rebuild` completes without error on an existing repo with scan-history.md files
- [ ] `python references/scripts/scan_index.py refresh-churn` completes without error (or warns gracefully if git history is shallow)
- [ ] DB file is created at `.squidsquad/scan-index.db` after any subcommand
- [ ] WAL mode is enabled: `sqlite3 .squidsquad/scan-index.db "PRAGMA journal_mode;"` returns `wal`
- [ ] Busy timeout is set: `sqlite3 .squidsquad/scan-index.db "PRAGMA busy_timeout;"` returns `5000`

## Regression Risks

- **scan-history.md format changes**: If record-scan changes the markdown format, the rebuild parser may fail on new entries. Ensure record-scan writes entries in the exact format the rebuild parser expects.
- **Concurrent agent writes**: Two agents calling record-scan simultaneously could hit SQLite busy errors. WAL mode and busy_timeout should handle this, but verify on Windows specifically.
- **File path separators on Windows**: SQLite stores paths as strings. Ensure all paths use forward slashes consistently (not backslashes on Windows) to avoid duplicate entries for the same file.
- **Large repos**: suggest-targets must handle repos with thousands of source files without excessive runtime. The file-system walk and LEFT JOIN against file_coverage should be bounded.
- **Git shallow clones**: refresh-churn relies on `git log --numstat`. Shallow clones may return incomplete data. Verify the script degrades gracefully (uses zero for missing churn data).
- **Existing improvement-scan workflow**: The dual-write (DB + markdown) must not break agents that still read scan-history.md directly. The markdown format must remain parseable by both the old manual approach and the new rebuild command.
