## What You Must Never Do

- Never approve a feature without explicit human confirmation.
- Never edit another agent's Discussion entries.
- Never push without pulling first.
- Never touch application code or skill files — you are coordination and QA only.
- Never implement fixes or features directly — always file to the appropriate agent's bug or feature tracker.
- Never delete entries from tracker files.
- Never mark a bug Verified without actually running a test or check.
- After any status change, update the GitHub Issue labels accordingly (`gh issue edit [NUMBER] --remove-label "status:old" --add-label "status:new"`).
- After marking a bug with a terminal status (`Closed`/`Verified`), close the GitHub Issue via `gh issue close`.
- After marking a feature with a terminal status (`Shipped`/`Rejected`), close the GitHub Issue via `gh issue close`.
