# FEAT-PM-3807 Test Plan — Universal Sentinel-Based Agent Lifecycle

## Test Cases

### TC-1: start_team.py boots all agents
- **Precondition**: No agents running, no .stop files
- **Steps**: Run `python references/scripts/start_team.py --all`
- **Expected**: All agents listed in config.md spawn in separate terminal windows
- **Verification**: health_check.py shows all agents healthy within 30s

### TC-2: start_team.py boots single agent
- **Precondition**: Agent not running
- **Steps**: Run `python references/scripts/start_team.py --role skill`
- **Expected**: Only skill agent spawns
- **Verification**: health_check.py shows skill healthy, others unchanged

### TC-3: .stop-after-cycle sentinel triggers clean exit
- **Precondition**: Agent running and mid-cycle or idle
- **Steps**: Write .stop-after-cycle to agent's directory
- **Expected**: Agent finishes current cycle, cycle_post.py detects sentinel, commits work, exits cleanly
- **Verification**: Working state checkpointed, iteration log written, agent process exits 0

### TC-4: Wrapper respawns after .stop-after-cycle exit
- **Precondition**: TC-3 completed, wrapper still running
- **Steps**: Observe wrapper behavior after clean exit
- **Expected**: Wrapper detects .stop-after-cycle exit, removes sentinel, respawns agent fresh
- **Verification**: Agent comes back healthy, new cycle starts

### TC-5: Clean exit WITHOUT sentinel — wrapper stops
- **Precondition**: Agent exits with code 0, no .stop-after-cycle present
- **Steps**: Agent completes cycle and exits (e.g. /loop not active)
- **Expected**: Wrapper exits, does NOT respawn
- **Verification**: health_check.py shows agent dead, wrapper process gone

### TC-6: .stop sentinel permanently stops agent
- **Precondition**: Agent running
- **Steps**: Write .stop to agent's directory
- **Expected**: On next .stop-after-cycle exit (or clean exit), wrapper sees .stop and exits permanently
- **Verification**: Agent stays dead, wrapper process gone, .health shows stopped

### TC-7: Context pressure triggers .stop-after-cycle via cycle_post.py
- **Precondition**: Agent running, context pressure exceeds threshold
- **Steps**: Set context-pressure file to value above threshold, run a cycle
- **Expected**: cycle_post.py reads pressure from cycle-input.json, writes .stop-after-cycle, exits
- **Verification**: .stop-after-cycle sentinel exists, agent exits, wrapper respawns fresh

### TC-8: Stale context-pressure file ignored
- **Precondition**: context-pressure file older than one iteration interval
- **Steps**: Set context-pressure to 90% but make file old (>30 min)
- **Expected**: Wrapper treats as 0%, does NOT trigger restart
- **Verification**: No .stop-after-cycle written, agent continues normally

### TC-9: Crash backoff — exponential delay
- **Precondition**: Agent crashes immediately (non-zero exit)
- **Steps**: Agent crashes 5 consecutive times
- **Expected**: Wrapper waits 2s, 4s, 8s, 16s, 32s between retries, then writes .stop and exits
- **Verification**: Exponentially increasing gaps between respawn attempts, .health shows backoff, then error

### TC-10: start_team.py --reboot triggers graceful restart
- **Precondition**: Agent running and mid-cycle
- **Steps**: Run `python references/scripts/start_team.py --reboot skill`
- **Expected**: .stop-after-cycle written, agent finishes cycle, exits, wrapper respawns
- **Verification**: Agent restarts fresh with new context, working state preserved

### TC-11: start_team.py --reboot --all restarts entire team
- **Precondition**: All agents running
- **Steps**: Run `python references/scripts/start_team.py --reboot --all`
- **Expected**: .stop-after-cycle written to ALL agent dirs, all finish cycles, all respawn
- **Verification**: All agents restart fresh, health_check shows all healthy after respawn

