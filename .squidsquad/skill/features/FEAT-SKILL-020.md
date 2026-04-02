## FEAT-SKILL-020 — Web-based UI for SquidSquad interaction

- **Priority**: Low
- **Owner**: TBD
- **Status**: Pending
- **Description**: Build a web-based interface for interacting with SquidSquad without directly using the Claude CLI. Claude remains the engine powering the agents, but all human interaction (filing bugs, approving features, answering Phase 2 questions, viewing status, etc.) happens through a web UI.

  **This is a large item requiring significant planning and scoping.** Recorded for now — not ready for implementation planning.

  **High-level vision:**
  - Dashboard showing agent health, open bugs/features, shipped counter, version info
  - Feature request form → files to tracker
  - Bug report form → files to tracker
  - Phase 2 discussion UI (interactive questions)
  - Status/progress view per feature lifecycle
  - Approval workflow via UI instead of CLI conversation
  - Claude API as backend engine — agents still run via Claude Code, UI is the coordination layer

- **Acceptance Criteria**: TBD — requires scoping phase before detailed criteria can be written.

### Discussion

> [2026-03-28 09:30] **pm/qa**: Filed from human request. Large item — web UI for all SquidSquad interaction with Claude as engine. Human noted this needs more planning and scoping. Recorded for future consideration. Status: Pending — awaiting human approval.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
