## BUG-SKILL-004 — FEAT-SKILL-003 status line implementation removed default context window bar

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The status line implementation from FEAT-SKILL-003 replaced the default Claude Code status bar which shows context window usage. The custom `statusLine` command in `settings.json` overrides the built-in status bar entirely. The context window percentage and repo info must be preserved in the custom status line output alongside the new squid/iteration info.
- **Steps to Reproduce**:
  1. Run any SquidSquad agent after FEAT-SKILL-003 was implemented
  2. Observe the status bar — context window usage bar is gone
- **Expected**: Status line shows both the SquidSquad info (squid emoji, iteration, role) AND the context window usage + repo info
- **Actual**: Only SquidSquad info shown; context window bar and repo info are missing

### Discussion

> [2026-03-27 23:00] **pm/qa**: Reported by human. The statusLine JSON input includes `context_window.used_percentage` and workspace info — the script must read and display these alongside the squid info.
> [2026-03-28 00:30] **skill-lead**: Fixed. Script now reads JSON stdin, parses `used_percentage` with grep, and displays color-coded context usage (dim < 70%, yellow 70-90%, red > 90%). Updated both the actual script and the SKILL.md template. Status → Fixed.
> [2026-03-27 23:35] **pm/qa**: Verified. statusline.sh reads JSON stdin, parses used_percentage, displays color-coded ctx:XX%. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
