# FEAT-250 Research: Auto-Restart Agent on Loop Limit or Context Pressure

**Feature**: #250 — Auto-restart agent when loop limit or context pressure is reached
**Date**: 2026-04-05
**Status**: Research

---

## Problem Statement

SquidSquad agents run as Claude Code CLI sessions launched by boot scripts (`start-[role].sh` / `start-[role].ps1`). Three failure modes currently cause agents to die with no recovery:

1. **Cron 7-day expiry**: The `/loop` cron auto-expires after 7 days. The agent stops cycling, and the CLI session eventually ends.
2. **Context pressure exit**: When `context_window.used_percentage` exceeds the threshold (default 80%), the agent saves `working-state.md`, commits, and exits. The CLAUDE.md claims "The boot script will restart you with a fresh context window" (skill/CLAUDE.md line 286) — but the boot scripts have no restart logic.
3. **Crash / unexpected exit**: Any unhandled error or process kill terminates the agent silently.

The boot scripts already handle fresh-start vs resume (working-state.md exists = resume). The gap is: **nothing re-invokes the boot script after the `claude` process exits.**

---

## 1. Codebase Impact

### Files requiring changes

| File | Change |
|------|--------|
| `references/templates/start-role.sh` | Add wrapper loop around `claude` invocation |
| `references/templates/start-role.ps1` | Add wrapper loop around `claude` invocation |
| `references/scripts/compose.py` | No logic changes — `boot_role()` does simple `{{ROLE}}` substitution, wrapper loop is in template |
| `.squidsquad/start-*.sh` / `.squidsquad/start-*.ps1` | Regenerated via `compose.py boot <role>` |

### Current boot script structure (bash template)

```bash
# ... banner, permissions, agent registration, status bar init ...
claude --dangerously-skip-permissions --name "$AGENT_NAME" \
  --append-system-prompt "SQUIDSQUAD_ROLE={{ROLE}}" "start the loop"
# <-- script exits here when claude exits. No restart.
```

### Exit code convention

Claude Code CLI exit behavior (empirically observed):
- **Exit 0**: Clean exit (user typed `/exit`, agent called exit, context pressure exit)
- **Exit 1**: Error (permission denied, invalid args, auth failure)
- **Exit non-zero (other)**: Crash, SIGTERM, SIGINT, OOM

**Key limitation**: There is no distinct exit code for "context pressure exit" vs "user typed /exit". The agent simply exits the conversation in both cases, resulting in exit 0. This means the wrapper loop cannot distinguish "needs restart" from "human intentionally stopped."

### Impact on working-state.md resume flow

No changes needed. The existing Step 1c (Resume From Working State) already reads `working-state.md` on startup and resumes in-progress tasks. The wrapper loop just ensures a new `claude` invocation happens after exit.

### Impact on status bar

The boot scripts already reset `current-state` to `idle|Initializing...` before launching `claude`. On restart, this happens again naturally. A brief `restarting` state could be added between `claude` exit and re-launch.

### Impact on `/loop` cron

Each new `claude` session needs a fresh `/loop` invocation. The agent's CLAUDE.md already starts the loop on boot (the init message is `"start the loop"`), so this is handled automatically. The 7-day cron expiry becomes irrelevant because the wrapper loop restarts the entire session.

---

## 2. Implementation Approaches

### Approach A: Wrapper Loop in Boot Script (RECOMMENDED)

Wrap the `claude` invocation in a retry loop with cooldown and max-restart logic.

#### Bash template (`start-role.sh`)

