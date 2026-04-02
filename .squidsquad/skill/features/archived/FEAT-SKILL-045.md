## FEAT-SKILL-045 — Overdue emoji on status bar when loop iteration is delayed

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: When an agent's Ralph Loop cycle runs longer than the configured iteration interval (e.g. 30 minutes) because it's blocked on work (long Feature Intake discussion, big implementation, etc.), show an overdue emoji in the statusline next to the countdown timer. This gives the human an at-a-glance indicator that an agent is running long and the next cycle is delayed.
- **Behavior**:
  - Overdue triggers immediately when elapsed time exceeds the iteration interval (no grace period)
  - Emoji appears at/near the countdown timer position in the statusline
  - Applies to all agents (PM, dev, future DM/QA)
  - When not overdue, no indicator shown (clean default state)
- **Acceptance Criteria**:
  - [ ] statusline.sh detects when an agent's current cycle has exceeded the iteration interval
  - [ ] Overdue emoji displayed next to the countdown/timer area when interval exceeded
  - [ ] Works for all agent roles
  - [ ] No indicator shown when cycle is within normal interval
  - [ ] Triggers immediately at interval boundary (no grace period)
  - [ ] SKILL.md statusline documentation updated
  - [ ] agent-instructions.md statusline section updated

### Discussion

> [2026-03-30 00:20] **pm/qa**: Filed from human request. Human wants visibility into when agents are running long. Overdue emoji at the countdown timer, all agents, immediate trigger at interval boundary. Status: Pending — awaiting human approval.
> [2026-03-30 00:25] **pm/qa**: Human approved. Light mode — statusline-only change, low risk. Skipping Research + Phase 2A. No open questions (behavior fully specified). CONTEXT.md and TEST-PLAN.md to follow. Status → Planning.
> [2026-03-30 00:35] **pm/qa**: Phase 2 (no open questions) and Phase 3 complete. CONTEXT.md and TEST-PLAN.md created (13 TCs, 9 smoke, 5 regression risks). Status → Approved.
> [2026-03-30 02:00] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-30 02:10] **skill-lead**: Implementation complete. Modified statusline.sh timer logic: when REMAINING <= 0, shows ⏰ +Nm (overdue by N minutes) instead of 🔜 <1m. Applies to all roles (shared timer section). Updated SKILL.md and agent-instructions.md docs. All smoke tests pass. Delivery notes: overdue emoji (⏰) appears when agent cycle exceeds iteration interval, shows overage time (+Nm), triggers at boundary with no grace period. Status → Pending Test.
> [2026-03-30 02:30] **pm/qa**: QA verified — 13/13 TCs PASS. Overdue emoji ⏰ +Nm at REMAINING<=0, all roles use shared TIMER_STR, boundary correct, clean default, docs updated in SKILL.md and agent-instructions.md. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
