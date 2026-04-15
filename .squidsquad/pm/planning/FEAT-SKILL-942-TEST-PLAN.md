# FEAT-SKILL-942 Test Plan — Boot Process Health Overhaul

## Test Cases

### TC-1: Happy path — .health lifecycle through full boot
- **Precondition**: Agent role directory `.squidsquad/<role>/` exists. No `.pid`, `.health`, or `.stop` files present. Boot script template updated with `.health` writes.
- **Steps**:
  1. Run `start-role.ps1` (or `.sh`) for a role (e.g., `skill`).
  2. Observe `.squidsquad/<role>/.health` file at each stage of the boot lifecycle.
  3. Let agent run for > 120s (past the fast-crash threshold), then kill the Claude process.
  4. Observe `.health` during restart.
  5. Create `.stop` sentinel and let wrapper exit.
- **Expected**:
  - `.health` contains `booting` immediately after script starts (before Claude launches).
  - `.health` transitions to `alive` once Claude is successfully spawned.
  - `.health` shows `restarting` when the wrapper detects exit and begins restart sequence.
  - `.health` shows `dead` (or file is removed) when wrapper exits after `.stop`.
- **Verification**:
  ```bash
  cat .squidsquad/<role>/.health   # at each stage
  ```

### TC-2: Happy path — .health shows backoff status on fast crash
- **Precondition**: Boot script updated with `.health` writes. Claude binary available but agent will crash quickly (e.g., gh auth is broken so agent exits in < 120s).
- **Steps**:
  1. Start the boot script.
  2. Let Claude crash within < 120s.
  3. Read `.health` during the exponential backoff sleep.
- **Expected**: `.health` contains `backoff` (or equivalent status with cooldown details). File is machine-parseable.
- **Verification**:
  ```bash
  cat .squidsquad/<role>/.health   # should show backoff state
  ```

### TC-3: Happy path — .health shows error on max restarts
- **Precondition**: Boot script configured. Agent crashes repeatedly (e.g., Claude binary missing or always exits immediately).
- **Steps**:
  1. Start boot script.
  2. Let it exhaust all 50 restart attempts.
  3. Read `.health` after wrapper exits.
- **Expected**: `.health` contains `error|Max restarts reached`. Wrapper has exited. PID file is cleaned up.
- **Verification**:
  ```bash
  cat .squidsquad/<role>/.health   # "error|Max restarts reached"
  test ! -f .squidsquad/<role>/.pid   # PID file removed
  ```

### TC-4: Pre-flight — gh auth failure writes error to .health
- **Precondition**: `gh` CLI installed but not authenticated (or auth token expired). Boot script has pre-flight checks.
- **Steps**:
  1. Run `gh auth status` manually to confirm it fails.
  2. Start the boot script.
  3. Read `.health` immediately.
- **Expected**: `.health` contains `error|gh auth failed` (or similar structured error). Boot script does NOT enter the restart loop. Wrapper exits cleanly after writing the error.
- **Verification**:
  ```bash
  cat .squidsquad/<role>/.health   # structured error mentioning gh auth
  # Confirm restart-log.txt has no entries (no restart loop entered)
  test ! -s .squidsquad/<role>/restart-log.txt || wc -l .squidsquad/<role>/restart-log.txt
  ```

### TC-5: Pre-flight — wrong branch writes error to .health
- **Precondition**: Repo checked out on a non-main branch (e.g., `feature/test`). Boot script has branch pre-flight check.
- **Steps**:
  1. `git checkout -b feature/test`
  2. Start the boot script.
  3. Read `.health`.
- **Expected**: `.health` contains `error|wrong branch: feature/test (expected main)`. Wrapper exits without entering restart loop.
- **Verification**:
  ```bash
  cat .squidsquad/<role>/.health
  git checkout main   # cleanup
  git branch -d feature/test
  ```

### TC-6: Pre-flight — no crash loop on gh auth failure
- **Precondition**: `gh` not authenticated. Boot script has pre-flight checks.
- **Steps**:
  1. Start the boot script.
  2. Wait 60s.
  3. Count entries in `restart-log.txt`.
