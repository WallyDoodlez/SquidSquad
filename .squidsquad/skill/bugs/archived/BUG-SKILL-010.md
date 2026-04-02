## BUG-SKILL-010 — Phase 2 (Discussion) dumps all questions at once instead of interactive flow

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The FEAT-SKILL-016 Feature Intake Process Phase 2 (Discussion) is supposed to be interactive — walking through questions one at a time with the human. But the current PM template doesn't specify the interaction format clearly enough, resulting in the PM dumping all research questions as a wall of text.

  The fix should specify that Phase 2 questions are presented **one at a time**, with each question formatted as:

  ```
  Q1: [Question text]
  Why this matters: [consequence of getting it wrong]

  (a) [Suggestion 1 — PM's recommended option]
  (b) [Suggestion 2 — alternative approach]
  (c) Type your own answer
  (d) Let's discuss this further

  Your choice:
  ```

  - If human picks (a) or (b): lock decision, move to next question
  - If human picks (c): human types freeform, PM captures it as a locked decision
  - If human picks (d): PM enters a longer back-and-forth discussion about this question until the human is satisfied, then locks the decision and moves on

  It's fine to present the full research summary first (Phase 1 output), but Phase 2 questions must be one-at-a-time interactive.

- **Steps to Reproduce**:
  1. Request a feature as human
  2. PM runs Phase 1 research
  3. PM enters Phase 2 — dumps all 7 questions with answers needed
- **Expected**: Questions presented one at a time with (a)(b)(c)(d) format
- **Actual**: All questions listed at once as a wall of text

### Discussion

> [2026-03-28 05:20] **pm/qa**: Found during first real test of FEAT-SKILL-016 (planning FEAT-SKILL-015). The research output is good — listing everything together first is fine. But the discussion phase needs to be truly interactive: one question at a time, two suggestions per question, option for freeform, option for deeper discussion.
> [2026-03-28 05:38] **skill-lead**: Fixed in agent-instructions.md Phase 2 section. Replaced generic numbered list with explicit one-at-a-time Q[N] format including (a)(b)(c)(d) options and handling rules for each response type. Added "Do NOT present all questions at once" directive. Status → Fixed.
> [2026-03-28 06:15] **pm/qa**: Verified. agent-instructions.md line 672 has "Do NOT present all questions at once" directive. Q[N] format with (a)(b)(c)(d) options confirmed at lines 653-670. Handling rules for each response type present. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
