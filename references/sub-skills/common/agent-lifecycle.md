<!-- sub-skill: agent-lifecycle -->
### Agent Lifecycle

Agent lifecycle is managed by the harness (`harness.py`) via REST API (#4966). Agents do not manage their own or other agents' processes directly.

**Three guarantees**:
1. **Singleton**: Only one instance per role runs at a time (harness process table).
2. **Graceful stop**: Harness sets intent=stopping via API. `cycle_post.py` queries `GET /agents/{role}` at cycle end, sees the intent, and exits with code 42.
3. **Start correctly**: Harness spawns agents via thin launcher (`thin_launcher.py`) in visible terminal windows. `cycle_pre.py` handles git pull/branch per cycle.

**Health monitoring**: Harness monitors agent liveness via direct PID checks (primary) and `.claude-pid` file (fallback). No heartbeat files needed — the harness polls every 5 seconds.

**Intent state machine** (per-agent, in harness memory + `.harness-state.json`):
- `running` — agent should be alive; auto-reboot on death
- `stopping` — graceful stop; do NOT reboot after death
- `restarting` — graceful restart; reboot after death
- `stopped` — agent died as requested

**Lifecycle interface**:
```bash
# Start all agents
python references/scripts/start_team.py --all

# Start single agent
python references/scripts/start_team.py --role <role>

# Graceful reboot — harness sets intent=restarting
python references/scripts/start_team.py --reboot <role>

# Reboot all agents
python references/scripts/start_team.py --reboot --all

# Stop agent — harness sets intent=stopping
python references/scripts/start_team.py --stop <role>

# Stop all agents
python references/scripts/start_team.py --stop --all
```

**Crash recovery**: Harness persists state to `.squidsquad/.harness-state.json`. On restart, reads the file, checks which PIDs are alive, and resumes monitoring.

**Ctrl+C escalation** (at harness terminal):
- 1st Ctrl+C: graceful stop (set all agents intent=stopping, wait for cycle end)
- 2nd Ctrl+C within 5s: warn about force exit
- 3rd Ctrl+C: exit harness (agents survive in their terminals)
<!-- /sub-skill: agent-lifecycle -->
