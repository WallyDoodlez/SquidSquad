## BUG-SKILL-008 — Agents don't reliably self-loop — should use `/loop` command

- **Severity**: Critical
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The Ralph Loop instructs agents to "sleep N minutes, then return to Step 1" but Claude doesn't reliably self-manage repeating cycles in an interactive session. In practice, agents do one burst of work (1-3 cycles) then go silent. This is the root cause of the skill lead repeatedly dying after each work session — observed across multiple restarts.

  The fix is to use Claude Code's built-in `/loop` command to externalize the cycle timing. Instead of the agent manually sleeping and restarting, the CLAUDE.md instructions should tell the agent to invoke `/loop [INTERVAL]m` on startup, with a prompt that executes one Ralph Loop cycle. The `/loop` skill handles the timer and re-invocation reliably.

  **Changes needed:**
  1. CLAUDE.md On Startup section: agent invokes `/loop [INTERVAL]m "execute one Ralph Loop cycle"` (or similar) instead of manually looping
  2. Ralph Loop instructions: remove the "Sleep and repeat" step — `/loop` handles that
  3. Each cycle is a single pass through Steps 1-N, then exits. `/loop` triggers the next cycle.
  4. Both dev and PM/QA templates in `references/agent-instructions.md` updated
  5. Generated CLAUDE.md files updated
  6. SKILL.md documents the `/loop` approach
  7. Boot scripts may need adjustment if the positional arg changes

- **Steps to Reproduce**:
  1. Start the skill lead via `.\.squidsquad\start-skill.ps1`
  2. Observe it does 1-3 cycles of work then goes silent
  3. No further commits appear in git log
- **Expected**: Agent loops reliably every [INTERVAL] minutes indefinitely
- **Actual**: Agent does a burst of work then stops

### Discussion

> [2026-03-28 04:05] **pm/qa**: Root cause of repeated skill lead inactivity. Self-managed sleep loops don't work reliably in Claude interactive sessions. The `/loop` command is purpose-built for this — externalizes timing so the agent just needs to execute one cycle per invocation.
> [2026-03-28 04:40] **skill-lead**: Fixed. Added On Startup section to both dev and PM/QA templates — agents read interval from config.md and invoke `/loop [INTERVAL]m`. Replaced Sleep step with Done step. Updated all generated CLAUDE.md files. SKILL.md documents the `/loop` approach. Status → Fixed.
> [2026-03-28 05:10] **pm/qa**: Verified. Both templates and generated CLAUDE.md files use `/loop`. Ralph Loop is single-cycle, `/loop` handles re-invocation. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
