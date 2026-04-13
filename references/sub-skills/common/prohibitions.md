## What You Must Never Do

- Never implement a task with status `Pending` — it has not been approved by a human yet.
- Never edit another agent's Discussion comments on GitHub Issues.
- Never push without pulling first.
- Never skip the test step before marking an issue Fixed or a task Pending Test.
- Never delete GitHub Issue comments.
- After any status change, use `python references/scripts/tracker.py transition` (see Tracker Protocol). Never construct `gh issue edit` label commands manually.
- Never run `gh issue close` directly. Issues are only closed via `tracker.py transition ... pending-ship shipped` which auto-closes. Direct close bypasses status transitions and leaves stale labels.
- Shipped transitions auto-close the Issue via tracker.py.
- Never mark Pending Test without running the full test suite and confirming all tests pass.
- Never mark Pending Test for new code without corresponding unit tests. Tests are part of the implementation, not follow-up work.
