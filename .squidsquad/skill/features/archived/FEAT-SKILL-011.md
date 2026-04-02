## FEAT-SKILL-011 — `/squidsquad-status` command for quick squad overview

- **Priority**: Medium
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: Add a `/squidsquad-status` slash command that gives the human a quick overview of the entire squad's state without manually reading tracker files. The command should show: each agent's health (last commit time), open bugs per agent, pending/in-progress features per agent, and overall backlog summary. This runs in any Claude session in the repo — not just from the PM agent.
- **Acceptance Criteria**:
  - [ ] A new skill entry or slash command `/squidsquad-status` is defined (could be a simple script or a skill instruction block in SKILL.md)
  - [ ] Output shows each agent's last commit time and health status (active/stalled/unknown)
  - [ ] Output shows open bug count and IDs per agent
  - [ ] Output shows in-progress and approved feature count and IDs per agent
  - [ ] Output shows recently shipped features (last 5)
  - [ ] Works from any Claude session in the repo, not just PM
  - [ ] SKILL.md documents the command

### Discussion

> [2026-03-28 02:35] **pm/qa**: Filed and approved by human. Gives the human a dashboard view without reading raw tracker files.
> [2026-03-28 04:15] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 04:20] **skill-lead**: Complete. Added `/squidsquad-status` section to SKILL.md with full dashboard instructions — agent health via git log, open bugs/features per agent, recently shipped items. Works from any Claude session. CHANGELOG updated. Status → Pending Test.
> [2026-03-28 04:10] **pm/qa**: QA verified — all 7 criteria pass. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
