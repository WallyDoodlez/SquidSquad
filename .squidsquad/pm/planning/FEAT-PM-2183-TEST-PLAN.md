# FEAT-PM-2183 Test Plan — Simplified Agent Lifecycle

## Test Cases

---

### Section A: Wrapper Guarantees (start-role.sh / start-role.ps1)

---

### TC-1: Singleton enforcement — PID lock prevents double-start
- **Precondition**: Agent "skill" is already running with a valid `.squidsquad/skill/.pid` file and the PID is alive.
- **Steps**:
  1. Run `./squidsquad/start-skill.sh` (or `.ps1`) a second time in a new terminal
- **Expected**: Second invocation prints a message indicating the agent is already running, then exits immediately with a non-zero exit code. No second claude process is spawned.
- **Verification**: `ps aux | grep claude | grep skill` shows exactly one process (Unix). On Windows: `Get-Process | Where-Object { $_.CommandLine -match 'skill' }` shows one.

### TC-2: Singleton enforcement — stale PID file does not block start
- **Precondition**: `.squidsquad/skill/.pid` contains a PID that is no longer alive (stale). No claude process running for skill.
- **Steps**:
  1. Write a dead PID to `.squidsquad/skill/.pid`
  2. Run `./squidsquad/start-skill.sh`
- **Expected**: Wrapper detects the PID is not alive, proceeds with startup normally. Old PID file is overwritten with the new PID. Agent boots successfully.
- **Verification**: `.squidsquad/skill/.pid` contains a valid, alive PID. Agent is running.

### TC-3: Never kill mid-work — reboot_agent.py waits for idle
- **Precondition**: Agent "skill" is running and `current-state` shows `verifying|verification — Verifying #100...` (not idle).
- **Steps**:
  1. Run `python references/scripts/reboot_agent.py skill --timeout 30`
  2. After 10 seconds, write `idle|` to `.squidsquad/skill/current-state`
- **Expected**: reboot_agent.py polls every 2 seconds. Once `idle|` appears, it kills the claude process. Wrapper detects exit, sees `.restart` sentinel, and respawns.
- **Verification**: Agent restarts with a new PID. `restart-log.txt` (if kept) records the reboot. Old work was not interrupted mid-cycle.

### TC-4: Never kill mid-work — reboot_agent.py times out on busy agent
- **Precondition**: Agent "skill" is running. `current-state` shows active work. Timeout set to 10s.
- **Steps**:
  1. Run `python references/scripts/reboot_agent.py skill --timeout 10`
  2. Do NOT write `idle|` — keep agent busy
- **Expected**: reboot_agent.py waits 10 seconds, prints "timeout waiting for idle — agent is busy", removes the `.restart` sentinel, exits with code 1.
- **Verification**: Agent is still running with the same PID. No `.restart` sentinel file exists.

### TC-5: Start correctly — SQUIDSQUAD_ROLE env var set
- **Precondition**: Clean environment. No agent running.
- **Steps**:
  1. Run `./squidsquad/start-skill.sh`
  2. Inspect the claude spawn command
- **Expected**: Claude is invoked with `--append-system-prompt "SQUIDSQUAD_ROLE=skill"`. The env var is embedded in the system prompt.
- **Verification**: `ps aux | grep claude` (or process inspection) shows the `--append-system-prompt` flag with the correct role.

### TC-6: Start correctly — pre-flight checks (gh auth, branch)
- **Precondition**: `gh auth status` fails (not authenticated).
- **Steps**:
  1. Run `./squidsquad/start-skill.sh`
- **Expected**: Wrapper prints an error about GitHub auth failure and exits before spawning claude. `.health` shows "dead" or is absent.
- **Verification**: No claude process running. Wrapper exited with non-zero code.

### TC-7: One retry on crash — non-zero exit, no sentinel
- **Precondition**: Agent is running. No `.restart` sentinel exists.
- **Steps**:
  1. Simulate claude crashing (kill the claude process with a non-zero exit signal)
  2. Observe wrapper behavior
- **Expected**: Wrapper detects non-zero exit. No `.restart` sentinel present. Wrapper restarts claude once (retry). If the retry runs for >30 seconds, the retry is considered successful.
- **Verification**: Claude process is running again with a new PID. `.pid` file updated.

### TC-8: One retry on crash — immediate second crash exits
- **Precondition**: Agent is running. No `.restart` sentinel exists.
- **Steps**:
  1. Simulate claude crashing (kill with non-zero exit)
  2. Wrapper restarts claude (retry)
  3. Simulate claude crashing again within <30 seconds of the retry
