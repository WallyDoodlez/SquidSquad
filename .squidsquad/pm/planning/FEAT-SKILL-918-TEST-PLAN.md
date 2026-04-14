# FEAT-SKILL-918 Test Plan -- Self-Restart Background Poller

## Test Cases

### TC-1: Happy path -- agent writes .restart, poller detects and kills Claude

- **Precondition**: Boot script running with background poller active. Claude process is alive. No `.restart` file exists.
- **Steps**:
  1. Start the boot script for a role (e.g. `bash start-pm.sh`).
  2. Confirm Claude child process is running (`kill -0 $CHILD_PID` succeeds).
  3. Write the sentinel: `echo "context-pressure" > .squidsquad/pm/.restart`
  4. Wait up to 6 seconds.
- **Expected**: Claude child process is killed within ~5 seconds of sentinel creation. Boot script's restart loop detects `.restart` at line 124, reads reason, deletes sentinel, logs to `restart-log.txt`, resets backoff, sleeps 2s, and starts a new Claude session.
- **Verification**:
  - `! kill -0 $OLD_CHILD_PID` (old Claude process is gone)
  - `! test -f .squidsquad/pm/.restart` (sentinel consumed)
  - `grep "self-restart" .squidsquad/pm/restart-log.txt | tail -1` shows `reason=context-pressure`
  - A new Claude process is spawned (new PID visible)

### TC-2: Normal exit -- Claude exits on its own, watcher is cleaned up

- **Precondition**: Boot script running with background poller active. No `.restart` file exists.
- **Steps**:
  1. Start the boot script.
  2. Let Claude exit normally (e.g. `/loop` cycle completes, context exhaustion, or manual `/exit`).
  3. Do NOT create `.restart`.
- **Expected**: Claude exits with its own exit code. The background watcher process is killed/cleaned up immediately. No zombie or orphan watcher process remains. Boot script continues to the normal restart logic (10s cooldown for healthy run, backoff for fast crash).
- **Verification**:
  - `ps aux | grep` (or `pgrep`) shows no lingering watcher subprocess from the boot script
  - Boot script's restart log shows a normal restart entry (not self-restart)
  - `current-state` shows `restarting|Restarting in 10s...` (normal path, not self-restart path)

### TC-3: Stale sentinel -- .restart exists before Claude starts

- **Precondition**: `.squidsquad/pm/.restart` file already exists on disk (left from a previous crash or manual creation). Boot script is NOT yet running.
- **Steps**:
  1. Create the sentinel manually: `echo "stale" > .squidsquad/pm/.restart`
  2. Start the boot script.
  3. Claude starts and runs for some time.
  4. Claude exits normally.
- **Expected**: The existing sentinel detection at line 124 (after Claude exits) picks up the stale file. The sentinel is consumed, logged as a self-restart, and a new session starts. The background poller does NOT act on it prematurely during the first session (the sentinel is only polled while Claude is running -- but if it exists before Claude even starts, the poller could detect it immediately). Two valid behaviors:
  - (a) The poller detects it immediately and kills Claude right away -- boot script then consumes it and restarts. Net effect: very short first session, then clean restart.
  - (b) The boot script cleans up stale sentinels before spawning the poller. Net effect: sentinel consumed, Claude runs normally.
- **Verification**:
  - `! test -f .squidsquad/pm/.restart` (sentinel consumed regardless of path)
  - `restart-log.txt` shows the stale sentinel was logged
  - No error output or crash

**Note**: The CONTEXT.md states "boot script already deletes it at line 126 -- no change needed." Line 126 (`rm -f "$RESTART_SENTINEL"`) only runs AFTER `wait $CHILD_PID` returns. If the poller is added, it would detect and act on stale sentinels during the session. The dev should decide whether to add a pre-session cleanup (`rm -f "$RESTART_SENTINEL"` before spawning Claude) or accept behavior (a). Either is valid -- document the choice.

### TC-4: Double Ctrl+C -- watcher must not interfere with signal handler

