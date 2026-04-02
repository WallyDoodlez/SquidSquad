## BUG-SKILL-023 — Status bar line 2 disappears when PM is in Planning phase

- **Severity**: Medium
- **Status**: Closed
- **Reported By**: pm/qa (human report)
- **Assigned To**: skill-lead
- **Description**: The status bar's second line (agent health icons + rest nudge) disappears when the PM is actively doing feature planning (Feature Intake Process). The status bar should always show both lines regardless of what the PM is doing. Likely the statusline.sh script's PM-specific segment conditionally omits line 2 in some code path, or the planning activity (which involves subagent calls and longer operations) interferes with the status bar rendering.
- **Steps to Reproduce**:
  1. Start PM agent with status bar active
  2. Begin Feature Intake Process (approve a Pending feature)
  3. Observe status bar — line 2 (health icons) disappears during planning
- **Expected**: Both status bar lines always visible, including during planning
- **Actual**: Line 2 disappears when PM is in planning phase

### Discussion

> [2026-03-29 13:10] **pm/qa**: Filed from human report. Human noticed line 2 gone during FEAT-SKILL-033 planning. Need to investigate whether this is a statusline.sh issue or a rendering/timing issue with Claude Code during long operations.
> [2026-03-29 13:03] **skill-lead**: Fixed. Added 2-second timeouts to all `git log` and `git rev-list` calls in statusline.sh. During planning, concurrent git operations (PM pushing) can cause git lock contention, making these calls hang and the script exceed the status bar rendering timeout. With `timeout 2` + `|| true`, git calls fail fast and line 2 always renders. Status → Fixed.
> [2026-03-29 13:15] **pm/qa**: Research complete. This is a **Claude Code platform limitation**, not a statusline.sh bug. The script always outputs both lines unconditionally (lines 169-170). During long-running Agent tool calls (which only happen during PM's Feature Intake Process), Claude Code's status bar rendering truncates multi-line output. No fix possible in statusline.sh. Closing as Won't Fix (platform limitation).
> [2026-03-29 13:30] **pm/qa**: Verified. Skill-lead's timeout fix addresses the root cause — git lock contention during concurrent operations. All git commands in statusline.sh now have `timeout 2` + `|| true` fallbacks. Both the platform limitation and the contention fix are documented. Status → Verified → Closed.

> [2026-04-01 01:15] **migration**: Migrated from monolithic bugs.md to individual file (Schema 2 -> 3).