- **Expected**: Wrapper detects a second immediate crash. Exits cleanly. Cleanup trap fires (removes `.pid`, writes dead health). No infinite restart loop.
- **Verification**: No claude process running. `.pid` file removed. `.health` indicates dead (or is removed by cleanup trap).

### TC-9: Self-restart sentinel — context pressure only
- **Precondition**: Agent "pm" is running. Context pressure exceeds threshold (e.g., 75% when threshold is 70%).
- **Steps**:
  1. PM agent writes `context pressure exceeded` to `.squidsquad/pm/.restart` at end of cycle
  2. PM agent's claude process exits normally
- **Expected**: Wrapper detects `.restart` sentinel, deletes it, respawns claude. PM gets a fresh context window.
- **Verification**: New PM claude process running. `.restart` sentinel deleted. PM reads `working-state.md` on startup and resumes.

### TC-10: Self-restart sentinel — non-context-pressure reasons blocked
- **Precondition**: Agent "skill" is running. Context pressure is below threshold.
- **Steps**:
  1. Verify that cycle_post.py only writes `.restart` when context pressure exceeds threshold
  2. Attempt to trigger self-restart for another reason (e.g., arbitrary restart request)
- **Expected**: cycle_post.py guard prevents writing `.restart` sentinel. Agent does NOT self-restart. PM handles reboots through the normal PM/DM flow.
- **Verification**: No `.restart` sentinel written. Agent continues normally.

### TC-11: Heartbeat background job writes epoch every 5s
- **Precondition**: Agent started with new wrapper.
- **Steps**:
  1. Start the agent
  2. Wait 12 seconds
  3. Read `.squidsquad/skill/.health` three times at 5-second intervals
- **Expected**: `.health` contains a plain integer (Unix epoch). Each read shows a value within 5 seconds of the current time. Values increment by ~5 between reads.
- **Verification**: `python -c "import time; epoch=int(open('.squidsquad/skill/.health').read().strip()); assert abs(time.time()-epoch) < 10"`

### TC-12: Cleanup trap fires on exit
- **Precondition**: Agent is running with a valid `.pid` and heartbeat.
- **Steps**:
  1. Send SIGINT to the wrapper (Ctrl+C once, then again)
  2. Observe cleanup
- **Expected**: Wrapper kills child claude process, removes `.pid` file, writes dead state to `.health` (or removes it). Heartbeat background job is killed.
- **Verification**: No `.pid` file. No orphaned heartbeat process. `.health` shows stale epoch or is removed.

### TC-13: Double Ctrl+C handling
- **Precondition**: Agent is running.
- **Steps**:
  1. Press Ctrl+C once
  2. Observe "press again to exit" message
  3. Press Ctrl+C again within the grace period
- **Expected**: First Ctrl+C prints a warning/confirmation message. Second Ctrl+C triggers clean shutdown via cleanup trap.
- **Verification**: Agent exits cleanly. PID file removed.

---

### Section B: Removal Verification

---

### TC-14: watchdog.py deleted, no imports remain
- **Precondition**: Feature branch with all changes applied.
- **Steps**:
  1. Check for `references/scripts/watchdog.py`
  2. Search entire codebase for imports of watchdog
- **Expected**: `references/scripts/watchdog.py` does not exist. No file contains `import watchdog`, `from watchdog`, or `scripts/watchdog` (except vault decision records which are historical).
- **Verification**: `test ! -f references/scripts/watchdog.py` and `grep -r "watchdog" --include="*.py" --include="*.sh" --include="*.ps1" --include="*.md" references/ tests/ .squidsquad/ | grep -v vault/ | grep -v CHANGELOG | grep -v planning/` returns empty.

### TC-15: test_watchdog.py deleted
- **Precondition**: Feature branch with all changes applied.
- **Steps**:
  1. Check for `tests/test_watchdog.py`
- **Expected**: File does not exist.
- **Verification**: `test ! -f tests/test_watchdog.py`

### TC-16: .stop sentinel removed from all templates
- **Precondition**: Feature branch with all changes applied.
- **Steps**:
  1. Search templates for `.stop` sentinel references
- **Expected**: No template file references `.stop` sentinel checking or creation. The wrapper does not check for `.stop`.
- **Verification**: `grep -r "\.stop" references/templates/ references/sub-skills/` returns no sentinel-related matches.

