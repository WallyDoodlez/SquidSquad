---
type: decision
tags: [architecture, reboot, lifecycle, process-management]
created: 2026-04-27
updated: 2026-04-27
owner: skill
status: active
confidence: medium
source: conversation
links: [decision-watchdog-supervisor]
---

## Context

Human clarified the correct reboot architecture (#3495): when rebooting an agent, kill the claude subprocess (child), not the wrapper (parent). Previously, reboot_agent.py killed the wrapper PID, leaving the claude process orphaned.

## Content

- `.pid` = wrapper process (for stop/singleton lock)
- `.claude-pid` = claude subprocess (for reboot)
- Reboot flow: write `.restart` sentinel → kill claude PID from `.claude-pid` → wrapper detects claude exit → reads `.restart` → respawns claude
- Wrapper NEVER dies during reboot — it stays alive and handles the respawn cycle
- Stop (manual kill/Stop-Process) kills wrapper — claude orphaned is acceptable for stop intent (separate concern)

## Rationale

The wrapper already has the respawn logic (check `.restart` sentinel after claude exits). Killing the wrapper and then spawning a new one duplicated lifecycle logic and caused the original bug: the old claude process survived as an orphan because `taskkill /F` on Windows doesn't cascade to children.

## Related

- [[decision-watchdog-supervisor]]

---

### Changelog

- 2026-04-27 — Created by skill. Documented #3495 fix: reboot kills child (claude), not parent (wrapper).
- 2026-05-16 — Updated by pm. Note: wrapper-based lifecycle partially superseded by harness intent API (#4966). Harness uses thin_launcher.py (no wrapper loop). `.claude-pid` remains as fallback for health monitoring. `.restart` sentinel deprecated in favor of intent state machine (running/stopping/restarting/stopped). Full deprecation tracked in #4792.
