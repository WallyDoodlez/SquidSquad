## FEAT-SKILL-043 — Separate QA from PM into its own hardcoded agent role

- **Priority**: High
- **Status**: Pending
- **Requested By**: human
- **Description**: Split the current PM/QA agent into two distinct hardcoded roles:

  **PM (Product Manager)** — the talker. Owns:
  - Human check-ins and communication
  - Feature intake process (Phases 1-3: research, discussion, test plan)
  - Backlog management, priority changes
  - Feature filing from human input
  - Version bump decisions

  **QA (Quality Assurance)** — the tester. Owns:
  - QA coherence pass (reading skill files for issues)
  - Bug verification (Fixed → Verified → Closed)
  - Feature testing (Pending Test → Shipped)
  - Agent health checks
  - Filing bugs from QA findings

  PM does NO testing. PM is primarily the interface between the human and the squad. QA runs its own Ralph Loop independently, testing and verifying work.

- **Rationale**: PM's context gets consumed by QA work (reading lots of files for coherence checks, verifying features against acceptance criteria). Splitting them keeps PM lean and focused on human interaction. QA can run at its own pace with its own interval.
- **Acceptance Criteria**:
  - [ ] QA is a hardcoded role (always present, like PM), not user-configured
  - [ ] QA has its own Ralph Loop template in `references/agent-instructions.md`
  - [ ] QA has its own boot script (`start-qa.sh` / `start-qa.ps1`)
  - [ ] QA owns: QA pass, bug verification, feature testing, agent health checks, filing bugs
  - [ ] PM owns: human check-ins, feature intake, backlog management, priority changes, version bumps
  - [ ] PM does NO testing or verification — hands off after Phase 3
  - [ ] PM is primarily the human-facing conversational agent
  - [ ] QA has its own tracker directory (`.squidsquad/qa/`) or shares PM's trackers (design decision)
  - [ ] QA can have its own loop interval independent of PM
  - [ ] Setup generates QA agent alongside PM automatically
  - [ ] SKILL.md updated with QA role definition, templates, boot scripts
  - [ ] Upgrade steps add QA to existing installs

### Discussion

> [2026-03-29 22:15] **pm/qa**: Filed from human request. Human wants PM to be "primarily the talker" — no testing. QA becomes its own hardcoded agent that runs independently. Key design decisions needed: does QA share PM's trackers or have its own? Does QA report findings to PM (who relays to human) or directly to dev agents? How does version bump work — PM decides but QA provides the ship count?
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
