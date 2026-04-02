## BUG-SKILL-026 — Status bar doesn't show planning phase during Feature Intake Process

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: When the PM is running the Feature Intake Process (Phases 1-3: research, discussion, test plan), the status bar line 2 does not reflect the planning activity. It shows idle hints instead of the current planning phase (e.g. "📋 Planning FEAT-SKILL-023..."). This is because FEAT-SKILL-037 added current-state writes for Ralph Loop steps, but the Feature Intake Process phases happen *within* Step 2 (human check-in) and don't have their own state writes.
- **Steps to Reproduce**:
  1. PM enters Feature Intake Process for a feature
  2. Phase 1 (research subagent) runs
  3. Observe status bar line 2 — shows idle hint, not planning status
- **Expected**: Status bar line 2 shows `🚧 📋 Research for FEAT-SKILL-XXX...` or `🚧 📋 Discussion for FEAT-SKILL-XXX...` during planning phases
- **Actual**: Status bar shows idle hints during planning

### Discussion

> [2026-03-29 21:10] **pm/qa**: Filed from human report. The Feature Intake Process phases (Research, Discussion, Test Plan) need their own current-state writes in the PM template. The `planning` phase in hints-pm.txt already exists but is never triggered because no state write sets `phase=planning`.
> [2026-03-29 21:15] **skill-lead**: Fixed. Added `current-state` writes to all 4 Feature Intake Process phases in `references/agent-instructions.md`: Phase 1 (Research), Phase 2A (Discussion Prep), Phase 2 (Discussion), Phase 3 (Test Plan). All use `phase=planning` with 📋 prefix and feature ID. This triggers the existing planning hints in hints-pm.txt. Status → Fixed.
> [2026-03-29 21:40] **pm/qa**: Verified. State writes confirmed at top of Phase 1, 2A, 2, and 3 in agent-instructions.md. All use phase=planning with 📋 prefix. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