```bash
# --- Auto-restart wrapper ---
MAX_RESTARTS=50
RESTART_COUNT=0
COOLDOWN_SECONDS=30
COOLDOWN_MAX=300
MIN_RUNTIME_SECONDS=120  # If claude runs < 2min, it's probably a boot error

while true; do
  START_TIME=$(date +%s)

  # Reset status bar
  rm -f .squidsquad/{{ROLE}}/current-state
  echo "idle|Initializing..." > .squidsquad/{{ROLE}}/current-state

  claude --dangerously-skip-permissions --name "$AGENT_NAME" \
    --append-system-prompt "SQUIDSQUAD_ROLE={{ROLE}}" "start the loop"
  EXIT_CODE=$?

  END_TIME=$(date +%s)
  RUNTIME=$((END_TIME - START_TIME))

  # Check for stop sentinel file (human wants to stop, not restart)
  if [ -f ".squidsquad/{{ROLE}}/.stop" ]; then
    echo "[SquidSquad] Stop file detected. Not restarting."
    rm -f ".squidsquad/{{ROLE}}/.stop"
    echo "stopped|Agent stopped by user" > .squidsquad/{{ROLE}}/current-state
    break
  fi

  # Max restarts guard
  RESTART_COUNT=$((RESTART_COUNT + 1))
  if [ "$RESTART_COUNT" -ge "$MAX_RESTARTS" ]; then
    echo "[SquidSquad] Max restarts ($MAX_RESTARTS) reached. Stopping."
    echo "error|Max restarts reached" > .squidsquad/{{ROLE}}/current-state
    break
  fi

  # Fast-crash detection: if runtime < MIN_RUNTIME, use exponential backoff
  if [ "$RUNTIME" -lt "$MIN_RUNTIME_SECONDS" ]; then
    COOLDOWN=$((COOLDOWN_SECONDS * (2 ** (RESTART_COUNT - 1))))
    [ "$COOLDOWN" -gt "$COOLDOWN_MAX" ] && COOLDOWN=$COOLDOWN_MAX
    echo "[SquidSquad] Fast exit detected (${RUNTIME}s). Backing off ${COOLDOWN}s..."
    echo "waiting|Restart backoff (${COOLDOWN}s)" > .squidsquad/{{ROLE}}/current-state
    sleep "$COOLDOWN"
  else
    # Healthy run — reset restart counter, use standard cooldown
    RESTART_COUNT=0
    COOLDOWN_SECONDS=30
    echo "[SquidSquad] Agent exited after ${RUNTIME}s (exit $EXIT_CODE). Restarting in 10s..."
    echo "restarting|Restarting in 10s..." > .squidsquad/{{ROLE}}/current-state
    sleep 10
  fi
done
```

Key design decisions:
- **MIN_RUNTIME_SECONDS=120**: If the agent runs for at least 2 minutes, it completed at least one useful cycle. Reset the restart counter — this is a healthy context-pressure exit.
- **Exponential backoff on fast crashes**: Prevents tight restart loops when CLAUDE.md has a syntax error or auth is broken.
- **Stop sentinel file** (`.squidsquad/[role]/.stop`): Human creates this file to signal "don't restart." Checked after each exit.
- **MAX_RESTARTS=50**: Safety cap. At 50 healthy restarts with context pressure exits, that's ~50 full context windows of work — more than a day.

#### PowerShell template (`start-role.ps1`)