### TC-17: 50-restart loop removed
- **Precondition**: Feature branch with all changes applied.
- **Steps**:
  1. Search wrapper templates for MAX_RESTARTS, COOLDOWN_BASE, COOLDOWN_MAX, SELF_RESTART_LIMIT, MIN_RUNTIME_SECONDS
- **Expected**: None of these constants exist in the new wrapper templates.
- **Verification**: `grep -E "MAX_RESTARTS|COOLDOWN_BASE|COOLDOWN_MAX|SELF_RESTART_LIMIT|MIN_RUNTIME" references/templates/start-role.sh references/templates/start-role.ps1` returns empty.

### TC-18: Cooldown/boot-lock/boot-attempts.log removed from boot_remote.py
- **Precondition**: Feature branch with all changes applied.
- **Steps**:
  1. Read `references/scripts/boot_remote.py`
  2. Search for cooldown, boot-lock, boot-attempts functions
- **Expected**: Functions `_read_boot_log`, `_append_boot_log`, `_check_cooldown`, `_acquire_lock`, `_release_lock` do not exist. No references to `boot-attempts.log` or `boot-lock` files.
- **Verification**: `grep -E "cooldown|boot-lock|boot-attempts|_read_boot_log|_append_boot_log|_check_cooldown|_acquire_lock|_release_lock" references/scripts/boot_remote.py` returns empty.

### TC-19: PID cross-check and mtime fallback removed from health_check.py
- **Precondition**: Feature branch with all changes applied.
- **Steps**:
  1. Read `references/scripts/health_check.py`
  2. Search for PID cross-check, mtime fallback, auto-correction logic
- **Expected**: Functions `_read_pid_file`, `_is_process_alive`, `_parse_health_file` (old status-string parser) do not exist. No mtime-based fallback logic. No auto-correction of stale health files.
- **Verification**: `grep -E "_read_pid_file|_is_process_alive|_parse_health_file|mtime|auto.correct" references/scripts/health_check.py` returns empty.

### TC-20: Runtime files cleaned up
- **Precondition**: Feature branch with all changes applied. Old runtime files from previous version may exist.
- **Steps**:
  1. Check that `.squidsquad/boot-attempts.log`, `.squidsquad/boot-lock`, `.squidsquad/watchdog-log.txt` are either deleted or ignored
  2. Check `.gitignore` for updated patterns
- **Expected**: These files are not tracked or referenced in new code. `.gitignore` entries for `boot-attempts.log` and `boot-lock` are removed (no longer needed since files are deleted).
- **Verification**: `grep -E "boot-attempts|boot-lock|watchdog-log" .gitignore` returns empty or confirms removal.

---

### Section C: New Components

---

### TC-21: reboot_agent.py — happy path reboot
- **Precondition**: Agent "skill" is running and idle (`current-state` = `idle|`).
- **Steps**:
  1. Run `python references/scripts/reboot_agent.py skill`
- **Expected**: Script writes `.restart` sentinel, detects idle immediately, kills claude process. Wrapper sees sentinel and respawns. Exit code 0. Prints "reboot initiated for skill".
- **Verification**: New claude process running with new PID. `.restart` sentinel deleted by wrapper.

### TC-22: reboot_agent.py — agent not running
- **Precondition**: No agent running for "skill". No `.pid` file or PID is dead.
- **Steps**:
  1. Run `python references/scripts/reboot_agent.py skill`
- **Expected**: Prints "agent not running". Exit code 0.
- **Verification**: No sentinel written. No process killed.

### TC-23: reboot_agent.py — --force flag skips idle wait
- **Precondition**: Agent "skill" is running and busy (not idle).
- **Steps**:
  1. Run `python references/scripts/reboot_agent.py skill --force`
- **Expected**: Script writes `.restart` sentinel and immediately kills claude without waiting for idle. Wrapper respawns.
- **Verification**: Agent restarts. Total execution time is <5 seconds regardless of agent state.

### TC-24: reboot_agent.py — --all flag iterates all roles
- **Precondition**: Multiple agents running (e.g., skill, qa). All idle.
- **Steps**:
  1. Run `python references/scripts/reboot_agent.py --all`
- **Expected**: Script iterates each role from config.md, reboots them sequentially. Each agent restarts.
- **Verification**: All agents have new PIDs after completion.

### TC-25: reboot_agent.py — exit codes
- **Precondition**: Various agent states.
- **Steps**:
  1. Run with agent idle -> observe exit code
  2. Run with agent busy and timeout -> observe exit code
  3. Run with invalid arguments -> observe exit code
