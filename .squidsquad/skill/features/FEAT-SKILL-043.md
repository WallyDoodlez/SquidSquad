## FEAT-SKILL-043 — Separate QA from PM into its own hardcoded agent role

- **Priority**: High
- **Status**: Pending Ship
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
> [2026-04-02 09:30] **pm/qa**: Human approved with major scope revision.
> [2026-04-02 10:00] **pm/qa**: Phase 2 Discussion complete.
> [2026-04-02 10:30] **skill-lead**: Picking up. Status → In Progress.
> [2026-04-02 11:00] **skill-lead**: Implementation complete. Created QA role sub-skill (roles/qa-agent.md) with verification sub-skill (qa-specific/verification.md). Created PM lean template (roles/pm-lean.md) — PM without verification steps. PM lean uses `**pm**` signature instead of `**pm/qa**`. QA owns: E2E tests, bug verification, feature testing, health checks, PR monitoring. PM lean keeps: human check-in, feature intake, delivery fallback, GitHub Issues. Setup selects pm-agent.md or pm-lean.md based on QA presence. agent-instructions.md now has 6 templates (dev, PM full, PM lean, QA, designer, DM). All smoke tests passing. Status → Pending Test.
> [2026-04-02 11:30] **pm/qa**: Verified. 12/12 checks pass. QA sub-skill files (2), PM lean template exists, 6 templates in composed output, QA section marker, correct signatures (pm vs qa), manifest updated with selection logic, QA Ralph Loop owns all verification, PM lean drops verification, PM lean keeps intake. Composed template 2975 lines. Status → Pending Ship.
> [2026-04-02 10:15] **pm/qa**: Phase 3 complete — TEST-PLAN.md generated (34 TCs, 4 sections). Planning phases complete. Status → Approved. Ready for skill-lead pickup. — 5 open questions resolved. Locked: same discovery as dev/DM, global interval, new qa/qa-log.md, NO PM fallback (QA presence expected once introduced), direct bug filing for objective failures. Key human insight: "once QA is introduced we expect its presence — like hiring someone." CONTEXT.md written. Human approved Phase 2 gate. Status → Planning. Revised pipeline: Human → PM (intake, planning, discussions) → Dev/Designer (build) → QA (verify across all agents) → DM (docs, release) → Ship. Key changes from original spec: (1) QA is NOT hardcoded/always-present — it's a recommended role when dev/designer exists, (2) ONE QA agent verifies work across ALL dev and designer agents (not per-agent), (3) QA hands verified work to DM (if exists) for docs/release, NOT back to PM, (4) if DM absent, PM takes over DM delivery role (existing fallback pattern), (5) PM does zero verification — purely human interface + coordination. Beginning Phase 1 Research.
