<!-- sub-skill: health-check -->
### Step 7 — Agent Health Check

Print: `[🦑 HH:MM:SS] Checking agent health...`

Run the deterministic health check script:

```bash
python references/scripts/health_check.py
```

The script reads each agent's `.claude-pid` (sole liveness signal) and `current-state` mtime for offline diagnostics. The harness monitors PIDs directly every 5 seconds (#4966); prefer `squidsquad_cli.py status` when the harness is reachable.

Log the script's output in `pm/qa-log.md`. For any agent reporting stalled (👻) or unknown (❓):

1. Append a Discussion note to that agent's latest open tracker item.
2. If no open item exists, log in `qa-log.md` only.

**Context pressure monitoring**: Check each agent's context pressure file. If any agent exceeds threshold, report to the human with the agent role and pressure percentage. **PM does not execute reboots directly** — agent lifecycle is managed by the harness; operators use `squidsquad_cli.py` (or the backward-compatible `start_team.py` shim) (#4966).

For programmatic use, the script accepts `--json` for structured output.
<!-- /sub-skill: health-check -->
