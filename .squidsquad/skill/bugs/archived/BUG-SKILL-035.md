## BUG-SKILL-035 — Overdue timer shows +183m because quiet cycles don't update the timestamp

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: The statusline timer calculates elapsed time from the last iteration file's modified timestamp (`ls iter-*.md | tail -1`). Quiet cycles skip iteration logging (by design), so during long stretches of quiet cycles the timer drifts — the last iteration file gets older and older, and the overdue indicator shows increasingly large values (e.g. `⏰ +183m`). The timer should reflect when the last cycle *ran*, not when the last iteration file was *written*.
- **Root Cause**: `statusline.sh` line 56 reads `LAST_MOD` from the latest `iter-*.md` file. Quiet cycles produce no iteration file, so `LAST_MOD` goes stale.
- **Possible Fixes**:
  1. Write a lightweight heartbeat/timestamp file (e.g. `.squidsquad/<role>/last-cycle`) at the end of every cycle including quiet ones — statusline reads this instead of iteration files
  2. Touch the latest iteration file on quiet cycles (changes mtime without creating a new file)
  3. Use the `current-state` file's mtime (already written every cycle, including `idle|` at cycle end)
- **Steps to Reproduce**:
  1. Run agent through several quiet cycles (no bugs to verify, no features to ship)
  2. Observe statusline timer — overdue value grows with each quiet cycle
- **Expected**: Timer resets after each cycle, including quiet ones
- **Actual**: Timer only resets when an iteration file is created (productive cycles only)

### Discussion

> [2026-03-30 13:45] **pm/qa**: Filed from human report. Human saw ⏰ +183m on PM status bar. Root cause: quiet cycles don't log iterations, so the timer source (iter file mtime) goes stale. Option 3 (use current-state mtime) is simplest since idle| is already written every cycle.
> [2026-03-31 00:05] **skill-lead**: Fixed in statusline.sh — timer now reads mtime from `current-state` file (written every cycle including quiet ones) instead of latest `iter-*.md` file. Falls back to iter file if current-state doesn't exist. Updated both `references/statusline.sh` and live `.squidsquad/statusline.sh`. Status → Fixed.
> [2026-03-31 00:30] **pm/qa**: Verified — timer reads current-state mtime with iter file fallback. No more stale +183m. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
