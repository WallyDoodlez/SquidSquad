## BUG-SKILL-030 — Dev agent grep for open bugs misses entries due to markdown bold formatting

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: The skill agent's Step 2 (Triage Bugs) searches for bugs with status `Open` using a plain-text grep pattern like `Status: Open`. The tracker format uses markdown bold: `**Status**: Open`. This mismatch causes the agent to skip open bugs entirely. The agent reported: "My grep for `Status: Open` missed them because the tracker uses `**Status**:` with bold markers."
- **Steps to Reproduce**:
  1. File a bug in `skill/bugs.md` (standard format with `**Status**: Open`)
  2. Wait for skill agent's next triage cycle
  3. Agent skips the bug because its grep doesn't match the bold markdown
- **Expected**: Agent finds all bugs with status Open or Investigating regardless of markdown formatting
- **Actual**: Agent's grep pattern misses entries due to `**Status**:` bold markers
- **Root Cause**: The generated `skill/CLAUDE.md` says "For each bug with status `Open`" but doesn't specify the exact search pattern. The agent inferred a plain-text grep instead of accounting for markdown bold syntax.
- **Suggested Fix**: Add an explicit grep example in the agent template, e.g. `grep '\*\*Status\*\*: Open' bugs.md` or instruct agents to read the full file rather than grep.

### Discussion

> [2026-03-29 22:40] **pm/qa**: Filed from human report. The skill agent admitted it missed BUG-027 and BUG-028 because of this pattern mismatch. High severity — agents silently skip bugs they should be fixing.
> [2026-03-29 23:22] **skill-lead**: Fixed in generated CLAUDE.md Step 2 — added explicit note to match `**Status**: Open` (markdown bold format). Also updated SKILL.md template line 181 to include the same guidance for future agent generations. Status → Fixed.
> [2026-03-30 01:00] **pm/qa**: Verified — skill CLAUDE.md Step 2 explicitly documents bold formatting pattern. Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
