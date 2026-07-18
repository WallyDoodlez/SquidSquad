---
slot: instructions
ordinal: 20
roles: [pm]
---

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

**Context pressure monitoring**: Check each agent's context pressure file. If any agent exceeds threshold, report to the human with the agent role and pressure percentage. **PM does not execute reboots for healthy agents** — graceful restart belongs to the harness via `squidsquad_cli.py` (or the backward-compatible `start_team.py` shim) (#4966). **On stall (harness down per #9242, or a specific agent stays dead despite auto-boot), PM may invoke `python references/scripts/boot_remote.py --role <name>` directly** — see the `boot-remote-agents` sub-skill for the full stall-recovery policy.

**Forge write-capability probe (#13574)**: liveness cannot see a forge WRITE-outage — during #13570 a read-only auth downgrade froze every transition, label write, and push fleet-wide while all health signals stayed green. Once per health check, run:

```bash
gh api repos/:owner/:repo -q .permissions.push
```

- `true` → healthy, no action.
- `false` → **infrastructure outage, not an agent problem**: every agent's writes are failing regardless of liveness. Escalate to the human immediately with the remediation (restore the gh identity's repo write role, or re-auth as an account with push access; `git push` confirming 403 = still read-only). Expect the escalation **transition itself to fail** mid-outage — fall back to whatever human-reaching surface still works (inline session, operator channel); the full handling lives in pipeline-sentinel halt class (e), which this probe result feeds (no need to re-run the probe there this cycle). Do not file per-agent stall findings for halts this explains.
- Probe error → inconclusive; note it and move on (the boot gate's read check covers connectivity).

For programmatic use, the script accepts `--json` for structured output.
<!-- /sub-skill: health-check -->
