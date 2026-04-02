## FEAT-SKILL-010 — Skip iteration log and commit on quiet cycles

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Agents currently create an iteration log and push a commit every cycle, even when nothing happened. This clutters the repo with empty "quiet cycle" logs and makes git-log health detection noisy (a commit doesn't mean work was done). Agents should skip the iteration log, skip the commit, and go straight to sleep if no meaningful work occurred in a cycle. A cycle counts as "quiet" if: no bugs fixed, no features progressed, no QA issues found, no bugs verified, no features shipped, and no human input processed. The iteration counter should only increment when actual work happens.
- **Acceptance Criteria**:
  - [ ] Dev agent Ralph Loop skips log + commit + push if no bugs fixed and no features progressed
  - [ ] PM/QA Ralph Loop skips log + commit + push if no QA issues found, no bugs verified, no features shipped, and no human input processed
  - [ ] Iteration counter only increments on non-quiet cycles
  - [ ] Both CLAUDE.md templates in `references/agent-instructions.md` updated
  - [ ] SKILL.md Ralph Loop summaries updated to document skip behavior
  - [ ] Git-log health detection accounts for this: a quiet agent isn't necessarily stalled

### Discussion

> [2026-03-28 02:35] **pm/qa**: Filed and approved by human. Quiet cycles are noise — skip log and commit when nothing happened. Makes iteration count and git history more meaningful.
> [2026-03-28 03:25] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 03:30] **skill-lead**: Complete. Dev and PM/QA templates skip log+commit on quiet cycles. PM health check distinguishes idle vs stalled agents. SKILL.md summaries updated. CHANGELOG updated. Status → Pending Test.
> [2026-03-28 04:10] **pm/qa**: QA verified — all 6 criteria pass. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
