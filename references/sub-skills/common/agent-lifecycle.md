<!-- sub-skill: agent-lifecycle -->
### Agent Lifecycle

Agent lifecycle is managed by the wrapper script and `reboot_agent.py`. Agents do not manage their own or other agents' processes directly.

**Three guarantees**:
1. **Singleton**: Only one instance per role runs at a time (PID lock file).
2. **Never kill mid-work**: `reboot_agent.py` waits for the agent to go idle before restarting.
3. **Start correctly**: Wrapper handles pre-flight checks, branch setup, and heartbeat.

**Heartbeat**: The wrapper writes the current epoch to `.squidsquad/[ROLE]/.health` every 5 seconds. Health monitoring reads this — if >10s old, the agent is considered dead.

**Reboot interface** (for PM and DM):
```bash
# Safe reboot — waits for idle, then restarts
python references/scripts/reboot_agent.py <role>

# Force reboot — kills immediately
python references/scripts/reboot_agent.py <role> --force

# Reboot all agents
python references/scripts/reboot_agent.py --all

# Custom timeout (default 300s)
python references/scripts/reboot_agent.py <role> --timeout 600
```

**Who reboots whom**:
- **PM** monitors context pressure and detects when agents need rebooting. PM plans reboots.
- **DM** executes reboots after shipping items that change agent templates/instructions.
- **PM fallback**: When DM is absent, PM executes reboots directly via `reboot_agent.py`.
- **Self-restart**: Agents can only self-restart for context pressure (see Self-Restart sub-skill).

**Sentinel files**:
- `.restart` — reboot request (written by agent for context pressure, or by `reboot_agent.py`)
- `.pid` — singleton lock (written by wrapper)
- `.health` — heartbeat epoch (written by wrapper every 5s)
<!-- /sub-skill: agent-lifecycle -->
