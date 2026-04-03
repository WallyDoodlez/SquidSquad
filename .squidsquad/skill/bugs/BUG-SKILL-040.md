## BUG-SKILL-040 — Dev agent does not pick up QA-rejected In Progress features

- **Severity**: High
- **Status**: Closed
- **Reported By**: human
- **Assigned To**: skill-lead
- **Description**: When QA rejects a feature (sends it back from Pending Test to In Progress with specific gaps documented in Discussion), the dev agent does not pick it up on subsequent cycles. The agent cycles idle for 7+ consecutive cycles while In Progress items with QA feedback sit untouched.

  **Root cause**: The dev agent template Step 3 (Implement Features) only looks for features with status `Approved`. Once a feature moves to `In Progress` (already picked up), the agent expects its working-state.md to track the task. But after QA rejection, the working state was cleared (the agent completed its implementation). The agent sees `In Progress` status but no working state entry, and doesn't recognize it as work that needs to be resumed.

  **The gap**: The dev agent template has no step for "scan for In Progress features that have QA rejection feedback in Discussion." It handles the initial pickup (`Approved` → pick up) and the working state resume (context reset → resume), but NOT the QA rejection loop (`In Progress` with new Discussion entries from QA → read feedback → fix gaps → mark Pending Test again).

  **Required fix**: Add to the dev agent Ralph Loop (Step 3 or new Step 2.5):
  1. Scan features/INDEX.md for `In Progress` features
  2. For each, check if there are NEW Discussion entries from `**pm/qa**` or `**qa**` since the last `**skill-lead**` entry
  3. If yes — QA feedback exists. Read the feedback, fix the gaps, mark Pending Test again.
  4. This is higher priority than picking up new `Approved` features (fix existing work before starting new work).

- **Steps to Reproduce**:
  1. Dev agent implements a feature → marks Pending Test
  2. QA/PM rejects it → marks In Progress with gaps in Discussion
  3. Dev agent cycles idle repeatedly, never picks up the rejected feature
- **Expected**: Dev agent reads QA feedback on next cycle and fixes the gaps
- **Actual**: Dev agent ignores In Progress features with QA feedback, cycles idle indefinitely

### Discussion

> [2026-04-03 08:00] **pm/qa**: Filed from human.
> [2026-04-04 04:00] **skill-lead**: Fixed.
> [2026-04-04 04:15] **pm/qa**: Verified. QA rejection loop present in dev-agent Step 3 — scans In Progress features for new QA/PM comments, reads feedback, fixes gaps, re-marks Pending Test. Status → Closed. Added QA rejection loop to dev-agent Step 3: before checking for new Approved features, scan In Progress features for new QA/PM comments since last dev comment. If found, read feedback, fix gaps, re-mark Pending Test. Existing work before new work. Recomposed agent-instructions.md. Status → Fixed. FEAT-SKILL-059 and FEAT-SKILL-029 both stuck In Progress for 7+ cycles after QA rejection. Dev agent template has no QA rejection loop — only handles initial Approved pickup and working state resume. Needs a new step to scan for In Progress features with unaddressed QA feedback.