- **Expected**: Zero restart log entries. The script exited after the first pre-flight failure without entering the while-true loop. No Claude sessions were consumed.
- **Verification**:
  ```bash
  wc -l .squidsquad/<role>/restart-log.txt 2>/dev/null   # should be 0 or file missing
  cat .squidsquad/<role>/.health   # error state, not backoff/restarting
  ```

### TC-7: Post-spawn — boot_remote.py polls .health and confirms alive
- **Precondition**: Agent boot script updated with `.health` writes. Agent is not currently running. `boot_remote.py` updated to poll `.health` after spawn.
- **Steps**:
  1. Run `python references/scripts/boot_remote.py --role skill --json`.
  2. Monitor output/return time.
- **Expected**: `boot_remote.py` spawns the terminal, then waits up to 30s polling `.health`. Once `.health` shows `alive`, it returns success with a message indicating the agent is confirmed alive. Total return time should be < 30s (agent boots quickly in happy path).
- **Verification**:
  ```bash
  python references/scripts/boot_remote.py --role skill --json
  # Output should include "success": true and mention health confirmation
  ```

### TC-8: Post-spawn — boot_remote.py times out waiting for .health
- **Precondition**: Boot script is broken or extremely slow (e.g., rename the boot script so spawn succeeds but Claude never starts, or `.health` never transitions to `alive`).
- **Steps**:
  1. Create a dummy boot script that writes `booting` to `.health` but never writes `alive`.
  2. Run `python references/scripts/boot_remote.py --role skill --json`.
  3. Wait for it to return.
- **Expected**: After 30s timeout, `boot_remote.py` returns with a warning/partial-success indicating the spawn happened but health confirmation timed out. It should NOT return failure (the terminal did spawn) but should flag the timeout.
- **Verification**:
  ```bash
  # Output should mention timeout or health-unconfirmed
  python references/scripts/boot_remote.py --role skill --json
  ```

### TC-9: Context pressure — skill agent writes context-pressure to disk
- **Precondition**: Skill agent running with updated CLAUDE.md containing `context-pressure` sub-skill. Context window usage is above threshold (or mock it).
- **Steps**:
  1. Boot the skill agent.
  2. Let it run at least one full cycle.
  3. Check for `context-pressure` file.
- **Expected**: `.squidsquad/skill/context-pressure` file exists and contains a numeric percentage (e.g., `45`).
- **Verification**:
  ```bash
  cat .squidsquad/skill/context-pressure   # numeric value
  ```

### TC-10: Context pressure — PM agent writes context-pressure to disk
- **Precondition**: PM agent CLAUDE.md updated with `context-pressure` disk-write instruction (previously missing). PM agent running.
- **Steps**:
  1. Boot the PM agent.
  2. Let it run at least one full cycle (Step 1b should write pressure).
  3. Check for `context-pressure` file.
- **Expected**: `.squidsquad/pm/context-pressure` file exists with a numeric percentage. Previously this file was never written by PM.
- **Verification**:
  ```bash
  cat .squidsquad/pm/context-pressure   # numeric value, not empty/missing
  ```

### TC-11: Context pressure — QA agent writes context-pressure to disk
- **Precondition**: QA agent CLAUDE.md updated with `context-pressure` disk-write instruction. QA agent running.
- **Steps**:
  1. Boot the QA agent.
  2. Let it run at least one full cycle.
  3. Check for `context-pressure` file.
- **Expected**: `.squidsquad/qa/context-pressure` file exists with a numeric percentage.
- **Verification**:
  ```bash
  cat .squidsquad/qa/context-pressure
  ```

### TC-12: Context pressure — watcher detects high pressure and restarts
- **Precondition**: Agent running. Context threshold set to 70 in `config.md`.
- **Steps**:
  1. Manually write `85` to `.squidsquad/<role>/context-pressure`.
  2. Write `idle|Cycle complete` to `.squidsquad/<role>/current-state`.
  3. Wait up to 15s for the watcher to detect and kill Claude.
- **Expected**: Watcher detects pressure >= 70, sees `idle|` state, kills Claude. Wrapper restarts with fresh context. `restart-log.txt` contains a `context-pressure` entry. `.health` transitions through `restarting` then back to `alive`.
- **Verification**:
  ```bash
  tail -1 .squidsquad/<role>/restart-log.txt   # should mention context-pressure
  cat .squidsquad/<role>/.health   # eventually shows alive again
  ```

