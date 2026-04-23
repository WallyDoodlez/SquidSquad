# Working State

- **Task**: #2183
- **Status**: in-progress
- **Started**: 2026-04-23 01:02
- **Quiet Cycles**: 0

## Completed Steps
- Read CONTEXT.md and RESEARCH.md
- Phase 1: Deleted watchdog.py (476 lines) and test_watchdog.py (370 lines)
- Phase 2: Created reboot_agent.py (~130 lines)
- Phase 2: Replaced start-role.sh (322→155 lines) and start-role.ps1 (326→155 lines)
- Phase 3: Replaced self-restart.md (watchdog ref → context pressure only)
- Phase 3: Created agent-lifecycle.md sub-skill
- Phase 3: Updated boot-remote-agents.md (watchdog ref → PM boot check)
- Phase 3: Updated health-check.md (watchdog ref → heartbeat monitoring)
- Phase 3: Updated context-pressure.md (watchdog ref → self-restart flag)
- Registered agent-lifecycle.md in manifest
- All tests passing

## Remaining Steps
- Phase 4 (simplify): Simplify boot_remote.py (remove cooldown/lock), health_check.py (heartbeat only)
- Phase 5 (templates): Recompose all role templates via compose.py deploy-all
- Phase 6 (tests): Write tests for reboot_agent.py, update boot_remote/health_check tests
- Phase 7 (cleanup): Update .gitignore, run full test suite
- Mark Pending Test

## Key Decisions
- Self-restart for context pressure only
- One retry on crash (< 30s = immediate crash)
- Remove .stop sentinel (CONTEXT.md locked decision)
- PM plans reboots, DM executes (PM fallback when DM absent)
- Heartbeat: epoch to .health every 5s, stale threshold 10s
