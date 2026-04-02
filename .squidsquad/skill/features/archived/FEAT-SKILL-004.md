## FEAT-SKILL-004 — PM/QA agent must never implement code directly

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: The PM/QA agent should be explicitly prohibited from implementing code or making direct changes to skill files, application code, or any non-tracker files. When PM/QA identifies something that needs changing, it must always file a bug or feature request to the appropriate dev agent's tracker instead of making the change itself. This should be enforced in both the PM/QA CLAUDE.md template (in `references/agent-instructions.md`) and the generated PM CLAUDE.md files.
- **Acceptance Criteria**:
  - [ ] PM/QA CLAUDE.md template in `references/agent-instructions.md` explicitly states PM/QA must never implement code changes
  - [ ] "What You Must Never Do" section includes: "Never implement fixes or features directly — always file to the appropriate agent's bug or feature tracker"
  - [ ] Ralph Loop steps reinforce this: if PM/QA finds an issue during QA, it files a bug rather than fixing it
  - [ ] Generated `pm/CLAUDE.md` files include this constraint

### Discussion

> [2026-03-27 23:05] **pm/qa**: Filed from human request. PM/QA's role is coordination and verification, not implementation. Any code-level fix must go through a dev agent's tracker.
> [2026-03-27 23:10] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 00:35] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 00:40] **skill-lead**: Complete. Added "never implement code directly" to PM/QA Responsibilities, "What You Must Never Do" in both the template (`references/agent-instructions.md`) and the generated `pm/CLAUDE.md`. Status → Pending Test.
> [2026-03-27 23:35] **pm/qa**: QA verified — all 4 criteria confirmed. Template (lines 214, 438), generated pm/CLAUDE.md (lines 20, 150) both have the constraint. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
