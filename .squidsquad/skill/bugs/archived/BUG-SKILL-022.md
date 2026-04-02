## BUG-SKILL-022 — Status bar line 2 only shows dev agents, not the full squad

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: The status bar's second line (agent health icons) only loops over `Dev Agents` from config.md. The PM agent is not represented. The human expects to see the entire squad — PM + all dev agents — on line 2. Currently if there's one dev agent (skill), only one 🦑 appears. The PM should also have a health icon.
- **Steps to Reproduce**:
  1. Run SquidSquad with PM + skill agents active
  2. Observe status bar line 2 — only one 🦑 for skill agent
- **Expected**: Line 2 shows health icons for ALL agents (PM + dev agents) — e.g., 🦑🦑 when both are healthy
- **Actual**: Line 2 only shows one 🦑 for the skill dev agent; PM is absent

### Discussion

> [2026-03-29 05:15] **pm/qa**: Filed from human report. Human said "should show the entire squad." The statusline.sh HEALTH loop only iterates over Dev Agents, skipping PM. Fix should add PM health detection (check for `pm:` commit prefix) alongside dev agents.
> [2026-03-29 12:33] **skill-lead**: Fixed. Health icon loop now iterates over `ALL_AGENTS="pm $AGENTS"` so PM appears first in line 2 alongside dev agents. Updated both `references/statusline.sh` and live `.squidsquad/statusline.sh`. Status → Fixed.
> [2026-03-29 12:35] **pm/qa**: Verified. Tested statusline — line 2 now shows two icons (PM + skill). Status → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
