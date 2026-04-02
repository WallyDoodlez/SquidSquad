## BUG-SKILL-015 — Phase 2 discussion should present all questions at once, then let human respond naturally

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: BUG-SKILL-010 introduced a one-at-a-time (a)(b)(c)(d) format for Phase 2 discussion questions. In practice this is too rigid — it blocks the PM loop waiting for individual answers and doesn't leverage Claude's natural conversation flow.

  The correct approach is a **two-part flow**:

  **Part 1 — Overview**: Present the full research summary AND all open questions together in a single output, so the human sees the full picture upfront.

  **Part 2 — Interactive walk-through**: Immediately start walking through questions one at a time. Each question gets 3 suggestions (PM's recommendations based on research) plus a "discuss more" option. Human picks one or types freeform. PM locks the decision, moves to next question.

  **Current (broken):**
  ```
  Q1: [question] ... (a)(b)(c)(d) Your choice:
  [wait — human never saw Q2-Q7]
  ```

  **Expected:**
  ```
  [Research summary]

  Open questions:
  Q1: [question] — Why it matters: [risk]
  Q2: [question] — Why it matters: [risk]
  ...Q7: [question] — Why it matters: [risk]

  Let's walk through these one at a time.

  Q1: [question]
  Why this matters: [consequence]

  (a) [Suggestion 1 — recommended]
  (b) [Suggestion 2]
  (c) [Suggestion 3]
  (d) Let's discuss this more

  Your choice:
  ```

  Key difference from BUG-010: the human sees ALL questions listed first for context, THEN the interactive walk-through begins with 3 suggestions (not 2) per question plus a discuss option.

- **Steps to Reproduce**:
  1. Approve a feature for planning
  2. PM runs Phase 1 research
  3. PM enters Phase 2 — presents Q1 with (a)(b)(c)(d) and waits
- **Expected**: All questions presented at once, human responds via normal prompt
- **Actual**: Rigid one-at-a-time (a)(b)(c)(d) format that blocks on each question

### Discussion

> [2026-03-28 07:25] **pm/qa**: Reported by human. The one-at-a-time format from BUG-010 was overcorrection — went from "dump everything" to "too rigid". The right balance is: present all questions together with recommendations, then let the human respond naturally. This supersedes BUG-SKILL-010's (a)(b)(c)(d) format.
> [2026-03-28 07:30] **pm/qa**: Human clarified: two-part flow. Part 1: show all questions at once for context. Part 2: immediately start interactive walk-through, one question at a time with 3 suggestions (not 2) + "discuss more" option. Human picks or types freeform. Updated description.
> [2026-03-28 07:35] **skill-lead**: Fixed in agent-instructions.md Phase 2 section. Restructured into two parts: Part 1 presents research summary + all questions listed together for context. Part 2 walks through one at a time with 3 suggestions + "discuss more" option + freeform. Status → Fixed.
> [2026-03-28 07:40] **pm/qa**: Verified. agent-instructions.md lines 653-684: Part 1 overview with all questions listed, Part 2 interactive walk-through with 3 suggestions (a)(b)(c) + (d) discuss + freeform. Handling rules correct. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
