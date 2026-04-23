# FEAT-PM-2183 Context — Simplified Agent Lifecycle

## Scope

Replace all existing agent boot/restart/health/stop complexity (~2,283 lines) with a simplified lifecycle (~300 lines). Three guarantees: singleton, never kill mid-work, start correctly. PM plans reboots, DM executes them. Sub-skill as script wrapper pattern established.

## Locked Decisions (human decided)

- **Self-restart for context pressure only**: Agents can signal restart via cycle_post only when their own context pressure exceeds threshold. This is PM's safety valve (PM can't reboot itself via reboot_agent.py). All other restart reasons go through PM → DM flow.
- **Remove .stop sentinel**: Human closes the terminal to stop agents. No sentinel file needed.
- **One retry on crash**: If claude crashes (non-zero exit, no .restart sentinel), wrapper restarts once. If it crashes again immediately, wrapper exits. PM detects dead heartbeat and handles persistent failures via boot_remote.py.
- **Remove watchdog entirely**: Delete watchdog.py (476 lines) and test_watchdog.py (370 lines). Simplified wrapper + PM health monitoring replaces it.
- **PM calls reboot_agent.py directly**: When DM is absent, PM falls back to issuing reboots itself. Safe — PM calls via bash, waits for completion, continues.
- **boot_remote.py kept but simplified**: Still needed to spawn agents that aren't running at all. Removes: cooldown tracking, boot-attempts.log, boot-lock, health polling loop. Keeps: terminal spawning, PID check.
- **PM plans reboots, DM executes**: PM monitors context pressure and human requests. DM issues reboot_agent.py after shipping items that change agent behavior. This is SquidSquad project-specific role customization via SOUL.md.
- **Sub-skill as script wrapper**: agent-lifecycle.md sub-skill documents the reboot_agent.py interface. Composable into any role. Establishes reusable pattern for project-specific tooling.

## Dev Discretion (dev agent can choose)

- Heartbeat interval (recommended 5s) and stale threshold (recommended 10s)
- Exact wrapper structure (as long as ~100 lines and meets 3 guarantees)
- reboot_agent.py timeout value for wait-for-idle
- How boot_remote.py detects heartbeat vs old .health file (transition logic)

## Side Effect Mitigations (required)

- **Transition compatibility**: health_check.py must handle both old .health status strings and new heartbeat epoch during rollout. Don't break running agents mid-deploy.
- **PM self-restart**: PM must be able to write its own .restart sentinel for context pressure. Wrapper respawns PM. This is the one exception to "PM plans, DM executes."
- **crash retry detection**: Wrapper must distinguish "crashed immediately" (< 30s runtime) from "ran a full cycle then exited." Only the immediate crash gets one retry.
- **Windows parity**: PowerShell wrapper must have identical behavior to bash wrapper. Fix the known atomic write bug.

## Removal List

- `references/scripts/watchdog.py` (476 lines) — DELETE
- `tests/test_watchdog.py` (370 lines) — DELETE
- `references/templates/start-role.sh` (322 lines) — REPLACE with ~100 lines
- `references/templates/start-role.ps1` (326 lines) — REPLACE with ~100 lines
- boot_remote.py cooldown/lock/polling (~300 lines) — REMOVE
- health_check.py PID cross-check/mtime fallback/auto-correction (~250 lines) — SIMPLIFY
- Self-restart sub-skill in agent templates — SIMPLIFY (context pressure only)
- .stop sentinel references in all templates — REMOVE
- boot-attempts.log, boot-lock, .stop files — REMOVE
- restart-log.txt — REMOVE (one retry doesn't need logging)

## Upgrade Path (required)

- **Deploy order**: code changes → template regeneration via compose.py → agent restart
- **Transition period**: health_check.py handles both old and new formats
- **Existing .health/.pid/.stop files**: ignored after upgrade, can be cleaned up
- **Config changes**: none needed (Cycle Runner already enabled)

## Out of Scope

- Auto-restart loop (removed by design)
- Context pressure watcher in wrapper (PM handles this)
- Template change detection in wrapper (DM handles post-ship)
- .stop sentinel (removed)
- Cross-project lifecycle patterns (this is SquidSquad-specific role customization)
