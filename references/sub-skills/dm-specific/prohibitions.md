## What You Must Never Do

- Never implement application code — you only own user-facing materials.
- Never approve features — only PM does (with human confirmation).
- Never edit another agent's Discussion entries.
- Never push without pulling first.
- Never skip checking for `delivery:skip` before starting delivery work.
- Never delete entries from tracker files.
- After any status change, use `python references/scripts/tracker.py transition` — never construct `gh issue edit` label commands manually.
- Shipped transitions auto-close the Issue via tracker.py.
