## BUG-SKILL-013 — `bash.exe.stackdump` committed to repo

- **Severity**: Low
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: A `bash.exe.stackdump` file was committed in `f8d0b14`. This is a Windows/MSYS crash dump artifact — not a project file. It should be removed from tracking and added to `.gitignore`.

  **Fix needed:**
  1. `git rm bash.exe.stackdump`
  2. Add `*.stackdump` to `.gitignore`

- **Steps to Reproduce**:
  1. `ls bash.exe.stackdump` — file exists in repo root
- **Expected**: Crash dumps not tracked in git
- **Actual**: `bash.exe.stackdump` is tracked

### Discussion

> [2026-03-28 06:15] **pm/qa**: Found during QA review of commit f8d0b14. Crash dump artifact accidentally committed alongside BUG-010/011 fixes.
> [2026-03-28 06:20] **skill-lead**: Fixed. Ran `git rm bash.exe.stackdump` and added `*.stackdump` to `.gitignore`. Status → Fixed.
> [2026-03-28 06:30] **pm/qa**: Verified. File removed from repo, `*.stackdump` in .gitignore line 5. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
