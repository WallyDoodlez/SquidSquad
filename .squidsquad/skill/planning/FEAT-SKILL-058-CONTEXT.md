# FEAT-SKILL-058 Context — Suppress PM Cycles During Active Planning Phases

## Scope

When PM is actively running a Feature Intake planning phase (Phase 1-3), cron-triggered Ralph Loop cycles perform only a silent pull + health check instead of a full cycle. Normal cycling auto-resumes when the planning artifact is written.

## Locked Decisions (human decided)

- **Silent pull + health check during suppression**: Not a full skip — still pull latest and check agent health, but no output, no tracker verification, no iteration log.
- **Applies to all planning phases**: Phase 1 (Research), Phase 2A (Discussion Prep), Phase 2 (Discussion), Phase 3 (Test Planning).
- **Auto-resume when artifact is written**: RESEARCH.md, PHASE2-PREP.md, CONTEXT.md, or TEST-PLAN.md being written clears the planning flag.

## Dev Discretion (dev agent can choose)

- How to detect active planning phase (working-state.md flag vs. checking for in-progress planning artifacts)
- Exact format of the suppression marker line
- Whether to write the suppressed cycle to current-state for statusline

## Side Effect Mitigations (required)

- Must still pull latest during suppressed cycles (agents need each other's commits)
- Must still check agent health (stalled agent detection shouldn't stop during planning)
- Must not affect other agents' cycles — only PM is suppressed

## Upgrade Path (required)

- N/A — internal PM template change only. No config changes, no new files, no migration needed.

## Out of Scope

- Suppressing dev or DM agent cycles
- Suppressing cycles for reasons other than active planning