### TC-13: health_check.py reads .health — alive agent
- **Precondition**: Agent running. `.health` file contains `alive`. `current-state` recently updated.
- **Steps**:
  1. Run `python references/scripts/health_check.py --json`.
- **Expected**: Agent reported as `healthy`. The script reads `.health` for liveness determination (not just mtime). Output JSON includes health status and the `.health` file content.
- **Verification**:
  ```bash
  python references/scripts/health_check.py --json | python -c "import sys,json; d=json.load(sys.stdin); print(d['agents'][0]['health'])"
  # Should print "healthy"
  ```

### TC-14: health_check.py reads .health — dead agent
- **Precondition**: No agent running. `.health` file contains `dead` or `error|Max restarts reached`.
- **Steps**:
  1. Manually write `dead` to `.squidsquad/<role>/.health`.
  2. Run `python references/scripts/health_check.py --json`.
- **Expected**: Agent reported as `stalled` or a new status category reflecting the `.health` dead state. The script does NOT rely solely on mtime when `.health` is present.
- **Verification**:
  ```bash
  python references/scripts/health_check.py --json
  ```

### TC-15: health_check.py reads .health — error state
- **Precondition**: `.health` contains `error|gh auth failed`.
- **Steps**:
  1. Write `error|gh auth failed` to `.squidsquad/<role>/.health`.
  2. Run `python references/scripts/health_check.py --json`.
- **Expected**: Agent reported with an error status. The error detail (`gh auth failed`) is included in the output so PM can diagnose why the agent is not running.
- **Verification**:
  ```bash
  python references/scripts/health_check.py --json
  # Check for error detail in output
  ```

### TC-16: health_check.py graceful fallback — missing .health file
- **Precondition**: Agent running (PID alive, `current-state` recently updated), but no `.health` file exists (old boot script, not upgraded).
- **Steps**:
  1. Ensure `.health` file does NOT exist.
  2. Ensure `current-state` file exists with recent mtime.
  3. Run `python references/scripts/health_check.py --json`.
- **Expected**: health_check.py falls back to mtime-based detection (existing behavior). Agent reported as `healthy` based on `current-state` mtime. No crash, no error about missing `.health`.
- **Verification**:
  ```bash
  python references/scripts/health_check.py --json
  # Should show healthy based on mtime fallback
  ```

### TC-17: Self-restart rate limit — wrapper enforces 3/hour
- **Precondition**: Boot script wrapper updated with hard 3/hour rate limit for self-restarts. Agent running.
- **Steps**:
  1. Write `.restart` sentinel 3 times in quick succession (within a few minutes), letting the wrapper process each restart.
  2. Write `.restart` a 4th time.
  3. Observe wrapper behavior on the 4th attempt.
- **Expected**: First 3 restarts honored normally (wrapper kills Claude, restarts fresh, resets crash counter). 4th restart sentinel is ignored or deferred — wrapper prints a rate-limit warning and continues running the current session without restarting. `restart-log.txt` shows the rate-limit event.
- **Verification**:
  ```bash
  grep -c "self-restart" .squidsquad/<role>/restart-log.txt   # exactly 3 in the last hour
  cat .squidsquad/<role>/.health   # still alive, not in restart loop
  ```

### TC-18: Self-restart rate limit — counter resets after 1 hour
- **Precondition**: 3 self-restarts already consumed in the current hour window.
- **Steps**:
  1. Wait until > 60 minutes have passed since the first self-restart of the current window.
  2. Write `.restart` sentinel again.
- **Expected**: Restart is honored (the hourly window has rolled over). Counter effectively resets.
- **Verification**:
  ```bash
  tail -5 .squidsquad/<role>/restart-log.txt   # new self-restart entry after gap
  ```

### TC-19: Stale wizard cleanup — QA CLAUDE.md no longer references wizard
- **Precondition**: `compose.py deploy qa` has been re-run after wizard removal.
- **Steps**:
  1. Read `.squidsquad/qa/CLAUDE.md`.
  2. Search for the string "wizard".
