### Step 7 — Agent Health Check

Print: `[🦑 HH:MM:SS] Checking agent health...`

Run the deterministic health check script — do NOT assemble health checks from prose or shell one-liners:

```bash
python references/scripts/health_check.py
```

The script reads `.squidsquad/.local-config` to find each agent's actual clone path, walks the cross-clone `current-state` files, and reports per-agent health (🦑 healthy / 👻 stalled / ❓ unknown / ⏹️ stopped). It uses the `Iteration Interval` from `config.md` with a 2× stale threshold.

Log the script's output in `pm/qa-log.md`. For any agent reporting stalled (👻) or unknown (❓):

1. Append a Discussion note to that agent's latest open tracker item:
   ```bash
   python references/scripts/tracker.py comment [NUMBER] --role pm --message "Agent [role] appears stalled — no cycle activity for [N] minutes. Please check."
   ```
2. If no open item exists for the agent, log the finding in `qa-log.md` only.

If `.local-config` is missing (no cross-clone paths configured), the script warns and exits cleanly — this is normal for single-clone setups and is not an error.

For programmatic use (e.g. by `boot_remote.py` from #4), the script also accepts `--json` for structured output.
