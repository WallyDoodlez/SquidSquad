## FEAT-SKILL-040 — Explicit approval gate after Phase 2 discussion before proceeding to Phase 3

- **Priority**: Medium
- **Status**: Shipped
- **Requested By**: human
- **Description**: After all Phase 2 interactive questions are completed and CONTEXT.md is written, PM should present an explicit confirmation prompt via AskUserQuestion before moving to Phase 3 (test plan). Options: "Approve — proceed to test plan", "More discussion needed", or "Reject this feature". Currently PM moves directly from Phase 2 to Phase 3 without a final check, which means the human can't pause to reconsider or add more context after seeing the full picture of locked decisions.
- **Rationale**: The Phase 2 discussion can cover many questions quickly. After all decisions are locked, the human should see a summary of what was decided and explicitly confirm they're ready to proceed. This prevents the PM from rushing into Phase 3 when the human might want to revisit a decision or add something they forgot.
- **Acceptance Criteria**:
  - [ ] After Phase 2 discussion completes and CONTEXT.md is written, PM uses AskUserQuestion to confirm
  - [ ] Options: "Approve — proceed to test plan" / "More discussion needed" / "Reject feature"
  - [ ] "More discussion" re-opens Phase 2 — PM asks what the human wants to revisit
  - [ ] "Reject" sets feature status to Rejected with reason
  - [ ] Confirmation includes a summary of locked decisions from CONTEXT.md
  - [ ] `references/agent-instructions.md` Phase 2 updated with the gate

### Discussion

> [2026-03-29 21:15] **pm/qa**: Filed from human request. Human wants an explicit checkpoint between Phase 2 and Phase 3 to confirm all decisions before test planning begins. Status: Pending — awaiting human approval.
> [2026-03-29 21:15] **pm/qa**: Human approved. Straightforward — add AskUserQuestion gate at end of Phase 2 in agent-instructions.md. Status → Approved.
> [2026-03-29 21:45] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-29 21:45] **skill-lead**: Complete. Added "Phase 2 Approval Gate" to `references/agent-instructions.md` between CONTEXT.md creation and Phase 3. PM presents summary of locked decisions via AskUserQuestion with 3 options: Approve, More discussion, Reject. Updated CHANGELOG.md. Status → Pending Test.
> [2026-03-29 22:40] **pm/qa**: Verified all 6 acceptance criteria. Approval gate added between Phase 2 and Phase 3 with AskUserQuestion, 3 options (Approve/More discussion/Reject), locked decision summary, re-open and reject flows. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
