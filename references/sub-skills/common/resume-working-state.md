---
slot: instructions
ordinal: 10
---

### Step 1c — Resume From Working State

Print: `[🦑 HH:MM:SS] Checking working state...`

Read `.squidsquad/[ROLE]/working-state.md`. If it contains an active task (status `in-progress`):
- Print: `[🦑 HH:MM:SS] Resuming [TASK_ID]...`
- Read the task ID, completed steps, remaining steps, and key decisions.
- Resume work on that task instead of starting fresh from the tracker.
- Skip re-analyzing code you've already understood — trust the working state summary.

If the file is empty or has no active task, proceed normally to Step 2.
