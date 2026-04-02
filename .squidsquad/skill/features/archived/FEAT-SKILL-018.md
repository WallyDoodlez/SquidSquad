## FEAT-SKILL-018 — All planning phases should maximize subagent usage

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: The 5-phase Feature Intake Process (FEAT-SKILL-016) should leverage Claude Code subagents (via the Agent tool) as much as possible across all phases. Currently Phase 1 (Research) spawns a research agent, but the other phases run inline. The PM should delegate heavy lifting to subagents wherever feasible:

  **Potential subagent usage per phase:**
  1. **Phase 1 (Research)** — Already uses a research subagent ✅
  2. **Phase 2 (Discussion)** — Could spawn an agent to prepare question recommendations and option analysis before presenting to human
  3. **Phase 3 (Planning)** — Could spawn an agent to draft the TEST-PLAN.md and feature entry based on locked decisions
  4. **Phase 4 (Execution)** — Dev agent already handles this
  5. **Phase 5 (QA)** — Could spawn an agent to do the file-level verification pass

  Benefits: reduces context pressure on the main PM agent, enables parallel work, and keeps the PM's context window focused on coordination rather than deep file reads.

- **Acceptance Criteria**:
  - [ ] All 5 phases documented with explicit subagent delegation where applicable
  - [ ] PM template in `references/agent-instructions.md` updated with subagent spawn instructions per phase
  - [ ] Phases that remain inline have documented rationale (e.g., Phase 2 discussion must be interactive with human)
  - [ ] Generated PM CLAUDE.md reflects the subagent approach

### Discussion

> [2026-03-28 06:50] **pm/qa**: Filed from human request. Human wants maximum subagent delegation across all planning phases to reduce PM context pressure and enable parallel work. Status: Pending — awaiting human approval.
> [2026-03-28 11:30] **pm/qa**: Human approved. Status → Planning. Beginning intake process. Running Phase 1 (Research).
> [2026-03-28 11:40] **pm/qa**: Phase 1 (Research) complete. Phase 2 (Discussion) complete — 5 questions resolved. Phase 3 (Planning) complete — CONTEXT.md + TEST-PLAN.md written. Status → Approved.
> [2026-03-28 11:50] **skill-lead**: Complete. Added Phase 2A (prep subagent), updated Phase 3 (test plan subagent), updated Phase 5 (QA subagent) in agent-instructions.md. Light mode skips Phase 2A. PM writes feature entries and makes final decisions. Generated pm/CLAUDE.md updated with subagent delegation note. Status → Pending Test.
> [2026-03-28 12:00] **pm/qa**: QA verified — all 4 acceptance criteria pass. Phase 2A, 3, 5 have subagent prompts in agent-instructions.md. Phase 2 stays inline (interactive). Generated pm/CLAUDE.md references subagent delegation. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
