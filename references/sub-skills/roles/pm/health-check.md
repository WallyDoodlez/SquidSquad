<!-- sub-skill: health-check -->
### Step 7 — Agent Health Check

Print: `[🦑 HH:MM:SS] Checking agent health...`

Run the deterministic health check script:

```bash
python references/scripts/health_check.py
```

The script checks agent liveness via PID monitoring (primary) and `.health` file (legacy fallback). The harness monitors PIDs directly every 5 seconds (#4966).

Log the script's output in `pm/qa-log.md`. For any agent reporting stalled (👻) or unknown (❓):

1. Append a Discussion note to that agent's latest open tracker item.
2. If no open item exists, log in `qa-log.md` only.

**Context pressure monitoring**: Check each agent's context pressure file. If any agent exceeds threshold, report to the human with the agent role and pressure percentage. **PM does not execute reboots directly** — agent lifecycle is managed by the harness and `start_team.py` (#4966).

For programmatic use, the script accepts `--json` for structured output.
<!-- /sub-skill: health-check -->
