## FEAT-SKILL-022 — Silent message output for quiet/silent cycles

- **Priority**: Low
- **Owner**: skill-lead
- **Status**: Shipped
- **Description**: When the Ralph Loop runs a quiet cycle (no work done), the PM currently prints a short text message like `[🦑] Quiet cycle. Cycle N.` This still produces visible output in the conversation. The feature request is to make quiet cycles truly silent — either no output at all, or a minimal non-intrusive indicator that doesn't clutter the conversation.

- **Acceptance Criteria**:
  - [ ] Quiet cycles produce minimal or no visible output
  - [ ] Human can still tell the loop is running (e.g., via status bar, not conversation text)
  - [ ] PM and dev agent templates updated
  - [ ] Non-quiet cycles still print full step markers as before

### Discussion

> [2026-03-28 10:50] **pm/qa**: Filed from human request. Quiet cycles currently print text that clutters the conversation. Should be truly silent or minimal. Status: Pending — awaiting human approval.
> [2026-03-28 11:00] **pm/qa**: Human approved. Trivial feature — fast-tracking through planning. No research needed. Quiet cycles should produce no text output at all. The loop is still running (visible via status bar or git log). Status → Approved.
> [2026-03-28 11:08] **skill-lead**: Complete. Updated all 4 templates (agent-instructions.md dev + PM, skill/CLAUDE.md, pm/CLAUDE.md) — quiet cycles now produce no text output, skip silently to Done. Status → Pending Test.
> [2026-03-28 11:10] **pm/qa**: Verified. Dev template line 159 and PM template line 605 both say "Produce no text output — skip silently to Done." All 4 templates updated. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
