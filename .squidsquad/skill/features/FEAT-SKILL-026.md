## FEAT-SKILL-026 — `/squidsquad-pending` slash command to list pending items from tracker

- **Priority**: Medium
- **Owner**: skill-lead
- **Status**: Pending
- **Description**: Create a `/squidsquad-pending` slash command that reads the actual tracker files and displays a summary of all pending work. This prevents stale answers from memory — the command always reads the live files. Should show: pending features (awaiting approval), approved features (ready for dev), open bugs, features pending test, and any items in Planning status.

- **Acceptance Criteria**:
  - [ ] `/squidsquad-pending` command defined in SKILL.md
  - [ ] Command reads `[role]/features.md` and `[role]/bugs.md` for all agents
  - [ ] Output groups items by status: Pending, Planning, Approved, In Progress, Pending Test, Open bugs
  - [ ] Each item shows ID, title, priority, and owner
  - [ ] Empty groups are omitted from output
  - [ ] Works from any Claude session (not just PM/QA)

### Discussion

> [2026-03-29 01:15] **pm/qa**: Filed from human feedback. PM answered "what's pending" from conversation memory and gave stale data. A slash command ensures the tracker files are always read fresh. Status: Pending — awaiting human approval.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
