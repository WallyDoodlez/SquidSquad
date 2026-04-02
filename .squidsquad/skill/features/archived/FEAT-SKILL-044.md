## FEAT-SKILL-044 — Granular status phases with item names across all agents

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: Replace generic status phases with distinct, granular phases that include the specific item being worked on. The status bar should telegraph the real status — not just "verifying" but "verifying BUG-SKILL-029". Applies to all agent roles (PM, dev, future DM/QA). PM currently has generic phases (`pulling`, `checkin`, `testing`, `verifying`, `planning`, `health`, `idle`); these should be expanded with distinct phases like `researching`, `discussing`, `test-planning` for the Feature Intake flow. Dev agents should similarly include item names in all phases.
- **Current PM phases**: `pulling`, `checkin`, `testing`, `verifying`, `planning`, `health`, `idle`
- **Proposed PM additions**: `researching` (Phase 1), `discussing` (Phase 2), `test-planning` (Phase 3), plus item names in all existing phases (e.g. `verifying|Verifying BUG-SKILL-029...`)
- **Scope**: All agent CLAUDE.md templates, agent-instructions.md, statusline.sh (if phase display needs updating)
- **Acceptance Criteria**:
  - [ ] PM status phases expanded: `researching`, `discussing`, `test-planning` added as distinct phases
  - [ ] All PM status writes include item name (e.g. `verifying|Verifying BUG-SKILL-029...`, `researching|Researching FEAT-SKILL-035...`)
  - [ ] Dev agent status writes include item name (e.g. `implementing|🔨 FEAT-SKILL-037...`, `triaging|Fixing BUG-SKILL-029...`)
  - [ ] Future DM/QA templates follow the same pattern
  - [ ] statusline.sh handles new phase values correctly (display, colors if applicable)
  - [ ] SKILL.md templates updated with new phase vocabulary
  - [ ] agent-instructions.md updated with new phase examples

### Discussion

> [2026-03-30 00:05] **pm/qa**: Filed from human request. Human wants the status bar to "telegram the real status" — distinct phases with item names, not generic labels. Applies to all agents. Status: Pending — awaiting human approval.
> [2026-03-30 00:10] **pm/qa**: Human approved. Light mode — cosmetic/template change, no behavioral risk. Skipping Phase 1 (Research) and Phase 2A. Status → Planning. Beginning intake process.
> [2026-03-30 00:15] **pm/qa**: Phase 2 complete. Locked: all agents, distinct phases (researching/discussing/test-planning), uniform styling, per-item updates. Phase 3 complete — TEST-PLAN.md created (20 TCs, 9 smoke, 6 regression risks). Status → Approved.
> [2026-03-30 00:45] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-30 00:50] **skill-lead**: Implementation complete. Updated: references/agent-instructions.md (dev + PM templates — new phases, item names in all examples), live .squidsquad/pm/CLAUDE.md (phase list + Feature Intake phase writes), live .squidsquad/skill/CLAUDE.md (item names in examples). statusline.sh already handles unknown phases gracefully — no changes needed. All smoke tests passing. Status → Pending Test.
> [2026-03-30 01:30] **pm/qa**: QA verified — 19/19 verifiable TCs PASS, 9/9 smoke tests PASS. PM template has all 10 phases including researching/discussing/test-planning with item IDs. Dev template has item IDs in examples. statusline.sh handles new phases gracefully. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