- **Expected**: Exit 0 for success (including "not running"), exit 1 for timeout, exit 2 for usage error.
- **Verification**: `echo $?` after each invocation matches expected code.

### TC-26: reboot_agent.py — PID change during wait
- **Precondition**: Agent "skill" is running with PID X. reboot_agent.py is waiting for idle.
- **Steps**:
  1. Start `python references/scripts/reboot_agent.py skill --timeout 60`
  2. While it waits, agent crashes and wrapper auto-restarts it (new PID Y, no sentinel)
- **Expected**: reboot_agent.py detects PID changed (X -> Y), recognizes agent already restarted, cleans up sentinel, exits with code 0.
- **Verification**: Script exits cleanly. Agent is running with PID Y.

### TC-27: reboot_agent.py — concurrent invocations for same role
- **Precondition**: Agent "skill" is running and idle.
- **Steps**:
  1. Start `python references/scripts/reboot_agent.py skill` in terminal A
  2. Immediately start `python references/scripts/reboot_agent.py skill` in terminal B
- **Expected**: Both write the sentinel (idempotent). First one kills the process and wrapper restarts. Second one detects PID changed and exits.
- **Verification**: Agent restarts exactly once. Both scripts exit with code 0.

### TC-28: agent-lifecycle.md sub-skill exists and is composable
- **Precondition**: Feature branch with all changes applied.
- **Steps**:
  1. Check `references/sub-skills/common/agent-lifecycle.md` exists
  2. Check it documents reboot_agent.py interface, heartbeat, sentinel files
  3. Check it has PM-specific and DM-specific sections
  4. Check `manifest.md` includes it
- **Expected**: File exists with all required sections. Composable via `{{include: common/agent-lifecycle}}`.
- **Verification**: `test -f references/sub-skills/common/agent-lifecycle.md` and content includes "reboot_agent.py", "heartbeat", ".restart", ".pid", "PM", "DM".

### TC-29: Heartbeat-based health detection — alive agent
- **Precondition**: Agent running with heartbeat writing epoch every 5 seconds.
- **Steps**:
  1. Run `python references/scripts/health_check.py --json`
- **Expected**: Agent reported as "alive" with heartbeat age < 10 seconds.
- **Verification**: JSON output shows status "alive" for the agent.

### TC-30: Heartbeat-based health detection — dead agent
- **Precondition**: Agent stopped. `.health` file contains epoch from 60 seconds ago (stale).
- **Steps**:
  1. Run `python references/scripts/health_check.py --json`
- **Expected**: Agent reported as "dead" with message about stale heartbeat.
- **Verification**: JSON output shows status "dead" or "stalled".

### TC-31: Heartbeat-based health detection — missing health file
- **Precondition**: Agent directory exists but no `.health` file.
- **Steps**:
  1. Run `python references/scripts/health_check.py --json`
- **Expected**: Agent reported as "dead" with "no heartbeat file" message.
- **Verification**: JSON output shows status "dead".

### TC-32: PM context pressure monitoring
- **Precondition**: PM agent running. Skill agent has `context-pressure` file showing 75%. Threshold in config.md is 70%.
- **Steps**:
  1. PM runs its health check step (Step 7)
  2. PM reads context-pressure for all agents
- **Expected**: PM detects skill agent exceeds threshold. If DM present, files a reboot task to DM. If DM absent, runs `reboot_agent.py skill` directly.
- **Verification**: Either a GitHub Issue is filed for DM or skill agent is rebooted.

### TC-33: DM post-ship reboot
- **Precondition**: DM ships a delivery that modifies `references/sub-skills/common/agent-lifecycle.md` (agent template change).
- **Steps**:
  1. DM completes shipping
  2. DM identifies affected agents
  3. DM runs `python references/scripts/reboot_agent.py skill`
- **Expected**: Skill agent reboots to pick up template changes.
- **Verification**: Skill agent running with new PID. DM logs the reboot in the issue.

---

### Section D: Migration & Transition

---

### TC-34: Transition — health_check.py handles old .health format
- **Precondition**: Old wrapper still running, writing `.health` as `alive|boot_epoch=1713700000`.
- **Steps**:
  1. Run `python references/scripts/health_check.py --json` (new version)
- **Expected**: health_check.py parses old format correctly. Reports agent as alive (if the old format indicates alive status).
- **Verification**: JSON output shows correct status despite old format.

