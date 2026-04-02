## FEAT-SKILL-023 — Smart resume for interrupted planning — skip or re-research based on state

- **Priority**: Medium
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: When the Feature Intake Process is interrupted (e.g., context reset, PM restart) and planning resumes, the PM should intelligently handle already-completed phases:

  **Two scenarios:**

  1. **Research done but not yet committed/pushed**: RESEARCH.md exists locally but hasn't been pushed to git. On resume, PM should detect the file exists and **skip re-research automatically** — proceed directly to Phase 2.

  2. **Research done and already committed**: RESEARCH.md exists in git history. On resume (new context), PM should **ask the user via AskUserQuestion** whether to re-research (research may be stale or context may have changed) or reuse the existing RESEARCH.md.

  **Same logic applies to other planning artifacts:**
  - CONTEXT.md exists → skip Phase 2 discussion, go to Phase 3
  - TEST-PLAN.md exists → skip Phase 3, feature is ready for Approved

  **Implementation:**
  At the start of each planning phase, PM checks if the output artifact already exists:
  - If exists and uncommitted → skip phase silently
  - If exists and committed → ask user via AskUserQuestion: "RESEARCH.md already exists from a previous session. Re-research or reuse?"
  - If doesn't exist → run the phase normally

- **Acceptance Criteria**:
  - [ ] PM checks for existing planning artifacts before starting each phase
  - [ ] Uncommitted artifacts → skip phase automatically
  - [ ] Committed artifacts with no code changes since → auto-reuse silently
  - [ ] Committed artifacts with code changes since → AskUserQuestion prompt to re-run or reuse
  - [ ] Code change detection: `git log --oneline <artifact_commit>..HEAD -- references/ SKILL.md CHANGELOG.md` — if commits found, code changed
  - [ ] Works for RESEARCH.md, PHASE2-PREP.md, CONTEXT.md, TEST-PLAN.md
  - [ ] PM template in `references/agent-instructions.md` updated
  - [ ] Generated PM CLAUDE.md reflects the resume logic

### Discussion

> [2026-03-28 12:00] **pm/qa**: Filed from human request. Smart resume for interrupted planning — detect existing artifacts and either skip or ask user. Two behaviors: uncommitted = auto-skip, committed = prompt user. Status: Pending — awaiting human approval.
> [2026-03-29 21:10] **pm/qa**: Human approved. Refined staleness logic: auto-reuse if no code changes since artifact commit (check git log for commits touching references/, SKILL.md, CHANGELOG.md). Only ask user if code has changed since the artifact was created. Status → Approved.
> [2026-03-29 21:35] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 21:40] **skill-lead**: Complete. Added "Artifact Resume Logic" section to `references/agent-instructions.md` before Phase 1, defining the 3-case check (uncommitted→skip, committed+no changes→reuse, committed+changes→ask user). Added resume check references to all 4 phases (Phase 1, 2A, 2, 3). Updated CHANGELOG.md. Status → Pending Test.
> [2026-03-29 22:10] **pm/qa**: Verified all acceptance criteria. Artifact Resume Logic section defines 3 cases. All 4 phases have resume checks. Code change detection via git log on references/, SKILL.md, CHANGELOG.md. CHANGELOG updated. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
