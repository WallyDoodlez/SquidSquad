## FEAT-SKILL-003 — PM status bar shows iteration number and squid emoji

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Add a Claude Code status line for all SquidSquad agents using the `statusLine` setting in `settings.json`. The status line gives the human a quick glance at squad activity without reading logs. Uses ANSI colors for state indication (animation not supported — status line only refreshes on assistant messages).
- **Acceptance Criteria**:
  - [ ] A `statusLine` command/script is configured in `.claude/settings.json` (or generated during setup)
  - [ ] Status line shows agent role label (e.g. `PM/QA`, `skill`)
  - [ ] Status line shows current iteration number (read from latest `iter-N.md`)
  - [ ] Status line shows squid emoji `🦑` in green (ANSI) when agent is active
  - [ ] PM status line shows other agents' health: `🦑` green if pushed recently, `🦑✖` red if silent for N+ cycles
  - [ ] Status line shows time since last cycle started
  - [ ] Status line shows open bug/feature counts as a backlog pulse (e.g. `2 bugs 1 feat`)
  - [ ] SKILL.md setup steps updated to generate the status line script and configure settings.json
  - [ ] PM and dev agent CLAUDE.md templates updated to document status line behavior

### Discussion

> [2026-03-27 22:40] **pm/qa**: Filed from human request. Status: Pending — awaiting human approval.
> [2026-03-27 22:50] **pm/qa**: Updated scope after research. Animation not feasible (status line only refreshes on events, no timer). Revised to use ANSI color-based state indicators instead. Added agent health monitoring, cycle timer, backlog counts, and coverage for all agents (not just PM). Human approved. Status → Approved.
> [2026-03-28 00:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 00:15] **skill-lead**: Complete. Created `.squidsquad/statusline.sh` with role detection, iteration tracking, backlog pulse, PM agent health, and ANSI coloring. Updated `settings.json` template with `statusLine` config. Updated SKILL.md Step 5b and Step 7. Updated dev and PM/QA CLAUDE.md templates with Status Line section. CHANGELOG updated. Status → Pending Test.
> [2026-03-27 23:15] **pm/qa**: QA verified — all 9 acceptance criteria pass. However, statusline.sh discards JSON stdin (context window %, repo info) — filed as BUG-SKILL-004. Status → Shipped (with caveat).
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
