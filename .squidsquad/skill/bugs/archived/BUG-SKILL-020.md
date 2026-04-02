## BUG-SKILL-020 — README.md not updated when features ship

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: Dev agent template Step 8 ("Update docs") requires updating README.md when user-facing behavior changes, but README has not been updated since BUG-SKILL-012. At least 3 shipped features are missing from README:
  1. **FEAT-SKILL-018** — Subagent delegation across planning phases (Phases 2A, 3, 5)
  2. **FEAT-SKILL-021** — Status bar chaining (SquidSquad appends to user's existing status bar)
  3. **FEAT-SKILL-022** — Silent quiet cycles (no text output on idle cycles)
- **Steps to Reproduce**:
  1. Read README.md
  2. Compare against CHANGELOG.md entries for FEAT-SKILL-018, 021, 022
- **Expected**: README documents all shipped user-facing features
- **Actual**: README is stale — missing at least 3 shipped features

### Discussion

> [2026-03-29 00:05] **pm/qa**: Reported by human. The doc-update step exists in the template but isn't being consistently followed by the skill agent. README should be brought up to date with all shipped features.
> [2026-03-29 12:05] **skill-lead**: Fixed. Added 5 missing feature sections to README: Subagent Delegation, Status Bar Chaining, Auto Versioning, Externalized Agent Templates, Open Planning Artifacts in VS Code. Updated Quiet Cycle Skipping to mention silent output. Status → Fixed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
