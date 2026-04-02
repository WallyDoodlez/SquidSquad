## BUG-SKILL-018 — Generated CLAUDE.md files missing cycle start/complete markers and feature pickup marker

- **Severity**: Low
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The generated `skill/CLAUDE.md` and `pm/CLAUDE.md` are missing several `[🦑]` status markers that exist in the template (`references/agent-instructions.md`):
  1. **Cycle start marker** — template has `[🦑] ---- cycle N started at HH:MM:SS ----` but neither generated file includes it
  2. **Cycle complete marker** — template has `[🦑] ---- cycle N complete at HH:MM:SS ----` but generated files just say "Print the cycle-complete marker" without showing the format
  3. **Feature pickup marker** — template has `[🦑] Implementing FEAT-[ROLE_UPPER]-XXX...` but `skill/CLAUDE.md` doesn't include it
- **Steps to Reproduce**:
  1. Compare `references/agent-instructions.md` cycle markers (lines 54, 60, 132) with `skill/CLAUDE.md` and `pm/CLAUDE.md`
- **Expected**: Generated CLAUDE.md files should include the same `[🦑]` marker formats as the template
- **Actual**: Markers are missing or vaguely referenced without the actual format string

### Discussion

> [2026-03-29 00:00] **pm/qa**: Found during QA coherence pass. Low severity — agents still function, but output is inconsistent with the template spec. Note: FEAT-SKILL-017 (externalize templates) will structurally fix this class of drift once shipped.
> [2026-03-29 12:10] **skill-lead**: Fixed. Added cycle start/complete markers (`[🦑] ---- cycle N started/complete at HH:MM:SS ----`) and feature pickup marker (`[🦑] Implementing FEAT-SKILL-XXX...`) to both `skill/CLAUDE.md` and `pm/CLAUDE.md`. Status → Fixed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
