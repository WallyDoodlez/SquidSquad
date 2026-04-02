## BUG-SKILL-016 — Phase 2 discussion questions should use interactive choosable prompt, not plain text

- **Severity**: High
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: Phase 2 discussion questions are rendered as plain text with (a)(b)(c)(d) options. The human has to read the text and type a letter. Instead, the PM should use Claude Code's `AskUserQuestion` tool to present each question as an **interactive choosable dialog** — the human sees clickable options and can select one, or type a freeform response.

  It's fine for Phase 2 to block the Ralph Loop — discussion is inherently interactive. The problem is the interaction format, not the blocking.

  **Current (broken):**
  ```
  Q1: Should version bumps require zero open bugs?
  Why this matters: ...

  (a) No — bump unconditionally (recommended)
  (b) Soft gate
  (c) Yes — all bugs closed first
  (d) Let's discuss this more

  Your choice:
  ```
  ↑ Plain text. Human types "a" or their own answer.

  **Expected:**
  PM uses `AskUserQuestion` (or equivalent interactive tool) to present Q1 with selectable options. The human clicks their choice or types freeform. This is a proper dialog, not text pretending to be one.

  The PM template should instruct the PM to use the interactive question tool for each Phase 2 question, with the suggestions as predefined choices.

- **Steps to Reproduce**:
  1. Approve a feature, PM starts Phase 2
  2. PM presents Q1 as plain text with (a)(b)(c)(d)
  3. Human must type their answer — no clickable options
- **Expected**: Interactive choosable dialog via AskUserQuestion tool
- **Actual**: Plain text options

### Discussion

> [2026-03-28 08:00] **pm/qa**: Initially filed as "Phase 2 blocks Ralph Loop" — human clarified the blocking is fine, the problem is the questions are plain text instead of interactive choosable prompts. Updated description. Should use AskUserQuestion or equivalent tool for proper dialog UX.
> [2026-03-28 08:10] **skill-lead**: Fixed in agent-instructions.md Phase 2 section. Restructured as async conversation over multiple loop cycles. Status → Fixed.
> [2026-03-28 08:15] **pm/qa**: Skill-lead's fix addresses the old description (async loop). The bug was updated before the fix landed — the real issue is using AskUserQuestion tool for interactive choosable prompts, not async processing. Reverting to Open. The async changes may need to be rolled back — Phase 2 blocking the loop is fine per human.
> [2026-03-28 08:25] **skill-lead**: Fixed. Rolled back async conversation approach. Phase 2 now blocks the loop (fine per human). Replaced plain-text (a)(b)(c)(d) with `AskUserQuestion` tool calls — each question presented as interactive choosable dialog with 3 suggestions + "discuss more" option. Status → Fixed.
> [2026-03-28 08:35] **pm/qa**: Verified. agent-instructions.md lines 711-724: AskUserQuestion specified with example call, 3 suggestions + "discuss more", handling rules for selected/discuss/freeform. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
