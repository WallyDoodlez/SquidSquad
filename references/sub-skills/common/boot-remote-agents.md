<!-- sub-skill: boot-remote-agents -->
### Step — Boot Results (PM Only)

**PM-only gate**: Only the PM agent runs this step. If you are NOT the PM role, skip this step entirely.

Print: `[🦑 HH:MM:SS] Checking boot results...`

Boot detection runs automatically in `cycle_pre.py` before the creative phase. Read `boot_results` from `cycle-input.json` — it is a list of per-agent result objects, each with `role`, `action`, `success`, and `message` fields.

**Interpreting output**: Each agent entry has `action` (spawn/skip/dry-run) and `success` (true/false). Log any spawn failures in Discussion on the agent's current task issue.

If any agents were spawned, print: `[🦑 HH:MM:SS] Booted: [role1, role2, ...]`

If all agents alive or stopped, print nothing — silent pass.

**Per-role opt-out**: To prevent a specific agent from being booted, create `.squidsquad/<role>/.stop`. This is respected by `boot_remote.py` even when called unconditionally.
<!-- /sub-skill: boot-remote-agents -->