### TC-35: Transition — health_check.py handles new .health format
- **Precondition**: New wrapper running, writing `.health` as plain epoch integer (e.g., `1713700000`).
- **Steps**:
  1. Run `python references/scripts/health_check.py --json`
- **Expected**: health_check.py parses new format (int parse) correctly. Reports agent as alive.
- **Verification**: JSON output shows "alive" with heartbeat age < 10s.

### TC-36: Transition — mixed old and new agents simultaneously
- **Precondition**: Agent "pm" running with old wrapper (old health format). Agent "skill" running with new wrapper (new health format).
- **Steps**:
  1. Run `python references/scripts/health_check.py`
- **Expected**: Both agents reported correctly. PM shows alive (old format parsed). Skill shows alive (new format parsed). No false "dead" reports.
- **Verification**: Health check output shows both agents healthy.

### TC-37: Existing state files handled gracefully
- **Precondition**: Directory contains old runtime files: `boot-attempts.log`, `boot-lock`, `watchdog-log.txt`, old-format `.health` files.
- **Steps**:
  1. Start agent with new wrapper
  2. Run health_check.py
- **Expected**: Old files are ignored. New wrapper creates new `.pid` and heartbeat `.health`. No errors from orphaned old files.
- **Verification**: Agent starts successfully. health_check.py works correctly.

### TC-38: Windows PowerShell parity — singleton enforcement
- **Precondition**: Windows machine. PowerShell wrapper available.
- **Steps**:
  1. Start agent via `start-skill.ps1`
  2. Attempt to start again via `start-skill.ps1` in a new terminal
- **Expected**: Second invocation detects existing PID and exits. Identical behavior to bash wrapper.
- **Verification**: Only one claude process running.

### TC-39: Windows PowerShell parity — heartbeat atomic write
- **Precondition**: Windows machine. Agent running with PowerShell wrapper.
- **Steps**:
  1. Read `.health` file rapidly (every 100ms for 5 seconds) while heartbeat is writing
- **Expected**: No partial reads, no file locking errors. Atomic write pattern (`.tmp` + `Move-Item`) prevents corruption.
- **Verification**: Every read returns a valid integer epoch.

### TC-40: Windows PowerShell parity — cleanup trap
- **Precondition**: Windows machine. Agent running with PowerShell wrapper.
- **Steps**:
  1. Close the terminal (or send termination signal)
- **Expected**: PowerShell cleanup block fires. `.pid` file removed. Heartbeat job stopped. Identical cleanup behavior to bash.
- **Verification**: No orphaned `.pid` file or heartbeat job.

### TC-41: Deploy order — code changes before template regeneration
- **Precondition**: Old wrappers running. New code deployed (reboot_agent.py, simplified health_check.py, simplified boot_remote.py).
- **Steps**:
  1. Deploy code changes without regenerating templates
  2. Run health_check.py against old-format agents
  3. Run reboot_agent.py against a running agent
- **Expected**: New health_check.py handles old format (transition code). reboot_agent.py works with old wrapper (writes sentinel, waits for idle, kills process). Old wrapper may or may not handle the sentinel (if old wrapper checks for it, great; if not, manual restart needed).
- **Verification**: No errors from new code against old wrappers.

### TC-42: compose.py install regenerates all files
- **Precondition**: Template changes applied. Sub-skill changes applied.
- **Steps**:
  1. Run `python references/scripts/compose.py install`
- **Expected**: All `.squidsquad/start-*.sh`, `.squidsquad/start-*.ps1`, `.squidsquad/*/CLAUDE.md`, and `references/agent-instructions.md` regenerated from new templates.
- **Verification**: `diff references/templates/start-role.sh .squidsquad/start-skill.sh` shows only role-specific substitutions.

---

### Section E: Side Effect Regression Tests

---

### TC-43: pipeline-sentinel still works with simplified health_check.py
- **Precondition**: Pipeline sentinel (Step 4f) references `health_check.py --json` for dead-agent detection.
- **Steps**:
  1. Run `python references/scripts/health_check.py --json`
  2. Verify output structure matches what pipeline_sentinel.md expects
- **Expected**: JSON output has same structure (per-agent entries with status field). Pipeline sentinel can parse it.
- **Verification**: `python -c "import json,sys; d=json.loads(sys.stdin.read()); assert all('status' in a for a in d.values())"` with health_check.py output piped in.

