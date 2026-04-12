### Step — Boot Remote Agents

Print: `[🦑 HH:MM:SS] Checking for agents to boot...`

Check `Auto Boot Agents` in `config.md`. If set to `no`, skip this step entirely.

Run the boot check:

```bash
python references/scripts/boot_remote.py --all --json
```

The script:
1. Runs `health_check.py --json` to get authoritative agent health
2. For each agent that is **stalled** or **unknown**, spawns a new terminal with the agent's boot script
3. Respects `.stop` sentinel (never boots explicitly stopped agents)
4. Enforces cooldown (10 min between spawn attempts per role)
5. Uses a lock file to prevent race conditions between agents

**Interpreting output**: Each agent entry has `action` (spawn/skip/dry-run) and `success` (true/false). Log any spawn failures in Discussion on the agent's current task issue.

If any agents were spawned, print: `[🦑 HH:MM:SS] Booted: [role1, role2, ...]`

If all agents healthy or stopped, print nothing — silent pass.
