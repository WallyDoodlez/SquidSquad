<!-- sub-skill: agent-lifecycle -->
### Agent Lifecycle

Agent lifecycle is managed by `start_team.py` and the wrapper scripts. Agents do not manage their own or other agents' processes directly.

**Three guarantees**:
1. **Singleton**: Only one instance per role runs at a time (PID lock file).
2. **Graceful stop**: `start_team.py --reboot` writes `.stop-after-cycle` and waits for the agent to finish its current cycle before respawning.
3. **Start correctly**: Wrapper handles pre-flight checks, branch setup, and heartbeat.

**Heartbeat**: The wrapper writes the current epoch to `.squidsquad/[ROLE]/.health` every 5 seconds. Health monitoring reads this — if >10s old, the agent is considered dead.

**Lifecycle interface**:
```bash
# Start all agents
python references/scripts/start_team.py --all

# Start single agent
python references/scripts/start_team.py --role <role>

# Graceful reboot — waits for cycle end, then restarts
python references/scripts/start_team.py --reboot <role>

# Reboot all agents
python references/scripts/start_team.py --reboot --all

# Stop agent (permanent until manually restarted)
python references/scripts/start_team.py --stop <role>

# Stop all agents
python references/scripts/start_team.py --stop --all
```

**Sentinel files**:
- `.stop-after-cycle` — graceful restart request (written by `cycle_post.py` for context pressure, or by `start_team.py --reboot`)
- `.stop` — permanent stop (written by `start_team.py --stop`, respected by wrapper)
- `.pid` — singleton lock (written by wrapper)
- `.health` — heartbeat epoch (written by wrapper every 5s)
<!-- /sub-skill: agent-lifecycle -->