```powershell
# --- Auto-restart wrapper ---
$MaxRestarts = 50
$RestartCount = 0
$CooldownSeconds = 30
$CooldownMax = 300
$MinRuntimeSeconds = 120

while ($true) {
    $startTime = Get-Date

    # Reset status bar
    Remove-Item ".squidsquad/{{ROLE}}/current-state" -ErrorAction SilentlyContinue
    "idle|Initializing..." | Set-Content ".squidsquad/{{ROLE}}/current-state" -NoNewline

    $sysPrompt = "SQUIDSQUAD_ROLE={{ROLE}}"
    $initMsg = "start the loop"
    claude --dangerously-skip-permissions --name "$AgentName" --append-system-prompt $sysPrompt $initMsg
    $exitCode = $LASTEXITCODE

    $runtime = ((Get-Date) - $startTime).TotalSeconds

    # Check for stop sentinel file
    $stopFile = ".squidsquad/{{ROLE}}/.stop"
    if (Test-Path $stopFile) {
        Write-Host "[SquidSquad] Stop file detected. Not restarting."
        Remove-Item $stopFile -ErrorAction SilentlyContinue
        "stopped|Agent stopped by user" | Set-Content ".squidsquad/{{ROLE}}/current-state" -NoNewline
        break
    }

    # Max restarts guard
    $RestartCount++
    if ($RestartCount -ge $MaxRestarts) {
        Write-Host "[SquidSquad] Max restarts ($MaxRestarts) reached. Stopping."
        "error|Max restarts reached" | Set-Content ".squidsquad/{{ROLE}}/current-state" -NoNewline
        break
    }

    # Fast-crash detection
    if ($runtime -lt $MinRuntimeSeconds) {
        $cooldown = [Math]::Min($CooldownSeconds * [Math]::Pow(2, $RestartCount - 1), $CooldownMax)
        Write-Host "[SquidSquad] Fast exit detected (${runtime}s). Backing off ${cooldown}s..."
        "waiting|Restart backoff (${cooldown}s)" | Set-Content ".squidsquad/{{ROLE}}/current-state" -NoNewline
        Start-Sleep -Seconds $cooldown
    } else {
        # Healthy run — reset counter
        $RestartCount = 0
        Write-Host "[SquidSquad] Agent exited after ${runtime}s (exit $exitCode). Restarting in 10s..."
        "restarting|Restarting in 10s..." | Set-Content ".squidsquad/{{ROLE}}/current-state" -NoNewline
        Start-Sleep -Seconds 10
    }
}
```

#### How to detect exit reason

| Scenario | Exit code | Runtime | Action |
|----------|-----------|---------|--------|
| Context pressure exit | 0 | > 2min | Restart (healthy) |
| Cron expiry / session end | 0 | > 2min | Restart (healthy) |
| User `/exit` | 0 | > 2min | Restart (mitigated by stop file) |
| Auth failure / bad config | 1 | < 2min | Backoff + retry |
| Crash / OOM | non-zero | varies | Backoff + retry |
| Human Ctrl+C | 130 (SIGINT) | varies | Caught by trap, stop |

#### Handling Ctrl+C (human wants to stop)

Bash: add a `trap` to catch SIGINT/SIGTERM at the wrapper level:

```bash
trap 'echo "[SquidSquad] Caught interrupt. Stopping."; exit 0' INT TERM
```

PowerShell: Ctrl+C propagates to the `claude` process. After it exits, the while loop would restart. Options:
- Check `$exitCode` — Ctrl+C in PS may produce exit code -1073741510 (STATUS_CONTROL_C_EXIT)
- Or: rely on the stop sentinel file approach

### Approach B: Self-Scheduling Restart (Agent Creates Cron Before Exit)

The agent, during its context pressure exit sequence, schedules a one-shot restart:

```bash
# Agent does this before exiting:
at now + 1 minute -f .squidsquad/start-skill.sh  # Unix
# or
schtasks /create /sc once /tn "SquidSquad-skill" /tr "..." /st ...  # Windows
```

**Pros**: Lighter — no long-running wrapper process. Agent only restarts when it knows it needs to.

