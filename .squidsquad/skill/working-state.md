# Working State

- **Task**: #2183
- **Status**: in-progress
- **Started**: 2026-04-23 01:02
- **Quiet Cycles**: 0

## Completed Steps
- Read CONTEXT.md — locked decisions captured
- Read RESEARCH.md — full file inventory, removal list, build specs
- Verified watchdog.py has no external imports (safe to delete)
- Identified sub-skills referencing watchdog that need updating

## Remaining Steps
- Phase 1 (deletions): Delete watchdog.py, test_watchdog.py
- Phase 2 (new code): Create reboot_agent.py (~50 lines), simplified start-role.sh (~100 lines), start-role.ps1 (~100 lines)
- Phase 3 (sub-skills): Replace self-restart.md, health-check.md, boot-remote-agents.md; create agent-lifecycle.md
- Phase 4 (simplify): Simplify boot_remote.py (remove cooldown/lock), health_check.py (heartbeat only)
- Phase 5 (templates): Recompose all role templates via compose.py deploy-all
- Phase 6 (tests): Write tests for reboot_agent.py, simplified wrapper, update boot_remote/health_check tests
- Phase 7 (cleanup): Remove .stop references, update .gitignore, run full test suite
- Mark Pending Test

## Key Decisions
- Self-restart for context pressure only
- One retry on crash (< 30s = immediate crash)
- Remove .stop sentinel (CONTEXT.md locked decision)
- PM plans reboots, DM executes (PM fallback when DM absent)
- Heartbeat: epoch to .health every 5s, stale threshold 10s
- Keep double Ctrl+C handling in wrapper
