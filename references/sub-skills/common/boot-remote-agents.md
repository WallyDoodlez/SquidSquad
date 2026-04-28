<!-- sub-skill: boot-remote-agents -->
### Step — First-Cycle Health Report (PM Only)

**PM-only gate**: Only the PM agent runs this step. If you are NOT the PM role, skip this step entirely.

Print: `[🦑 HH:MM:SS] Checking agent health...`

Boot detection runs automatically in `cycle_pre.py` before the creative phase. Read `boot_results` from `cycle-input.json` — it is a list of per-agent result objects, each with `role`, `action`, `success`, and `message` fields.

**Interpreting output**: Each agent entry has `action` (spawn/skip/dry-run) and `success` (true/false). Log any spawn failures in Discussion on the agent's current task issue.

If any agents were spawned, print: `[🦑 HH:MM:SS] Booted: [role1, role2, ...]`

If all agents alive or stopped, print nothing — silent pass.

**PM does not boot agents directly.** Agent lifecycle is managed by `start_team.py` and the wrapper scripts. If PM detects a stalled or dead agent, report to the human — do not attempt to spawn or restart agents.
<!-- /sub-skill: boot-remote-agents -->
