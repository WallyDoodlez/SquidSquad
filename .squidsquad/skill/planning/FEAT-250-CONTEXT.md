# FEAT-250 Context — Auto-Restart Agent on Loop Limit / Context Pressure

## Scope

Add a wrapper loop to boot script templates so agents automatically restart when they exit (context pressure, cron expiry, or crash). Includes PID lock, stop sentinel, restart logging, and exponential backoff.

**Delivers:**
1. Updated `references/templates/start-role.sh` — bash wrapper loop with restart logic
2. Updated `references/templates/start-role.ps1` — PowerShell wrapper loop with restart logic
3. PID lock file (`.squidsquad/[role]/.pid`) — prevents double-start
4. Stop sentinel (`.squidsquad/[role]/.stop`) — human-initiated shutdown
5. Double Ctrl+C handling — breaks wrapper loop for interactive stops
6. Restart log (`.squidsquad/[role]/restart-log.txt`) — timestamps, exit codes, restart count
7. Exponential backoff on fast crashes (<2min runtime)
8. Regenerate boot scripts via `compose.py boot`

## Locked Decisions (human decided)

- **Stop UX: sentinel + double Ctrl+C**: Touch `.squidsquad/[role]/.stop` for scripted stops. Double Ctrl+C (within 5s) for interactive stops. Belt and suspenders. Why: covers both automated and interactive shutdown scenarios.

- **Hardcoded max 50 restarts with exponential backoff**: No config field. 50 restarts covers 25+ hours of operation. Fast crashes (<2min runtime) trigger exponential backoff (2s, 4s, 8s, 16s... capped at 5min). Restart counter resets on healthy runs (>2min). Why: simple, no config bloat, backoff prevents resource waste.

- **PID lock file**: `.squidsquad/[role]/.pid` checked on boot. If PID is running, abort with message. ~10 lines per template. Why: prevents real operational errors from accidental double-start.

- **Restart log**: `.squidsquad/[role]/restart-log.txt` — append-only, gitignored. Each restart logs: timestamp, exit code, restart count, runtime of previous session. Why: debugging visibility without polluting git history.

## Dev Discretion (dev agent can choose)

- Exact exponential backoff curve and cap
- How to detect if PID is still running cross-platform (bash `kill -0` vs PowerShell `Get-Process`)
- Whether to clear .stop sentinel after the agent fully stops or leave it for human to remove
- Restart log rotation (if file grows large)
- Status bar message format during restart ("restarting|..." text)

## Side Effect Mitigations (required)

- **Infinite restart prevention**: Max 50 + exponential backoff on fast crashes. If all 50 exhausted, print final message and exit for real.
- **Orphan process prevention**: PID lock checked on start. Stale PID file (process dead) detected and cleaned up.
- **.gitignore**: Add `.pid`, `.stop`, `restart-log.txt` patterns if not already covered.
- **Working state preservation**: Agent's Step 1b (context pressure) already saves working-state.md and commits before exiting. The wrapper loop just needs to restart — resume logic exists in Step 1c.
- **Double Ctrl+C on Windows**: Must test PowerShell trap behavior. If unreliable, sentinel file is the primary stop mechanism on Windows.

## Upgrade Path (required)

- **Template changes**: `references/templates/start-role.sh` and `start-role.ps1` get wrapper loop
- **Regenerate**: `compose.py boot` regenerates all boot scripts
- **Graceful degradation**: Non-upgraded boot scripts still work — they just don't restart. No breakage.
- **New gitignore entries**: `.pid`, `.stop`, `restart-log.txt`

## Out of Scope

- External watchdog / OS service wrapper (future enhancement)
- Remote restart triggers (future — relates to #6 urgent cycle trigger)
- Restart across machine reboots (OS-level concern, not SquidSquad's)
