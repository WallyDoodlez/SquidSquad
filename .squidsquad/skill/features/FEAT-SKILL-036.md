## FEAT-SKILL-036 — Boot script first message includes role for terminal title

- **Priority**: Low
- **Status**: Consolidated
- **Requested By**: human
- **Description**: Change the boot scripts' first message to Claude so the first line is `🦑 [role] — [project]` and the second line is `start the loop`. This way the terminal title/tab shows which SquidSquad agent is running in that terminal (e.g. "🦑 skill — MyProject", "🦑 pm — MyProject"). Currently all agents send the same `"start the loop"` message, making terminal tabs indistinguishable.
- **Rationale**: When running multiple SquidSquad agents in separate terminals, there's no way to tell which tab is which agent at a glance. Terminal emulators typically show the command arguments in the tab title, so putting the role identifier in the first line of the message makes tabs self-identifying.
- **Acceptance Criteria**:
  - [ ] Boot script templates (`.sh` and `.ps1` for both dev and PM) send multi-line first message with `🦑 [role] — [project]` on line 1 and `start the loop` on line 2
  - [ ] CLAUDE.md auto-boot section updated to handle the new message format (still reads role from `.active-role`, ignores the first line)
  - [ ] Terminal tab/title shows the role identifier in Windows Terminal
  - [ ] SKILL.md boot script templates updated
  - [ ] Upgrade steps update existing boot scripts

### Discussion

> [2026-03-29 13:50] **pm/qa**: Filed from human request. Human wants terminal tabs to identify which SquidSquad role is running. Approach: change the first positional argument in boot scripts from `"start the loop"` to a two-line message with role on line 1. Status: Pending — awaiting human approval.
> [2026-03-29 15:30] **pm/qa**: Human wants role + project name (e.g. "🦑 skill — MyProject"). PM advised against ANSI escape sequences — Windows Terminal already picks up command arguments for tab title, ANSI escapes may conflict with Claude Code's own title management. Skip ANSI for now, add as follow-up if needed. Updated description and criteria.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
> [2026-04-02 11:25] **pm/qa**: Consolidated into FEAT-SKILL-061 (named sessions). Same goal — identify agents. 061 covers both Claude Code remote session names and terminal titles. Status → Consolidated.
