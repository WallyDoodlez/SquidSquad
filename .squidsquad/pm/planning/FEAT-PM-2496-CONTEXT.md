# FEAT-PM-2496 Context — Unify Agent Lifecycle

## Scope

Make all agent lifecycle operations (human start, PM auto-boot, PM reboot, self-restart) go through the same wrapper. Eliminate the "agent dies permanently" failure mode where reboot kills an agent but nothing respawns it.

## Locked Decisions (human decided)

- **Wrapper PID**: .pid always stores the wrapper process PID. Killing it stops both wrapper and child. Singleton check is against the wrapper.
- **Reboot == ensure running**: If agent is dead, reboot boots it. If alive, restart it. Reboot is a universal recovery tool — no more no-op on dead agents.
- **Patch existing scripts**: Make reboot_agent.py call boot_remote.py's spawn logic after killing. No new supervisor script. Smallest change that unifies the lifecycle.

## Dev Discretion (dev agent can choose)

- How to share spawn logic between reboot_agent.py and boot_remote.py (import, shared module, or inline)
- How to unify clone-path resolution (reboot uses .local-config markdown parse, boot uses ~/.squidsquad/clones/ then .local-config)
- Whether to respect .stop sentinel during reboot (recommended: yes — don't respawn explicitly stopped agents)
- PID file standardization approach in wrapper templates if needed

## Side Effect Mitigations (required)

- **Double-start prevention**: Before spawning, verify PID is truly dead (not just stale file). Use OS-level process check, not .health file.
- **Timeout case**: If reboot times out waiting for idle, do NOT spawn a new wrapper (would restart mid-cycle). Only spawn after confirmed kill or confirmed dead.
- **Cross-clone path resolution**: Unify with boot_remote.py's logic (shared filesystem first, then .local-config). Do not maintain two different path resolution implementations.
- **.stop sentinel**: Respect it — if .stop exists, reboot should not respawn. Print a message instead.

## Upgrade Path (required)

- **Modified files**: reboot_agent.py, potentially boot_remote.py
- **Template changes**: Possible if PID semantics need standardization in wrapper templates
- **Upgrade steps**: If templates change, users regenerate via compose.py deploy-all + boot_all()
- **Graceful degradation**: If user doesn't upgrade wrappers, reboot_agent.py can still spawn existing start scripts. Behavior improves without requiring wrapper regeneration.

## Out of Scope

- New Python supervisor/lifecycle_manager.py (future consideration)
- Merging reboot_agent.py and boot_remote.py into one script
- Changes to the self-restart (.restart sentinel) flow — wrapper already handles this correctly
