<!-- sub-skill: boot-remote-agents -->
### Step — Boot Remote Agents (PM Only)

**PM-only gate**: Only the PM agent runs this step. If you are NOT the PM role, skip this step entirely.

Print: `[🦑 HH:MM:SS] Checking for agents to boot...`

Check `Auto Boot Agents` in `config.md`. If set to `no`, skip this step entirely.

Run the boot check:

```bash
python references/scripts/boot_remote.py --all --json
```

The script:
1. Reads each agent's `.pid` file from their clone path
2. Checks if the PID process is alive
3. If dead (or no PID file) and no `.stop` sentinel, spawns a new terminal
4. Enforces cooldown (10 min between spawn attempts per role)
5. Uses a lock file to prevent race conditions

**Interpreting output**: Each agent entry has `action` (spawn/skip/dry-run) and `success` (true/false). Log any spawn failures in Discussion on the agent's current task issue.

If any agents were spawned, print: `[🦑 HH:MM:SS] Booted: [role1, role2, ...]`

If all agents alive or stopped, print nothing — silent pass.
<!-- /sub-skill: boot-remote-agents -->
