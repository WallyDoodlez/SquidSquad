---
slot: instructions
ordinal: 20
roles: [pm]
---

## Status Line

A status line is shown at the bottom of your Claude Code session. It displays:

- `🦑` (green) — you are active
- `PM` role label and current iteration number
- **Agent health**: for each agent (PM + verifier + DM + workers), `🦑` if `current-state` mtime is within 2× iteration interval (healthy), `👻` if stale (stalled), `❓` if no data (unknown/unreachable)
- Time since your last completed cycle (shows ⏰ overdue indicator when cycle exceeds iteration interval)

The status line updates automatically after each assistant message. No action is required from you — it reads from iteration logs across all agents.
