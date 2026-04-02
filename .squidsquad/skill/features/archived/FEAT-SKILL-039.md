## FEAT-SKILL-039 — Slash command to change loop interval on the fly

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: Add a `/squidsquad-interval` slash command that changes the Ralph Loop interval for the current agent mid-session. Currently the interval is set at setup and baked into the cron job on startup — changing it requires manually editing config.md and restarting. The command should update config.md, cancel the existing cron, and create a new one with the new interval. Usage: `/squidsquad-interval 3m` or `/squidsquad-interval 10m`.
- **Rationale**: During active development the human may want faster cycles (2-3m), during quiet periods slower cycles (10-15m). Changing this should be instant without restarting agents.
- **Acceptance Criteria**:
  - [ ] New slash command `/squidsquad-interval <Nm>` defined in SKILL.md
  - [ ] Command updates `Iteration Interval > Minutes` in config.md
  - [ ] Command cancels existing cron job (CronDelete) and creates new one (CronCreate) with new interval
  - [ ] Validates input (integer >= 1, suffix m)
  - [ ] Prints confirmation with old and new interval
  - [ ] Works for both PM and dev agents
  - [ ] All agents detect interval change at cycle start and re-schedule (no restart needed)
  - [ ] Minimum 5 minutes enforced, no max
  - [ ] SKILL.md documents the command

### Discussion

> [2026-03-29 18:50] **pm/qa**: Filed from human request. Human approved immediately. Status → Planning. Beginning intake process.
> [2026-03-29 18:55] **pm/qa**: Light-mode intake complete. Decisions locked: (D1) all agents immediately via file-based signal, (D2) minimum 5 minutes. CONTEXT.md and TEST-PLAN.md (17 tests) created. Status → Approved.
> [2026-03-29 19:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 19:05] **skill-lead**: Complete. Added `/squidsquad-interval` slash command section to SKILL.md
> [2026-03-29 19:05] **pm/qa**: Verified all acceptance criteria. Slash command in SKILL.md with validation (>= 5, optional m suffix), config.md update, CronDelete+CronCreate. Step 1d (Interval Sync) in agent-instructions.md, skill/CLAUDE.md, and pm/CLAUDE.md. CHANGELOG updated. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
