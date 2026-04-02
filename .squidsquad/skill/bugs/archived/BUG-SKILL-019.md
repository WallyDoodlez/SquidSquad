## BUG-SKILL-019 — Boot logo in settings.json startup hook doesn't match README logo

- **Severity**: Low
- **Status**: Closed
- **Reported By**: human (via pm/qa)
- **Assigned To**: skill-lead
- **Description**: The ASCII squid art in the startup hook (`.claude/settings.json`) uses a different squid design than the canonical logo in `README.md`. The startup hook should use the README version.
- **Steps to Reproduce**:
  1. Open `.claude/settings.json`, find the startup hook command with the LOGO heredoc
  2. Compare with the logo at the top of `README.md`
- **Expected**: Boot logo matches the README logo:
  ```
        ▗▄▖
       ▟█ █▙
      ▐█• •█▌
     ███████
     ▐█████▌
      ▐▌▐▌▐▌
    S Q U I D S Q U A D
  ```
- **Actual**: Boot logo uses a different wider squid design with different eye style and body shape

### Discussion

> [2026-03-29 01:10] **pm/qa**: Filed from human request. The boot logo should match the README logo exactly.
> [2026-03-29 12:08] **skill-lead**: Fixed. Replaced old wide squid design with README canonical logo in all 6 occurrences in SKILL.md (boot scripts, Step 9, SessionStart hook template) and in `.claude/settings.json`. Status → Fixed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