### TC-44: cycle_pre.py context pressure reading unchanged
- **Precondition**: `context-pressure` file exists for an agent.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Check context_pressure field in cycle-input.json
- **Expected**: cycle_pre.py still reads context pressure correctly. `_read_context_pressure()` function unchanged.
- **Verification**: cycle-input.json has valid `context_pressure` object.

### TC-45: cycle_post.py restart sentinel guarded by context pressure
- **Precondition**: Agent completes a cycle. Context pressure below threshold.
- **Steps**:
  1. Agent runs cycle_post.py
  2. Inspect whether `.restart` sentinel was written
- **Expected**: No `.restart` sentinel written (pressure below threshold). cycle_post.py only writes sentinel when `restart_needed: true` AND context pressure exceeds threshold.
- **Verification**: `test ! -f .squidsquad/skill/.restart`

### TC-46: boot_remote.py spawn logic still works
- **Precondition**: Agent "skill" is not running (no alive PID). New simplified boot_remote.py deployed.
- **Steps**:
  1. Run `python references/scripts/boot_remote.py --role skill`
- **Expected**: boot_remote.py spawns a new terminal with the start script. No cooldown check, no boot-lock, no boot-attempts logging.
- **Verification**: Agent starts in a new terminal. `.pid` file created.

### TC-47: boot_remote.py heartbeat-based needs_boot check
- **Precondition**: Agent health file missing or stale.
- **Steps**:
  1. Run `python references/scripts/boot_remote.py --all --json`
- **Expected**: Simplified `_needs_boot()` reads heartbeat file. If epoch >10s old or missing, reports agent needs boot.
- **Verification**: JSON output shows `action: "spawn"` for dead agents.

### TC-48: scan_index.py and model_router.py unaffected
- **Precondition**: Feature branch applied. These scripts reference `.health` for scanning/diagnostics.
- **Steps**:
  1. Run `python references/scripts/scan_index.py` (if applicable)
  2. Run `python references/scripts/model_router.py` (if applicable)
- **Expected**: Both scripts work with new heartbeat format or are tolerant of format changes.
- **Verification**: No errors or exceptions.

### TC-49: .restart sentinel ownership — only reboot_agent.py and context-pressure self-restart
- **Precondition**: Full codebase search.
- **Steps**:
  1. Search all code for writes to `.restart` sentinel
- **Expected**: Only two sources write `.restart`: reboot_agent.py (external reboot) and cycle_post.py (context pressure self-restart). No other code writes this file.
- **Verification**: `grep -rn "\.restart" references/scripts/ --include="*.py" | grep -v "read\|exist\|check\|delete\|remove"` shows only reboot_agent.py and cycle_post.py.

---

### Section F: Upgrade Verification Tests

---

### TC-50: Fresh install — no old files, new wrapper works
- **Precondition**: Clean clone of SquidSquad. No prior agent state.
- **Steps**:
  1. Run `python references/scripts/compose.py install`
  2. Start an agent
- **Expected**: New wrapper boots successfully. Heartbeat starts. No errors about missing old files.
- **Verification**: Agent running, heartbeat active, health_check.py reports alive.

### TC-51: Upgrade from old version — old health format transition
- **Precondition**: Existing SquidSquad install with old-format `.health` files (`alive|boot_epoch=...`).
- **Steps**:
  1. Pull new code
  2. Run `python references/scripts/compose.py install`
  3. Run health_check.py before restarting any agents
- **Expected**: health_check.py correctly parses old format during transition. No false "dead" reports.
- **Verification**: All agents that were alive before the upgrade still show as alive.

### TC-52: Upgrade — old runtime files don't interfere
- **Precondition**: Existing install has `boot-attempts.log`, `boot-lock`, `watchdog-log.txt`.
- **Steps**:
  1. Pull new code
  2. Start agents with new wrapper
- **Expected**: Old files are inert. New wrapper ignores them. No errors.
- **Verification**: Agent starts successfully. Old files can be manually cleaned up.

### TC-53: Upgrade — compose.py install regenerates wrappers
- **Precondition**: Old wrapper templates in `.squidsquad/start-*.sh`.
- **Steps**:
  1. Run `python references/scripts/compose.py install`
  2. Compare regenerated wrappers to new templates
- **Expected**: All `start-*.sh` and `start-*.ps1` files regenerated from new simplified template. Old 322-line wrappers replaced with ~100-line versions.
- **Verification**: `wc -l .squidsquad/start-skill.sh` shows ~100-110 lines (not ~322).

