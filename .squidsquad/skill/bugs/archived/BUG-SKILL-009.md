## BUG-SKILL-009 — Setup overwrites user's existing statusLine and settings.json config

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The setup Step 7 writes a `statusLine` config to `.claude/settings.json`. If the user already has a custom `statusLine` configured (e.g. their own status bar script), the setup overwrites it. The merge logic says "do not overwrite existing hooks" for SessionStart, but there's no equivalent protection for `statusLine`. The user's personalized settings get wiped.

  The fix should:
  1. Check if `statusLine` already exists in settings.json before writing
  2. If it exists, warn the user and ask whether to replace, merge, or skip
  3. If merging, chain the scripts (e.g. run both and combine output)
  4. Same check needed for `permissions.allow` — don't duplicate or remove existing entries
  5. Document this behavior in SKILL.md setup Step 7

- **Steps to Reproduce**:
  1. Have a custom `.claude/settings.json` with a `statusLine` config
  2. Run SquidSquad setup
  3. Observe your statusLine config is overwritten
- **Expected**: Setup detects existing statusLine and asks the user how to handle it
- **Actual**: Setup silently overwrites the user's statusLine config

### Discussion

> [2026-03-28 04:15] **pm/qa**: Reported by human. The status line feature was an impulse requirement that didn't consider users with existing settings.json customizations. Setup must be non-destructive.
> [2026-03-28 04:45] **skill-lead**: Fixed. SKILL.md Step 7 merge logic now explicitly checks for existing statusLine — prompts user to replace or skip. permissions.allow deduplicates. Status → Fixed.
> [2026-03-28 05:10] **pm/qa**: Verified. Step 7 checks for existing statusLine, prompts user. permissions.allow deduplicates. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
