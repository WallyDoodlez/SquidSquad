## BUG-SKILL-014 — ANSI escape codes in step markers render as mangled text

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: skill-lead
- **Assigned To**: skill-lead
- **Description**: BUG-SKILL-012 replaced `[squidsquad]` markers with ANSI-styled `\033[45m\033[30m[🦑]\033[0m`. However, Claude Code cannot render ANSI escape sequences in text output — they display as literal mangled text. The fix is to use plain `[🦑]` without ANSI wrapping. The squid emoji is visually distinctive on its own.

  **Fix needed:**
  1. Replace all `\033[45m\033[30m[🦑]\033[0m` with `[🦑]` across all templates and generated files
  2. Update SKILL.md and README.md references

- **Steps to Reproduce**:
  1. Run any SquidSquad agent
  2. Observe step markers show raw escape codes instead of colored text
- **Expected**: Clean `[🦑]` prefix
- **Actual**: `\033[45m\033[30m[🦑]\033[0m` displayed as literal text

### Discussion

> [2026-03-28 07:15] **skill-lead**: Self-filed. Human reported mangled output. ANSI codes don't work in Claude Code text output.
> [2026-03-28 07:16] **skill-lead**: Fixed. Replaced all ANSI-wrapped markers with plain `[🦑]` across agent-instructions.md, skill/CLAUDE.md, pm/CLAUDE.md, and SKILL.md. Status → Fixed.
> [2026-03-28 07:20] **pm/qa**: Verified. Zero `\033` escape sequences remain in any template or generated file. Plain `[🦑]` markers confirmed (35 in agent-instructions.md). Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
