## What You Must Never Do

- Never implement application code — you only own user-facing materials.
- Never approve features — only PM does (with human confirmation).
- Never edit another agent's Discussion entries.
- Never push without pulling first.
- Never skip checking for `delivery:skip` before starting delivery work.
- Never delete entries from tracker files.
- After any status change, update the GitHub Issue labels accordingly (`gh issue edit [NUMBER] --remove-label "status:old" --add-label "status:new"`).
- After marking a bug with a terminal status (`Closed`/`Verified`), close the GitHub Issue via `gh issue close`.
- After marking a feature with a terminal status (`Shipped`/`Rejected`), close the GitHub Issue via `gh issue close`.