- **Expected**: No mention of "wizard" anywhere in QA's CLAUDE.md. The active agents line should match `config.md` Dev Agents list (currently: `skill`).
- **Verification**:
  ```bash
  grep -i "wizard" .squidsquad/qa/CLAUDE.md   # should return no matches
  grep "active dev agents" .squidsquad/qa/CLAUDE.md   # should show "skill" only
  ```

### TC-20: Stale wizard cleanup — DM CLAUDE.md no longer references wizard
- **Precondition**: `compose.py deploy dm` has been re-run after wizard removal.
- **Steps**:
  1. Read `.squidsquad/dm/CLAUDE.md`.
  2. Search for the string "wizard".
- **Expected**: No mention of "wizard" anywhere in DM's CLAUDE.md. The active agents line matches `config.md`.
- **Verification**:
  ```bash
  grep -i "wizard" .squidsquad/dm/CLAUDE.md   # should return no matches
  ```

### TC-21: Side effect regression — existing boot flow still works
- **Precondition**: Updated boot scripts deployed. Agent not currently running.
- **Steps**:
  1. Run the boot script for a role (e.g., `start-skill.ps1`).
  2. Verify the full boot sequence completes: squid logo prints, permissions injected, config synced, PID file written, Claude launches.
- **Expected**: All existing boot steps still work. The addition of `.health` writes does not break the logo display, permission injection, config sync, PID lock, or Claude launch. Agent enters its Ralph Loop normally.
- **Verification**:
  ```bash
  test -f .squidsquad/<role>/.pid   # PID file created
  cat .squidsquad/<role>/current-state   # agent writes status
  cat .squidsquad/<role>/.health   # new file also present
  ```

### TC-22: Side effect regression — PID files still created and cleaned
- **Precondition**: Updated boot scripts. Agent not running.
- **Steps**:
  1. Start the boot script. Verify `.pid` file is created with a valid PID number.
  2. Kill the wrapper process (or let it exit via `.stop`).
  3. Verify `.pid` file is removed by the cleanup handler.
- **Expected**: PID file lifecycle is unchanged. Created at boot, contains wrapper PID, removed on exit (via `finally` block on PS1 or `trap EXIT` on sh).
- **Verification**:
  ```bash
  cat .squidsquad/<role>/.pid   # valid PID while running
  # After exit:
  test ! -f .squidsquad/<role>/.pid   # cleaned up
  ```

### TC-23: Side effect regression — current-state still written by agents
- **Precondition**: Agent running with updated boot script.
- **Steps**:
  1. Let agent complete at least one cycle.
  2. Read `current-state` file.
- **Expected**: Agent still writes `current-state` with `phase|description` format at each step. The introduction of `.health` does not replace or interfere with `current-state` writes.
- **Verification**:
  ```bash
  cat .squidsquad/<role>/current-state   # phase|description format
  ```

### TC-24: Side effect regression — agents without upgraded boot scripts degrade gracefully
- **Precondition**: One agent (e.g., `qa`) has an OLD boot script (no `.health` writes). Another agent (e.g., `skill`) has the new boot script.
- **Steps**:
  1. Boot both agents.
  2. Run `python references/scripts/health_check.py --json`.
  3. Run `python references/scripts/boot_remote.py --all --json`.
- **Expected**: `health_check.py` reports the old agent using mtime fallback (TC-16) and the new agent using `.health`. `boot_remote.py` handles both — reads `.health` when present, falls back to PID-only check when `.health` is missing. No crashes, no false "dead" reports for the old agent.
- **Verification**:
  ```bash
  python references/scripts/health_check.py --json
  python references/scripts/boot_remote.py --all --json
  # Both agents show as alive/healthy, using different detection methods
  ```

### TC-25: Cross-platform — PS1 boot script writes .health correctly
- **Precondition**: Windows environment with PowerShell. Updated `start-role.ps1` template.
- **Steps**:
  1. Generate boot script: `python references/scripts/compose.py boot skill`
  2. Run `.squidsquad/start-skill.ps1` in PowerShell.
  3. Monitor `.health` file transitions.
- **Expected**: `.health` is written using PowerShell-native file operations (e.g., `Set-Content`). Transitions: `booting` -> `alive` -> (on exit) `restarting` or `dead`. File encoding is UTF-8. No BOM issues.
- **Verification**:
  ```powershell
  Get-Content .squidsquad/skill/.health
  [System.IO.File]::ReadAllBytes(".squidsquad/skill/.health")[0..2]   # Check no BOM
  ```

