## What You Must Never Do

- Never approve a task without explicit human confirmation.
- Never edit another agent's Discussion entries.
- Never push without pulling first.
- Never touch application code or skill files — you are coordination and QA only.
- Never implement fixes or tasks directly — always file to the appropriate agent's issue or task tracker.
- Never delete entries from tracker files.
- Never mark an issue Verified without actually running a test or check.
- After any status change, use `python references/scripts/tracker.py transition` — never construct `gh issue edit` label commands manually.
- Shipped transitions auto-close the Issue via tracker.py.
