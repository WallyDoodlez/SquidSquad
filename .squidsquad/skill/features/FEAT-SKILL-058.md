## FEAT-SKILL-058 — Suppress PM cycles during active planning phases

- **Priority**: High
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: When PM is actively running a Feature Intake planning phase (Phase 1 Research, Phase 2A Discussion Prep, Phase 2 Discussion, Phase 3 Test Planning), cron-triggered Ralph Loop cycles should be suppressed to avoid noisy interruptions. Instead of a full cycle, suppressed cycles perform only a silent `git pull --rebase` and agent health check with no output. Normal cycling auto-resumes when the planning phase completes (detected by the corresponding artifact being written: RESEARCH.md, PHASE2-PREP.md, CONTEXT.md, or TEST-PLAN.md).

  **Implementation approach:**
  - PM writes a planning phase flag to `working-state.md` (e.g., `**Phase**: discussing FEAT-SKILL-030`) when entering any planning phase.
  - On cycle start (Step 1c), PM checks working state — if a planning phase is active, perform silent pull + health check only, then skip remaining steps.
  - When the planning artifact is written, PM clears the phase flag and resumes normal cycling.
  - Suppressed cycles print a single-line marker: `[🦑] ---- cycle N (suppressed — active planning phase) ----`

- **Acceptance Criteria**:
  - [ ] PM writes planning phase flag to working-state.md when entering Phase 1, 2A, 2, or 3
  - [ ] Cron-triggered cycles during active planning perform silent pull + health check only
  - [ ] No tracker verification, no feature/bug checks, no iteration log during suppressed cycles
  - [ ] Suppressed cycles print a single-line suppression marker
  - [ ] Normal cycling auto-resumes when the planning artifact (RESEARCH.md, CONTEXT.md, TEST-PLAN.md) is written
  - [ ] Phase flag is cleared from working-state.md when planning completes

### Discussion

> [2026-04-02 05:30] **pm/qa**: Filed from human request during FEAT-SKILL-030 Phase 2 discussion.
> [2026-04-02 08:45] **pm/qa**: Human approved. Status → Planning. Light-mode intake (trivial/internal feature). Skipping Phase 1 Research. Proceeding to abbreviated Phase 2 + Phase 3.
> [2026-04-02 08:50] **pm/qa**: Phase 2 (light mode) — all decisions locked at filing time, no open questions. CONTEXT.md written. Phase 3 — TEST-PLAN.md generated (12 TCs, 3 smoke tests, 4 regression risks). Planning complete. Status → Approved. Ready for skill-lead pickup. Human experienced repeated cycle interruptions during interactive planning and requested suppression. Locked decisions: (1) silent pull + health check during suppression (not full skip), (2) applies to all planning phases (1-3), (3) auto-resume when artifact is written. Internal-only process improvement — delivery:skip candidate.
> [2026-04-02 09:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-04-02 09:15] **skill-lead**: Implementation complete.
> [2026-04-02 09:45] **pm/qa**: Verified. 6/6 acceptance criteria pass. Phase flag set/clear in all 4 planning phases. Suppressed cycles do silent pull + health check only. Single-line marker printed. Auto-resume on artifact write. delivery: skip (internal-only, no user-facing changes). Status → Pending Ship. Added planning phase suppression to PM template Step 1c (suppressed cycles do silent pull + health check, print single-line marker). Added phase flag set/clear to all 4 planning phases in feature-intake sub-skill. Regenerated agent-instructions.md. All tests passing. Status → Pending Test.
> [2026-04-02 07:30] **dm**: No delivery work needed (delivery: skip). Status → Shipped.
