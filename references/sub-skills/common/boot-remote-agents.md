<!-- sub-skill: boot-remote-agents -->
### Step — First-Cycle Health Report (PM Only)

**PM-only gate**: Only the PM agent runs this step. If you are NOT the PM role, skip this step entirely.

Print: `[🦑 HH:MM:SS] Checking agent health...`

Boot detection runs automatically in `cycle_pre.py` before the creative phase. Read `boot_results` from `cycle-input.json` — it is a list of per-agent result objects, each with `role`, `action`, `success`, and `message` fields.

**Interpreting output**: Each agent entry has `action` (spawn/skip/dry-run) and `success` (true/false). Log any spawn failures in Discussion on the agent's current task issue.

If any agents were spawned, print: `[🦑 HH:MM:SS] Booted: [role1, role2, ...]`

If all agents alive or stopped, print nothing — silent pass.

**Manual boot is permitted on stall.** Routine agent lifecycle (start/stop on demand, restart on healthy cycles) belongs to the harness (`harness.py`) and `start_team.py` (#4966) — and the auto-boot path in `cycle_pre.py` runs before every PM cycle. When auto-boot is unavailable (harness down — see #9242) or insufficient (a specific agent stayed dead), PM may invoke `python references/scripts/boot_remote.py --role <name>` directly to spawn the stalled agent. Use `--all` only on explicit human request. Manual PM intervention is reserved for stall recovery — do NOT pre-emptively boot healthy agents (#9272, memory rule `feedback_manual_agents`).
<!-- /sub-skill: boot-remote-agents -->