### TC-26: Cross-platform — sh boot script writes .health correctly
- **Precondition**: Linux/macOS environment with bash. Updated `start-role.sh` template.
- **Steps**:
  1. Generate boot script: `python references/scripts/compose.py boot skill`
  2. Run `.squidsquad/start-skill.sh`.
  3. Monitor `.health` file transitions.
- **Expected**: `.health` written via `echo "status" > .health`. Same lifecycle as PS1. File permissions are standard (644). No trailing carriage returns.
- **Verification**:
  ```bash
  cat .squidsquad/skill/.health
  file .squidsquad/skill/.health   # should show ASCII text
  od -c .squidsquad/skill/.health | tail -1   # no \r characters
  ```

### TC-27: Cross-platform — .health cleanup on wrapper exit (PS1)
- **Precondition**: Windows. Agent running via PS1 boot script.
- **Steps**:
  1. Create `.stop` sentinel to trigger clean shutdown.
  2. Wait for wrapper to exit.
  3. Check `.health` file.
- **Expected**: `.health` contains `dead` (or is removed, depending on dev's choice — per CONTEXT.md dev discretion). The `finally` block in PS1 handles this.
- **Verification**:
  ```powershell
  Get-Content .squidsquad/<role>/.health   # "dead" or file absent
  ```

### TC-28: Cross-platform — .health cleanup on wrapper exit (sh)
- **Precondition**: Linux/macOS. Agent running via sh boot script.
- **Steps**:
  1. Send SIGTERM to wrapper process.
  2. Wait for cleanup trap to execute.
  3. Check `.health` file.
- **Expected**: `.health` contains `dead` (or is removed). The `trap cleanup EXIT` handler writes the final state.
- **Verification**:
  ```bash
  cat .squidsquad/<role>/.health   # "dead" or file absent
  ```

### TC-29: Cross-platform — pre-flight checks work in PS1
- **Precondition**: Windows. `gh auth status` returns non-zero. Updated PS1 template with pre-flight checks.
- **Steps**:
  1. Invalidate gh auth (e.g., `gh auth logout`).
  2. Run `start-role.ps1`.
  3. Read `.health`.
- **Expected**: PS1 script runs `gh auth status`, detects failure, writes error to `.health`, and exits without entering the restart loop. PowerShell error handling (try/catch or exit code check) works correctly.
- **Verification**:
  ```powershell
  Get-Content .squidsquad/<role>/.health   # error mentioning gh auth
  ```

### TC-30: Cross-platform — pre-flight checks work in sh
- **Precondition**: Linux/macOS. `gh auth status` returns non-zero. Updated sh template with pre-flight checks.
- **Steps**:
  1. Invalidate gh auth.
  2. Run `start-role.sh`.
  3. Read `.health`.
- **Expected**: sh script runs `gh auth status`, detects failure (non-zero exit code), writes error to `.health`, exits cleanly.
- **Verification**:
  ```bash
  cat .squidsquad/<role>/.health   # error mentioning gh auth
  ```

### TC-31: Upgrade path — old boot scripts without .health, health_check.py falls back
- **Precondition**: Agent running with OLD boot script (no `.health` writes). `health_check.py` updated to read `.health` with mtime fallback.
- **Steps**:
  1. Ensure NO `.health` file exists for the agent.
  2. Ensure `current-state` exists and was recently updated (agent is actually running).
  3. Run `python references/scripts/health_check.py --json`.
- **Expected**: health_check.py detects missing `.health`, falls back to `current-state` mtime check. Reports agent as `healthy` (mtime is recent). Output may include a note like `"health_source": "mtime-fallback"` to indicate which detection method was used.
- **Verification**:
  ```bash
  python references/scripts/health_check.py --json
  # Agent should be healthy, detected via mtime
  ```

### TC-32: Upgrade path — boot_remote.py handles missing .health gracefully
- **Precondition**: Agent running with old boot script. `.pid` file exists with alive PID. No `.health` file.
- **Steps**:
  1. Run `python references/scripts/boot_remote.py --role skill --json`.
- **Expected**: boot_remote.py reads `.health` first — not found. Falls back to PID-based detection. Reports agent as alive (skip). Does NOT try to spawn a duplicate.
- **Verification**:
  ```bash
  python references/scripts/boot_remote.py --role skill --json
  # action: "skip", message mentions PID alive
  ```

### TC-33: Upgrade path — partial upgrade (one agent new, one old)
- **Precondition**: `skill` has new boot script with `.health`. `qa` has old boot script without `.health`. Both agents running.
- **Steps**:
  1. Run `python references/scripts/health_check.py --json`.
  2. Run `python references/scripts/boot_remote.py --all --json`.
- **Expected**: Both scripts handle the mixed state. `skill` is checked via `.health` (primary). `qa` is checked via mtime/PID fallback. Both report correctly. No errors or crashes from the mixed detection.
- **Verification**:
  ```bash
  python references/scripts/health_check.py --json
  python references/scripts/boot_remote.py --all --json
  ```

### TC-34: Upgrade path — compose.py boot regenerates scripts with .health support
- **Precondition**: Updated templates in `references/templates/start-role.ps1` and `start-role.sh`. Existing old boot scripts in `.squidsquad/`.
- **Steps**:
  1. Run `python references/scripts/compose.py boot skill`.
  2. Read the generated `.squidsquad/start-skill.ps1` (or `.sh`).
  3. Search for `.health` file operations.
- **Expected**: Generated boot script contains `.health` write operations at each lifecycle stage (booting, alive, restarting, backoff, dead/error). Pre-flight checks are present.
- **Verification**:
  ```bash
  grep -c "\.health" .squidsquad/start-skill.ps1   # multiple matches
  grep "gh auth" .squidsquad/start-skill.ps1   # pre-flight check present
  ```

## Smoke Tests

- [ ] `python references/scripts/health_check.py` runs without error on a fresh clone with no agents running
- [ ] `python references/scripts/health_check.py --json` returns valid JSON in all cases (no agents, some agents, mixed old/new)
- [ ] `python references/scripts/boot_remote.py --dry-run --all --json` returns valid JSON and does not spawn anything
- [ ] `.health` file is valid single-line text (no multi-line, no binary, no BOM)
- [ ] `config.md` Dev Agents list does not include "wizard"
- [ ] QA CLAUDE.md does not contain "wizard"
- [ ] DM CLAUDE.md does not contain "wizard"
- [ ] PM CLAUDE.md does not contain "wizard"
- [ ] Boot script `.pid` file still created on boot (regression check)
- [ ] Boot script `current-state` still initialized to `idle|Initializing...` on boot (regression check)
- [ ] Pre-flight failure does not leave stale `.pid` file behind
- [ ] Self-restart with `.restart` sentinel still works (regression check)
- [ ] Context pressure restart still works when pressure file is present (regression check)

## Regression Risks

- **Split-brain worsened by partial migration**: If `boot_remote.py` is updated to read `.health` but boot scripts are not regenerated, `boot_remote.py` will see no `.health` and must fall back cleanly. TC-32 covers this.
- **PowerShell encoding**: `Set-Content` in PS1 may write UTF-16 by default on older PowerShell versions. Ensure `-Encoding UTF8` is used for `.health` writes. TC-25 checks for BOM.
- **File locking on Windows**: Both `.health` and `current-state` are written by the wrapper and read by `health_check.py`/`boot_remote.py`. Concurrent read/write on Windows may cause access errors. Writes should use atomic patterns (write to `.tmp` then rename).
- **Wrapper rate limit breaks crash recovery**: The new 3/hour self-restart limit in the wrapper must NOT interfere with crash-restart (which uses a different counter). Only `.restart` sentinel restarts should be rate-limited, not crash-induced restarts. TC-17 verifies this.
- **Pre-flight checks block legitimate non-main branch work**: If the branch check is hard-coded to `main`, agents cannot run on feature branches during development. The implementation should read the expected branch from config or allow an override.
- **health_check.py dual-read ordering**: When both `.health` and `current-state` are present, the script must define clear precedence. If `.health` says `alive` but `current-state` mtime is stale, which wins? The CONTEXT.md says `.health` for liveness, `current-state` for phase info — ensure this is respected.