- **Precondition**: Boot script running with background poller active. Claude is running.
- **Steps**:
  1. Start the boot script.
  2. Press Ctrl+C once.
  3. Verify the message: "Ctrl+C received. Press again within 5s to stop wrapper, or wait for claude to exit."
  4. Press Ctrl+C again within 5 seconds.
- **Expected**: First Ctrl+C sends SIGINT to Claude child (existing behavior). Second Ctrl+C within 5s stops the wrapper entirely. The watcher process is cleaned up as part of the EXIT trap. No interference -- the watcher does not catch SIGINT, does not print extra messages, and does not prevent the wrapper from exiting.
- **Verification**:
  - Wrapper exits cleanly after double Ctrl+C
  - `current-state` shows `stopped|Agent stopped by user`
  - No orphan watcher process remains (`ps aux | grep` clean)
  - PID file is removed

### TC-5: .stop takes priority over .restart

- **Precondition**: Boot script running with background poller active. Claude is running.
- **Steps**:
  1. Start the boot script.
  2. Create both sentinels simultaneously:
     ```bash
     echo "context-pressure" > .squidsquad/pm/.restart
     echo "" > .squidsquad/pm/.stop
     ```
  3. Wait up to 6 seconds for the poller to detect `.restart` and kill Claude.
  4. Observe the boot script's behavior after Claude exits.
- **Expected**: The poller detects `.restart` and kills Claude. After Claude exits, the boot script checks `.stop` FIRST (lines 116-121). Since `.stop` exists, the boot script breaks out of the while loop and stops entirely. The `.restart` sentinel is NOT acted upon -- `.stop` wins.
- **Verification**:
  - Boot script exits (wrapper stops)
  - `current-state` shows `stopped|Agent stopped by user`
  - `.stop` is consumed (deleted by boot script)
  - `.restart` may or may not be consumed (irrelevant -- the wrapper has stopped)
  - No restart occurs

### TC-6: Watcher cleanup -- no orphan background processes

- **Precondition**: Boot script running with background poller active. Claude is running.
- **Steps**:
  1. Start the boot script. Record the wrapper PID and the watcher PID.
  2. Trigger Claude exit by any means (normal exit, Ctrl+C, `.restart`, kill).
  3. Check for the watcher process.
  4. Repeat: let the boot script restart Claude (second iteration of the loop). Record the new watcher PID.
  5. Exit Claude again. Check for both old and new watcher PIDs.
- **Expected**: Each time Claude exits, the corresponding watcher is killed before the next iteration. After N iterations, there are zero orphan watcher processes. The cleanup mechanism (trap, explicit kill, or process group) reliably terminates the watcher.
- **Verification**:
  - After each Claude exit: `! kill -0 $WATCHER_PID` (watcher gone)
  - After wrapper exits: `ps --ppid $WRAPPER_PID` returns nothing (no children)
  - `pgrep -f` for the watcher polling pattern returns nothing

### TC-7: Windows (.ps1) -- equivalent behavior

- **Precondition**: Windows machine with PowerShell. `start-role.ps1` template updated with the background poller.
- **Steps**:
  1. Run `.\start-pm.ps1` in PowerShell.
  2. Confirm Claude is running.
  3. Write the sentinel: `"context-pressure" | Set-Content .squidsquad/pm/.restart -NoNewline`
  4. Wait up to 6 seconds.
- **Expected**: The background job or timer detects `.restart`, calls `Stop-Process` on the Claude process. Boot script's restart loop picks up, reads reason, deletes sentinel, logs, restarts.
- **Verification**:
  - Claude process is terminated within ~5s
  - `.restart` file is consumed
  - `restart-log.txt` shows self-restart entry
  - New Claude session starts
  - After wrapper exits (Ctrl+C or `.stop`): `Get-Job` shows no lingering background jobs; `Get-Process` shows no orphan watcher processes

### TC-7b: Windows -- watcher cleanup on normal exit

- **Precondition**: Same as TC-7. No `.restart` file.
- **Steps**:
  1. Run `.\start-pm.ps1`.
  2. Let Claude exit normally.
- **Expected**: Background job/timer is stopped and removed in the `finally` block. No orphan PowerShell jobs.
- **Verification**:
  - `Get-Job | Where-Object { $_.State -eq 'Running' }` returns nothing after Claude exits
  - No `powershell` child processes from the watcher remain

