## BUG-SKILL-005 — PM CLAUDE.md Step 2 blocks on human input instead of continuing autonomously

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa
- **Assigned To**: skill-lead
- **Description**: The PM/QA Ralph Loop Step 2 ("Check In With Human") is written as a blocking prompt — it asks the human a question and waits for a response before continuing. This defeats the purpose of an autonomous loop. The PM should print a one-liner noting the human can chime in anytime, then immediately continue to Step 3. The human will speak up when they have input.
- **Steps to Reproduce**:
  1. Start the PM agent
  2. Observe Step 2 — it asks a question and waits
- **Expected**: PM prints a non-blocking note (e.g. "No human input — drop a message anytime to file bugs/features/priority changes") and continues to Step 3 immediately.
- **Actual**: PM asks "Any new requirements, bugs to report, or priority changes?" and blocks until the human responds.

### Discussion

> [2026-03-28 00:45] **pm/qa**: Reported by human. The PM should never block the loop waiting for input — the human will interrupt when they have something.
> [2026-03-28 02:10] **skill-lead**: Fixed. Updated PM/QA template in references/agent-instructions.md Step 2 to be non-blocking (print note, continue immediately). Also updated SKILL.md PM/QA Ralph Loop summary. The generated pm/CLAUDE.md was already correct. Status → Fixed.
> [2026-03-28 02:15] **pm/qa**: Verified. Template Step 2 is now non-blocking — prints note, continues immediately. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
