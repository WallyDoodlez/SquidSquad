## FEAT-SKILL-046 — Bug discussion flow: PM investigates and presents fix before filing to dev

- **Priority**: High
- **Status**: Shipped
- **Requested By**: human
- **Description**: Currently when a bug is identified (from test failures, human reports, or QA), PM files it directly to the dev agent's tracker with no discussion. The human has no chance to weigh in on the fix approach. This feature adds a discussion step: when a bug is mentioned or discovered, PM immediately investigates the root cause, presents the problem and proposed fix to the human, and asks if more discussion is needed. Only after the human is satisfied with the approach does PM file it to the dev agent.
- **Current Flow**: Bug discovered → PM files to dev tracker → Dev picks up and fixes however it sees fit
- **Proposed Flow**: Bug discovered → PM investigates root cause and possible fixes → PM presents problem + proposed fix to human → Human confirms or discusses further → PM files to dev tracker with the agreed-upon fix approach
- **Scope**: PM CLAUDE.md template, agent-instructions.md PM template (Steps 4, 2 — bug filing from test failures and human reports)
- **Acceptance Criteria**:
  - [ ] PM investigates the root cause when a bug is reported or discovered
  - [ ] PM presents the problem and proposed fix to the human before filing
  - [ ] Human can discuss the fix further or approve it
  - [ ] Only after human approval does the bug get filed to the dev tracker
  - [ ] Filed bug includes the agreed-upon fix approach in the Description or Discussion
  - [ ] Works for all bug sources: human reports, test failures, QA findings
  - [ ] PM CLAUDE.md template updated with bug discussion flow
  - [ ] agent-instructions.md PM template updated

### Discussion

> [2026-03-30 14:00] **pm/qa**: Filed from human request. Human wants a chance to discuss and steer bug fixes before they go to dev. Currently bugs go straight to dev with no human input on the approach. New flow: investigate → present → discuss → file. Status: Pending — awaiting human approval.
> [2026-03-31 00:05] **pm/qa**: Human approved. Light mode — PM template behavior change, low technical risk. Status → Planning. Beginning intake process.
> [2026-03-31 00:10] **pm/qa**: Phase 2 (no open questions) and Phase 3 complete. CONTEXT.md and TEST-PLAN.md created (11 TCs, 8 smoke, 6 regression risks). Status → Approved.
> [2026-03-31 00:15] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-31 00:20] **skill-lead**: Implementation complete. Updated PM template Steps 2 and 4 in both `references/agent-instructions.md` and live `.squidsquad/pm/CLAUDE.md`. Step 2 bug reports now use Bug Discussion Flow (investigate→present→discuss→file). Step 4 test failures use same flow. Non-blocking: PM notes "awaiting human input" and continues loop. All 8 smoke tests passing. Status → Pending Test.
> [2026-03-31 01:15] **pm/qa**: QA verified — 11/11 TCs PASS. Both templates updated, non-blocking confirmed, dev agent unchanged, no regressions. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