### TC-54: Upgrade — sub-skill composition updated
- **Precondition**: Old includes.yml references `common/self-restart`, `pm-specific/health-check`, `common/boot-remote-agents`.
- **Steps**:
  1. Run `python references/scripts/compose.py install`
  2. Read generated CLAUDE.md for PM role
- **Expected**: PM CLAUDE.md includes agent-lifecycle.md content (context pressure monitoring, reboot coordination). Old self-restart watchdog references are gone.
- **Verification**: `grep "agent-lifecycle\|reboot_agent\|heartbeat" .squidsquad/pm/CLAUDE.md` returns matches. `grep "watchdog" .squidsquad/pm/CLAUDE.md` returns empty.

---

## Smoke Tests

- [ ] `python references/scripts/reboot_agent.py --help` prints usage without error
- [ ] `python references/scripts/reboot_agent.py nonexistent-role` exits with code 2
- [ ] `python references/scripts/health_check.py` runs without error (exit 0)
- [ ] `python references/scripts/health_check.py --json` returns valid JSON
- [ ] `python references/scripts/boot_remote.py --role skill --json` runs without import errors
- [ ] `references/sub-skills/common/agent-lifecycle.md` exists and is non-empty
- [ ] `references/scripts/watchdog.py` does NOT exist
- [ ] `tests/test_watchdog.py` does NOT exist
- [ ] New wrapper template is <150 lines: `wc -l references/templates/start-role.sh`
- [ ] `python tests/run_tests.py` passes (all remaining tests green)
- [ ] `grep -r "watchdog" references/scripts/*.py` returns no hits

---

## Regression Risks

- **False "dead" during transition**: If health_check.py is deployed before agents restart, old health format might be misread. Mitigated by TC-34/TC-35/TC-36 transition tests.
- **PM health step activation**: PM's health check was previously a no-op (watchdog handled it). Now PM must actively monitor. Risk: PM step fails or is slow. Mitigated by TC-32.
- **Pipeline sentinel breakage**: pipeline_sentinel.md depends on `health_check.py --json` output format. Mitigated by TC-43.
- **boot_remote.py regression**: Removing ~300 lines from boot_remote.py could break spawn logic. Mitigated by TC-46/TC-47.
- **cycle_post.py self-restart guard**: If the guard is too strict, PM cannot self-restart for context pressure (the one exception). If too loose, agents self-restart for arbitrary reasons. Mitigated by TC-9/TC-10/TC-45.
- **Windows heartbeat race condition**: Concurrent read/write of `.health` on Windows could cause partial reads. Mitigated by TC-39 (atomic write pattern).
- **Orphaned heartbeat process**: If wrapper exits abnormally without cleanup trap, background heartbeat subshell keeps running. Low risk but could cause stale "alive" reports. Mitigated by TC-12.
- **crash retry detection**: If wrapper cannot distinguish "immediate crash" (<30s) from "ran a full cycle," it might exit prematurely or retry indefinitely. Mitigated by TC-7/TC-8.

---

## Comprehension Test Specs (CQs)

These tests verify that agents correctly understand their lifecycle responsibilities under the new model. Each CQ is executed by spawning a fresh agent and asking it questions about the new instructions. The agent must answer from its composed CLAUDE.md without access to planning artifacts.

---

### CQ-1: PM understands it monitors context pressure of all agents

**Target role**: PM

**Setup**: Spawn a fresh PM agent with the composed CLAUDE.md (post-compose.py install). No planning artifacts provided.

**Questions**:
1. "Which agents' context pressure do you monitor?"
   - **Expected**: PM monitors ALL agents listed in config.md Dev Agents list, not just itself.
2. "What do you do when an agent's context pressure exceeds the threshold?"
   - **Expected**: PM checks if DM is present. If DM present, files a reboot task to DM. If DM absent, runs `reboot_agent.py <role>` directly.
3. "Where do you find each agent's context pressure?"
   - **Expected**: `.squidsquad/<agent>/context-pressure` file (written by statusline hook).
4. "Where do you find the threshold?"
   - **Expected**: `config.md` — Context Pressure Threshold setting.

**Failure criteria**: If PM says it only monitors its own pressure, or says it relies on the watchdog, or says it does not monitor pressure at all — FAIL.

---

### CQ-2: PM knows to plan reboots for human, DM executes

**Target role**: PM

**Setup**: Spawn a fresh PM agent with the composed CLAUDE.md.

