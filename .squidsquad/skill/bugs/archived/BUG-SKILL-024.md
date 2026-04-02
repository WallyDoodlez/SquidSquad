## BUG-SKILL-024 — PM asks "approve?" immediately after filing a feature instead of opening discussion

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: When the PM files a new feature request from human input, it immediately asks "Want me to approve it?" This skips the discussion phase entirely. Instead, after filing a feature the PM should: (1) predict what the human likely wants from the feature based on context, (2) surface those predictions and open-ended questions, and (3) invite the human to discuss before any approval happens. The current behavior rushes to approval and misses the opportunity to refine scope, surface edge cases, and align on approach.
- **Steps to Reproduce**:
  1. Tell PM a feature request (e.g. "show current step in status bar")
  2. PM files FEAT-SKILL-XXX
  3. PM immediately says "Want me to approve it?"
- **Expected**: After filing, PM should present predictions about what the human wants, ask clarifying questions, and invite discussion. Approval comes later after the conversation.
- **Actual**: PM jumps straight to "Want me to approve it?" with no discussion.

### Discussion

> [2026-03-29 14:00] **pm/qa**: Filed from human report. Human says PM should never ask to approve right after creation — should always open a conversation first. PM should predict what the user wants, present those predictions, and invite the human to comment before approval is even mentioned. This is a behavioral issue in the PM CLAUDE.md template's Step 2 guidance and/or the agent-instructions.md Feature Intake Process.

> [2026-03-29 14:15] **skill-lead**: Fixed in agent-instructions.md Step 2 and SKILL.md PM loop summary. Changes: (1) Step 2 "feature request" handler now explicitly requires predict→surface questions→invite discussion before filing, (2) Phase 3 approval prompt now states it is the *only* point where approval should be offered, (3) SKILL.md PM loop outline updated to reflect discuss-first flow. Status → Fixed.
> [2026-03-29 16:45] **pm/qa**: Verified. agent-instructions.md Step 2 now has 4-step process (predict→surface questions→invite discussion→file). Phase 3 approval explicitly marked as "only" point for approval. SKILL.md PM loop summary updated. Fix is correct and complete. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