**Cons**:
- Does NOT handle crashes (agent can't schedule if it dies unexpectedly)
- Does NOT handle cron expiry (agent doesn't know the cron is about to expire)
- `at` / `schtasks` availability varies across systems
- More complex cross-platform logic
- Agent must "know it's dying" — only works for context pressure, not for silent failures

**Verdict**: Insufficient. Does not cover crash recovery or cron expiry.

### Approach C: External Watchdog Process

A separate process (cron job, systemd service, Windows Task Scheduler) monitors agent health:

```bash
# watchdog.sh — runs every 5 minutes via system cron
for role_dir in .squidsquad/*/; do
  role=$(basename "$role_dir")
  state_file="$role_dir/current-state"
  if [ -f "$state_file" ]; then
    mtime=$(stat -c %Y "$state_file")
    now=$(date +%s)
    age=$((now - mtime))
    if [ "$age" -gt 3600 ]; then  # stale for > 1hr
      bash ".squidsquad/start-${role}.sh" &
    fi
  fi
done
```

**Pros**: Catches ALL failure modes including crashes. Decoupled from agent lifecycle.

**Cons**:
- Requires system-level cron/task setup (out of SquidSquad's control)
- Race conditions with existing processes (need PID file or lock)
- Harder to set up on Windows (Task Scheduler has different semantics)
- Overkill when Approach A already covers all cases

**Verdict**: Good as a defense-in-depth addition, but not worth the complexity for v1. The wrapper loop (Approach A) handles all practical cases.

---

## 3. Side Effects

### Infinite restart loops on persistent errors
- **Risk**: Bad CLAUDE.md syntax, expired auth token, broken dependency
- **Mitigation**: Exponential backoff + MAX_RESTARTS cap. After 50 fast-crash restarts (with escalating backoff), the wrapper gives up. At max backoff (5min), that's ~4 hours of retries before stopping.

### Resource consumption
- **Risk**: Orphan `claude` processes if wrapper is killed but child survives
- **Mitigation**: Bash `trap` handler to kill child process. PS: process tree kill on exit.
- The wrapper loop itself is trivial — a sleeping bash/PS process uses ~0 resources.

### Multiple agents starting
- **Risk**: If the user runs `start-skill.sh` again while a wrapper loop is already running
- **Mitigation for v1**: Document that only one instance should run. A PID lock file (`.squidsquad/[role]/.pid`) could be added but adds complexity.
- **Mitigation for v2**: PID file check at wrapper start: `if kill -0 $(cat .pid) 2>/dev/null; then echo "Already running"; exit 1; fi`

### Windows vs Unix process lifecycle
- **Bash**: `trap` for SIGINT/SIGTERM works reliably. `$?` captures exit code.
- **PowerShell**: Ctrl+C behavior is more complex. `$LASTEXITCODE` captures native exit codes. `try/finally` can catch termination.
- Both platforms: the `claude` CLI should handle SIGINT gracefully (save and exit).

### Human wants to shut down
- **Stop sentinel file**: `touch .squidsquad/[role]/.stop` — wrapper checks after each exit and stops.
- **Ctrl+C**: Bash `trap` catches this and breaks the loop.
- **Could also support**: a `/squidsquad-stop` command inside the agent that creates the sentinel and exits.

---

## 4. Edge Cases

### Agent exits during a git push
- `working-state.md` is committed before the context pressure exit (Step 1b mandates "commit and push all pending work" before exiting). If the push is interrupted, the next session will have local commits that need pushing — the agent's startup should handle this (pull/push sync in Step 1d interval sync).

### Two restart attempts overlap (race condition)
- Not possible with wrapper loop approach — the loop is sequential. `claude` must exit before the next iteration starts.
- Risk only exists with Approach B (self-scheduling) or Approach C (watchdog). Not applicable to recommended approach.

### Context pressure exit with uncommitted vault writes
- The vault (memory system) uses `vault_remember.py` which writes to files immediately. The context pressure exit sequence (Step 1b) commits all pending work before exiting. If the agent crashes before committing, vault writes are uncommitted but still on disk — the next session's git status will pick them up.

### Boot script itself has a bug
- Exponential backoff + MAX_RESTARTS prevents infinite tight loops. The wrapper detects fast crashes (< 2min runtime) and backs off progressively.
- Wrapper code should be minimal and well-tested — it's outside the `claude` session so it can't be debugged by the agent.

### Human manually kills the process
- `kill <pid>` sends SIGTERM to the wrapper, caught by `trap` — clean exit, no restart.
- `kill -9 <pid>` kills the wrapper immediately. The `claude` child process may continue running as an orphan. Not easily fixable — documented behavior.
- On Windows, closing the terminal window kills the entire process tree.

---

## 5. Integration Risks

### Interaction with `/loop` cron

Each new `claude` session is a fresh conversation. The agent's CLAUDE.md instructs it to start the loop on boot (init message: `"start the loop"`). The agent will issue `/loop 30m` (or whatever interval is configured) during its first cycle. This means:
- The 7-day cron expiry is now irrelevant — when the cron expires, the session ends, the wrapper restarts, and a new cron is created.
- The wrapper loop effectively makes the agent immortal (up to MAX_RESTARTS).

### Interaction with working-state.md

- Context pressure exit: Agent writes working-state.md, commits, exits. Wrapper restarts. New session reads working-state.md in Step 1c. **Works as designed.**
- Crash exit: Agent may NOT have written working-state.md. New session starts without state. **Acceptable** — the agent was mid-task but has no record. It will pick up the next item from the tracker. The GitHub Issue is still in `status:in-progress` so it won't be lost.

### Interaction with current-state file

The wrapper writes `restarting|Restarting in 10s...` between sessions. The status bar (if anyone is watching) shows the agent is cycling. This is new and useful.

---

## 6. Upgrade & Migration

### Template changes propagate via `compose.py boot`

1. Modify `references/templates/start-role.sh` and `start-role.ps1` with the wrapper loop.
2. Run `python references/scripts/compose.py boot-all` to regenerate all boot scripts.
3. Existing running agents must be stopped and re-launched to pick up the new wrapper.

### Backward compatibility

- The wrapper loop is purely additive — it wraps the existing `claude` invocation.
- `compose.py boot_role()` does simple `{{ROLE}}` substitution. No logic changes needed.
- Existing `working-state.md` files work unchanged.

### Graceful degradation

- If a user has a customized boot script (not generated from template), they won't get the wrapper. Documented in CHANGELOG.
- The agent's CLAUDE.md already says "The boot script will restart you" — this feature makes that claim true.

---

## 7. Open Questions

1. **Stop UX**: Is the sentinel file (`.stop`) sufficient, or do we also need a `/squidsquad-stop` slash command that the agent can execute from within the conversation?

2. **MAX_RESTARTS value**: 50 seems generous. Should this be configurable in `config.md`?

3. **Restart notification**: Should the wrapper log restarts somewhere persistent (a `.squidsquad/[role]/restart-log.txt`) so the human can see restart history?

4. **PID lock file**: Should v1 include duplicate-instance prevention, or defer to v2?

5. **Ctrl+C on Windows**: PowerShell Ctrl+C behavior is nuanced. Should we test this explicitly and document platform-specific stop behavior?

6. **Cron expiry still relevant?**: With the wrapper loop, the 7-day cron expiry just means the session ends and restarts. Is there any scenario where this causes problems (e.g., the agent is mid-conversation with a human)?

---

## 8. Recommendation

**Approach A (Wrapper Loop)** is the clear winner. It is:
- Simple to implement (template changes only, no new scripts)
- Cross-platform (bash + PowerShell variants already exist)
- Covers all three failure modes (context pressure, cron expiry, crash)
- Compatible with existing resume flow (working-state.md)
- Safe (exponential backoff, max restarts, stop sentinel)

### Implementation plan

1. **Update `references/templates/start-role.sh`**: Add wrapper loop with trap, backoff, stop file, status bar updates.
2. **Update `references/templates/start-role.ps1`**: Equivalent PowerShell wrapper.
3. **Add stop sentinel convention**: Document `.squidsquad/[role]/.stop` as the way to prevent restart.
4. **Regenerate boot scripts**: `compose.py boot-all`.
5. **Update SKILL.md**: Document auto-restart behavior, stop file, and restart limits.
6. **Test matrix**: Bash on Linux/macOS/WSL, PowerShell on Windows. Test context pressure exit, fast crash backoff, Ctrl+C, stop file.

### Estimated scope

- Template changes: ~60 lines per template (bash + PS1)
- No changes to `compose.py`, `cycle.py`, or agent CLAUDE.md files
- SKILL.md documentation: ~10 lines
- Testing: manual — launch agent, trigger context pressure, verify restart