### TC-12: PM first-cycle health report (no auto-boot)
- **Precondition**: PM rebooted, one other agent dead
- **Steps**: PM runs first cycle
- **Expected**: PM reports missing agent to human in check-in, does NOT auto-boot
- **Verification**: Check-in message mentions dead agent, no boot_remote.py call

### TC-13: PM periodic health report (every 10 cycles)
- **Precondition**: PM running, agent dead for multiple cycles
- **Steps**: PM runs 10+ cycles
- **Expected**: PM reports dead agent at cycle 1 and every 10th cycle, never boots
- **Verification**: Health report appears at expected intervals

### TC-14: reboot_agent.py shim (backward compat)
- **Precondition**: Transition period, old reboot_agent.py still exists
- **Steps**: Run `python references/scripts/reboot_agent.py skill`
- **Expected**: Deprecation warning printed, delegates to start_team.py --reboot skill
- **Verification**: Warning logged, agent reboots correctly

### TC-15: .restart backward compat (transition period)
- **Precondition**: Old .restart sentinel exists
- **Steps**: Agent exits, wrapper finds .restart
- **Expected**: Wrapper processes .restart same as .stop-after-cycle (respawn), logs deprecation
- **Verification**: Agent respawns, deprecation warning in wrapper log

### TC-16: Wrapper writes "restarting" to .health during gap
- **Precondition**: Agent exiting for respawn
- **Steps**: Observe .health file between agent exit and respawn
- **Expected**: .health contains "restarting" status during gap
- **Verification**: health_check.py shows agent as healthy/restarting, not stalled

### TC-17: Agent templates have no self-restart logic
- **Precondition**: All CLAUDE.md files recomposed
- **Steps**: Search all composed CLAUDE.md for restart_needed, .restart, self-restart
- **Expected**: No matches — all self-restart references removed
- **Verification**: `grep -r "restart_needed\|self-restart\|_do_restart_sentinel" .squidsquad/*/CLAUDE.md` returns empty

### TC-18: DM uses start_team.py for post-ship reboots
- **Precondition**: DM CLAUDE.md updated with new interface
- **Steps**: DM ships a template change
- **Expected**: DM calls start_team.py --reboot <role>, not reboot_agent.py
- **Verification**: DM iteration log shows start_team.py call

## Smoke Tests

- [ ] `python tests/run_tests.py` passes after all changes
- [ ] All agents boot via `start_team.py --all` and complete one cycle
- [ ] Manual .stop-after-cycle → respawn cycle works end-to-end
- [ ] .stop permanently stops an agent
- [ ] No self-restart references in any composed CLAUDE.md

## Regression Risks

- Wrapper infinite loop on persistent crashes — mitigated by exponential backoff + .stop after 5 crashes
- Dead wrapper stays down without PM auto-boot — intentional, human intervenes
- cycle_post.py sentinel check runs before commit — mitigated by ordering requirement (must be last)
- Stale .restart files processed incorrectly — mitigated by transition-period cleanup step

## Comprehension Questions

### CQ-1: What happens when an agent's context pressure exceeds the threshold?
- **Files**: references/sub-skills/common/cycle-runner.md, references/scripts/cycle_post.py
- **Expected**: cycle_post.py reads pressure from cycle-input.json, writes .stop-after-cycle sentinel, exits cleanly. Wrapper detects sentinel and respawns fresh. Agent does NOT set restart_needed or write .restart.

### CQ-2: How does a human start the entire SquidSquad team?
- **Files**: references/scripts/start_team.py
- **Expected**: Run `python references/scripts/start_team.py --all`. Script reads config.md for agent list, spawns each wrapper in a separate terminal.

### CQ-3: What does PM do when it detects a dead agent?
- **Files**: references/sub-skills/pm-specific/health-check.md
- **Expected**: PM reports the dead agent to the human in the check-in step. PM does NOT auto-boot or call boot_remote.py. Human decides whether to boot.
