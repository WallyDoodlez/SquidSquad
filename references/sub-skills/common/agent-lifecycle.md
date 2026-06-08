---
slot: instructions
ordinal: 10
---

<!-- sub-skill: agent-lifecycle -->
### Agent Lifecycle

Agent lifecycle is managed by the harness (`harness.py`) via REST API (#4966). Agents do not manage their own or other agents' processes directly during normal operation. **Stall-recovery exception (#9272)**: PM may invoke `python references/scripts/boot_remote.py --role <name>` directly to spawn a stalled agent when the harness is unreachable (#9242) or when an agent stays dead despite auto-boot — see the `boot-remote-agents` sub-skill for the full policy. No other role boots agents directly.

**Three guarantees**:
1. **Singleton**: Only one instance per role runs at a time (harness process table).
2. **Graceful stop**: Harness sets intent=stopping via API. `cycle_post.py` queries `GET /agents/{role}` at cycle end, sees the intent, and exits with code 42. (Polling-mode wrapper. In event mode the per-event ack-cursor loop has no cycle boundary; the stop signal is observed at task boundaries per [[event-mode-contract]] Case E.)
3. **Start correctly**: Harness spawns agents via thin launcher (`thin_launcher.py`) in visible terminal windows. `cycle_pre.py` handles git pull/branch per cycle. (Polling-mode wrapper. In event mode the harness owns git — pull, commit, and push are managed at boot and shutdown by the harness; agents do not run `cycle_pre.py` / `cycle_post.py` per event.)

**Health monitoring**: Harness monitors agent liveness via PID monitoring through `.claude-pid` (sole liveness signal). The harness polls every 5 seconds.

**Intent state machine** (per-agent, in harness memory + `.harness-state.json`):
- `running` — agent should be alive; auto-reboot on death
- `stopping` — graceful stop; do NOT reboot after death
- `restarting` — graceful restart; reboot after death
- `stopped` — agent died as requested

**Lifecycle interface** (`squidsquad_cli.py` is canonical; `start_team.py <args>` remains as a backward-compatible shim):
```bash
# Start harness + all agents
python references/scripts/squidsquad_cli.py start

# Start a single agent (harness auto-spawns if needed)
python references/scripts/squidsquad_cli.py start <role>

# Graceful restart — harness sets intent=restarting
python references/scripts/squidsquad_cli.py restart <role>

# Stop a single agent — harness sets intent=stopping
python references/scripts/squidsquad_cli.py stop <role>

# Stop all agents
python references/scripts/squidsquad_cli.py stop

# Stop all agents and exit the harness
python references/scripts/squidsquad_cli.py shutdown
```

**Crash recovery**: Harness persists state to `.squidsquad/.harness-state.json`. On restart, reads the file, checks which PIDs are alive, and resumes monitoring.

**Ctrl+C escalation** (at harness terminal):
- 1st Ctrl+C: graceful stop (set all agents intent=stopping, wait for cycle end)
- 2nd Ctrl+C within 5s: warn about force exit
- 3rd Ctrl+C: exit harness (agents survive in their terminals)
<!-- /sub-skill: agent-lifecycle -->