### TC-8: Upgrade path -- old boot scripts without poller

- **Precondition**: Agent running with an OLD boot script (generated before this change). Sub-skill instructs agent to write `.restart`.
- **Steps**:
  1. Start the agent with the old boot script.
  2. Agent writes `.restart` at cycle end (per sub-skill instructions).
  3. Claude continues running (old boot script has no poller).
  4. Eventually Claude exits on its own (context exhaustion, `/loop` cycle, etc.).
- **Expected**: The `.restart` file persists while Claude runs (no poller to detect it). After Claude exits normally, the existing post-exit sentinel check (line 124) detects `.restart`, consumes it, logs it, and restarts. The self-restart works -- it's just delayed until the next natural exit rather than being immediate.
- **Verification**:
  - `.restart` is consumed after Claude exits
  - `restart-log.txt` shows a self-restart entry
  - Agent restarts successfully
  - No errors or unexpected behavior -- graceful degradation

### TC-9: Rapid .restart writes -- poller does not race with boot script

- **Precondition**: Boot script running with poller. Claude is running.
- **Steps**:
  1. Write `.restart`.
  2. Poller detects it and kills Claude.
  3. Before the boot script loop processes the sentinel (during the small window between `wait` returning and the sentinel check), observe behavior.
- **Expected**: No race condition. The poller kills Claude, then the boot script's normal flow picks up: `wait` returns, checks `.stop` (not present), checks `.restart` (present), consumes it, logs, restarts. The poller does NOT delete the sentinel -- it only kills Claude. Sentinel lifecycle remains the boot script's responsibility.
- **Verification**:
  - Exactly one self-restart entry in `restart-log.txt` per `.restart` write
  - No double-restart or missed sentinel

### TC-10: Poller interval accuracy

- **Precondition**: Boot script running with poller. Claude is running.
- **Steps**:
  1. Record the time.
  2. Write `.restart`.
  3. Measure how long until Claude is killed.
  4. Repeat 5 times.
- **Expected**: Detection latency is between 0 and 5 seconds (one poll interval). Average latency should be approximately 2.5 seconds.
- **Verification**:
  - All measurements fall within 0-5s range
  - No measurement exceeds 6s (one full interval plus margin)

## Smoke Tests

- [ ] Boot script starts Claude successfully with poller (no regression on startup)
- [ ] Claude runs a full `/loop` cycle without the poller interfering
- [ ] Writing `.restart` kills Claude and triggers restart within 5 seconds
- [ ] Ctrl+C still works as before (single: kills Claude, double: kills wrapper)
- [ ] No watcher processes remain after wrapper exits
- [ ] `.stop` file still stops the wrapper (existing behavior preserved)
- [ ] PowerShell script starts and the poller works on Windows
- [ ] `compose.py boot [role]` generates the updated template without errors

## Regression Risks

- **Signal handling**: The background watcher could intercept or interfere with SIGINT/SIGTERM handling. The watcher subshell must not have its own signal traps that conflict with the wrapper's `on_sigint` and EXIT traps.
- **Process group inheritance**: If the watcher is a subshell, `kill $CHILD_PID` in the signal handler might also kill the watcher (or vice versa). The cleanup order matters.
- **PID file integrity**: The watcher must not write to or interfere with the PID lock mechanism. The wrapper PID ($$) must remain the PID file's content.
- **State file writes**: The watcher should NOT write to `current-state`. Only the boot script's main flow manages state transitions.
- **Exponential backoff**: If the poller kills Claude quickly (e.g. stale sentinel detected immediately), the runtime will be very short. The boot script must correctly identify this as a self-restart (not a fast crash) to avoid triggering exponential backoff. This depends on `.restart` being detected in the post-exit check (line 124) before the runtime check (line 147).
- **Windows Ctrl+C**: PowerShell handles Ctrl+C differently from Bash. The `try/finally` block must still execute cleanup even if the background job is running.
- **Restart log format**: Entries from poller-triggered restarts must be indistinguishable from naturally-detected restarts. The log format should not change.