**Questions**:
1. "A human asks you to reboot the skill agent. What do you do?"
   - **Expected**: If DM is present, PM files a task to DM requesting reboot of skill. If DM is absent, PM runs `reboot_agent.py skill` directly.
2. "Can you reboot yourself?"
   - **Expected**: PM cannot reboot itself via reboot_agent.py (it would kill its own session). PM can write its own `.restart` sentinel when context pressure exceeds threshold. The wrapper handles the actual restart.
3. "What command does DM use to reboot an agent?"
   - **Expected**: `python references/scripts/reboot_agent.py <role>`

**Failure criteria**: If PM says it reboots agents directly without checking for DM, or says the watchdog handles reboots, or does not know about reboot_agent.py — FAIL.

---

### CQ-3: DM knows to issue reboot after shipping template changes

**Target role**: DM

**Setup**: Spawn a fresh DM agent with the composed CLAUDE.md (post-compose.py install).

**Questions**:
1. "You just shipped a delivery that modifies `references/sub-skills/common/agent-lifecycle.md`. What should you do next?"
   - **Expected**: DM identifies which agents include agent-lifecycle.md (all roles that compose it). Runs `python references/scripts/reboot_agent.py <role>` for each affected agent. Logs the reboot in the issue.
2. "What types of changes trigger a post-ship reboot?"
   - **Expected**: Changes to CLAUDE.md templates, SOUL.md, sub-skills, config.md settings that affect agent behavior, includes.yml.
3. "What if you ship a change that only affects README.md?"
   - **Expected**: No reboot needed — README.md is not an agent template or instruction file.

**Failure criteria**: If DM does not mention post-ship reboot, or says the watchdog detects template changes, or does not know the reboot_agent.py command — FAIL.

---

### CQ-4: Agents understand self-restart is context-pressure only

**Target role**: skill (dev agent)

**Setup**: Spawn a fresh skill agent with the composed CLAUDE.md.

**Questions**:
1. "Under what circumstances can you trigger your own restart?"
   - **Expected**: Only when context pressure exceeds the threshold. Agent writes `.restart` sentinel via cycle_post.py. No other self-restart reasons are valid.
2. "If you detect that your CLAUDE.md template has changed, what do you do?"
   - **Expected**: Agent does NOT self-restart. DM handles post-ship reboots for template changes. Agent continues until DM reboots it.
3. "What happens after you write the `.restart` sentinel?"
   - **Expected**: Agent's claude process exits normally at end of cycle. Wrapper detects `.restart` sentinel, deletes it, respawns a fresh session. The new session reads `working-state.md` to resume.

**Failure criteria**: If agent says it can self-restart for arbitrary reasons, or mentions the watchdog, or says it self-restarts on template change — FAIL.

---

### CQ-5: PM understands heartbeat-based health detection

**Target role**: PM

**Setup**: Spawn a fresh PM agent with the composed CLAUDE.md.

**Questions**:
1. "How do you determine if an agent is alive or dead?"
   - **Expected**: Run `python references/scripts/health_check.py --json`. The script reads `.health` files which contain a heartbeat epoch. If the epoch is within 10 seconds of current time, agent is alive. If stale or missing, agent is dead.
2. "What do you do if an agent is detected as dead?"
   - **Expected**: Run `python references/scripts/boot_remote.py --role <agent>` to spawn the agent in a new terminal.
3. "Do you check PIDs to determine liveness?"
   - **Expected**: No. PID-based liveness detection is removed. Heartbeat is the sole liveness signal.

**Failure criteria**: If PM mentions PID cross-check, mtime fallback, or auto-correction of health files — FAIL.

---

### CQ-6: Agents understand wrapper guarantees

**Target role**: skill (dev agent)

**Setup**: Spawn a fresh skill agent with the composed CLAUDE.md.

**Questions**:
1. "What prevents two copies of you from running simultaneously?"
   - **Expected**: The wrapper's PID lock. If `.pid` file exists and the PID is alive, the second wrapper instance exits immediately.
2. "What happens if your claude process crashes?"
   - **Expected**: Wrapper restarts once (one retry). If the retry crashes immediately (<30s runtime), wrapper exits. PM detects dead heartbeat and handles via boot_remote.py.
3. "Can PM or DM kill you while you are in the middle of work?"
   - **Expected**: No. reboot_agent.py waits for the agent to be idle before killing. Only the `--force` flag skips the idle wait.

**Failure criteria**: If agent mentions the 50-restart loop, watchdog, cooldown, or says nothing prevents concurrent instances — FAIL.
