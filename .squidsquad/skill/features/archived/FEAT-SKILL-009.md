## FEAT-SKILL-009 — Iteration log retention — keep last 20, delete older

- **Priority**: Low
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: The `iterations/` folders grow indefinitely as agents cycle. Old iteration logs have minimal value — the real record is in git commits and tracker Discussion entries. Add a cleanup step at the start of each Ralph Loop cycle: if more than 20 iteration files exist, delete the oldest ones. Git history preserves them if ever needed.
- **Acceptance Criteria**:
  - [ ] Ralph Loop for dev agents includes a cleanup step: if `iterations/` has more than 20 `iter-*.md` files, delete the oldest ones
  - [ ] Ralph Loop for PM/QA includes the same cleanup step
  - [ ] Both CLAUDE.md templates in `references/agent-instructions.md` include the cleanup step
  - [ ] Retention limit (20) is documented in SKILL.md
  - [ ] Deleted files are committed as part of the normal cycle commit

### Discussion

> [2026-03-28 02:30] **pm/qa**: Filed and approved by human. Simple approach — old logs are in git history, no need for archive files. Keep last 20 (~1.5 hours at 5min interval). Status → Approved.
> [2026-03-28 03:10] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 03:15] **skill-lead**: Complete. Added cleanup step to both dev and PM/QA templates and generated CLAUSE.md files. Documented retention limit (20) in SKILL.md. Updated CHANGELOG. Status → Pending Test.
> [2026-03-28 03:15] **pm/qa**: QA verified — all 5 criteria pass. Cleanup in both templates, retention documented in SKILL.md. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
