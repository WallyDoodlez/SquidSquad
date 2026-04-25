# FEAT-PM-2496 Test Plan — Unify Agent Lifecycle

## Test Cases

### TC-1: Reboot of running agent kills wrapper and spawns new wrapper
- **Precondition**: Agent `skill` is running. `.squidsquad/skill/.pid` contains the wrapper PID. Process is alive. Agent is idle (`current-state` starts with `idle`).
- **Steps**: Run `python references/scripts/reboot_agent.py skill`.
- **Expected**: Script writes `.restart` sentinel, waits for idle, kills the wrapper PID, then calls boot_remote spawn logic to start a new wrapper. New wrapper starts, writes a new PID to `.pid`. Exit code 0.
- **Verification**:
  - Old PID is no longer alive: `tasklist /FI "PID eq <old_pid>"` (Windows) or `kill -0 <old_pid>` (Unix) returns not found.
  - `.squidsquad/skill/.pid` contains a new PID that IS alive.
  - `.squidsquad/skill/.restart` sentinel is consumed (deleted by wrapper on respawn).

### TC-2: Reboot of dead agent (stale .pid) boots the agent
- **Precondition**: `.squidsquad/skill/.pid` exists but the PID inside is dead (process no longer running). No `.stop` sentinel.
- **Steps**: Run `python references/scripts/reboot_agent.py skill`.
- **Expected**: Script detects PID is dead. Instead of returning 0 (no-op), it calls boot_remote spawn logic to start the wrapper. Agent boots successfully. Exit code 0.
- **Verification**:
  - `.squidsquad/skill/.pid` contains a new, alive PID.
  - Console output indicates agent was booted (not "not running" no-op).
  - `.health` file is written by the new wrapper within 10 seconds.

### TC-3: Reboot of agent with no .pid file boots the agent
- **Precondition**: `.squidsquad/skill/.pid` does not exist. No `.stop` sentinel. Boot script `start-skill.ps1` or `start-skill.sh` exists.
- **Steps**: Run `python references/scripts/reboot_agent.py skill`.
- **Expected**: Script detects no PID file. Calls boot_remote spawn logic to start the wrapper. Agent boots. Exit code 0.
- **Verification**:
  - `.squidsquad/skill/.pid` is created with a valid, alive PID.
  - Console output indicates agent was booted.

### TC-4: .stop sentinel prevents respawn
- **Precondition**: `.squidsquad/skill/.stop` sentinel exists. Agent may or may not be running.
- **Steps**: Run `python references/scripts/reboot_agent.py skill`.
- **Expected**: Script detects `.stop` sentinel. Does NOT spawn a new wrapper. Prints a message indicating the agent is explicitly stopped. Exit code 0.
- **Verification**:
  - No new terminal or process spawned.
  - Console output contains "stopped" or ".stop" indication.
  - `.squidsquad/skill/.pid` is NOT updated.

### TC-5: Timeout does NOT spawn new wrapper
- **Precondition**: Agent `skill` is running and busy (current-state does NOT start with `idle`). Short timeout configured.
- **Steps**: Run `python references/scripts/reboot_agent.py skill --timeout 4`.
- **Expected**: Script writes `.restart` sentinel, polls for idle, times out after 4 seconds. Cleans up `.restart` sentinel. Does NOT kill the process. Does NOT call boot_remote spawn logic. Exit code 1.
- **Verification**:
  - `.restart` sentinel is removed.
  - Original PID is still alive and unchanged.
  - Console output includes "timeout" message on stderr.
  - No new terminal or process spawned.

### TC-6: PID file stores wrapper PID, not child PID
- **Precondition**: Wrapper script (`start-skill.sh` or `start-skill.ps1`) is the entrypoint.
- **Steps**: Start the wrapper manually. Read `.squidsquad/skill/.pid`. Compare the stored PID against the wrapper process PID (e.g., `$$` in bash, `$PID` in PowerShell) and the child Claude process PID.
- **Expected**: `.pid` contains the wrapper's own PID, not the child process PID.
- **Verification**:
  - On Unix: wrapper writes `echo $$ > .squidsquad/skill/.pid`. Verify `$$` matches file content.
  - On Windows: wrapper writes `$PID` to `.pid`. Verify it matches the PowerShell host process, not the spawned `claude` child.
  - Killing the `.pid` PID terminates both wrapper and child.

### TC-7: Clone-path resolution unified between reboot_agent and boot_remote
- **Precondition**: Multi-clone setup with `~/.squidsquad/clones/skill` pointing to `/path/to/skill-clone`, OR `.squidsquad/.local-config` with `- **skill**: /path/to/skill-clone`.
- **Steps**:
  1. Run `python references/scripts/reboot_agent.py skill` and observe which clone path it resolves.
  2. Run `python references/scripts/boot_remote.py --role skill --dry-run` and observe which clone path it resolves.
- **Expected**: Both scripts resolve to the same clone path. Reboot uses boot_remote's `_parse_local_config()` logic (shared filesystem `~/.squidsquad/clones/` first, then `.local-config` fallback) rather than its own legacy markdown parser.
- **Verification**:
  - Add debug/print or inspect code: `reboot_agent._get_clone_path("skill")` returns the same `Path` as `boot_remote._get_clone_path("skill")`.
  - If `~/.squidsquad/clones/skill` exists, it takes precedence over `.local-config` in both scripts.

### TC-8: --all flag iterates roles correctly (regression #2353)
- **Precondition**: `config.py get_agents()` returns a list. List may contain dicts (`{"id": "skill", ...}`) or strings (`"skill"`).
- **Steps**: Run `python references/scripts/reboot_agent.py --all`.
- **Expected**: Script iterates all agents without error. Each agent is rebooted (or booted if dead). No `TypeError` from treating a string as a dict or vice versa.
- **Verification**:
  - Exit code is 0 (or 1 only if a specific agent timed out).
  - Console output shows one line per agent role.
  - No Python traceback or `TypeError`.

### TC-9: Double-start prevention — verify PID dead before spawning
- **Precondition**: Agent `skill` is running with a valid, alive PID in `.pid`.
- **Steps**: Call the spawn logic directly (simulate reboot completing the kill step but PID still alive due to race condition).
- **Expected**: Before spawning a new wrapper, the script checks `_is_process_alive(pid)`. If PID is still alive, it does NOT spawn a second wrapper. Waits or retries until PID is confirmed dead.
- **Verification**:
  - Only one wrapper process exists for the role at any time.
  - If PID is alive, spawn is skipped with a diagnostic message.

### TC-10: Cross-platform — Windows (Start-Process) and Unix (tmux/osascript)
- **Precondition**: Reboot completes (kill + spawn path reached).
- **Steps**:
  - On Windows: Run `python references/scripts/reboot_agent.py skill`. Verify spawn uses `wt.exe` or `cmd /c start` fallback.
  - On Unix/macOS: Run `python references/scripts/reboot_agent.py skill`. Verify spawn uses `tmux new-session` or `osascript`.
- **Expected**: Spawn uses the correct platform-specific terminal mechanism from `boot_remote._spawn_terminal()`.
- **Verification**:
  - Windows: new terminal tab/window appears titled `squidsquad-skill`.
  - Linux: `tmux list-sessions` shows `squidsquad-skill`.
  - macOS: Terminal.app opens a new window.

### TC-11: Singleton enforcement — new wrapper refuses if another wrapper PID is alive
- **Precondition**: Wrapper for `skill` is already running with PID in `.pid`.
- **Steps**: Manually attempt to start a second instance of the wrapper (`bash .squidsquad/start-skill.sh` or `pwsh .squidsquad/start-skill.ps1`).
- **Expected**: The second wrapper detects an existing alive PID in `.pid`, prints a message indicating another instance is already running, and exits without starting.
- **Verification**:
  - Second wrapper exits with non-zero code or prints "already running".
  - Only one wrapper process exists.
  - `.pid` file is not overwritten.

### TC-12: Existing boot_remote.py behavior unchanged for normal boot
- **Precondition**: Agent `skill` is dead (no PID file or PID is dead). No `.stop` sentinel.
- **Steps**: Run `python references/scripts/boot_remote.py --role skill`.
- **Expected**: Agent is booted via terminal spawn, identical to pre-FEAT-2496 behavior. `_needs_boot()` logic, `_find_boot_script()`, `_spawn_terminal()` all produce the same results as before the patch.
- **Verification**:
  - Output matches format: `[skill] spawn — OK: spawned via ...`
  - Exit code 0.
  - `--dry-run` still works: `[skill] dry-run — OK: would boot: ...`
  - `--all` still iterates `_get_all_roles()` from `config.md`, excludes `pm`.
  - `--json` output schema unchanged.

### TC-13: Force reboot kills immediately and spawns
- **Precondition**: Agent `skill` is running and busy (not idle).
- **Steps**: Run `python references/scripts/reboot_agent.py skill --force`.
- **Expected**: Script writes `.restart`, kills the PID immediately (no idle wait), then spawns a new wrapper via boot_remote logic. Exit code 0.
- **Verification**:
  - Old PID is dead.
  - New PID is alive in `.pid`.
  - No timeout delay observed.

### TC-14: Reboot with --force still respects .stop sentinel
- **Precondition**: `.squidsquad/skill/.stop` exists. Agent may be running.
- **Steps**: Run `python references/scripts/reboot_agent.py skill --force`.
- **Expected**: `.stop` is checked before any kill/spawn logic. Agent is not killed and not respawned. Message indicates agent is stopped.
- **Verification**:
  - Console output mentions `.stop` or "stopped".
  - No process killed, no new process spawned.

## Smoke Tests
- [ ] `python references/scripts/reboot_agent.py skill` on a running idle agent completes in <10 seconds
- [ ] `python references/scripts/reboot_agent.py --all` processes every configured role without crash
- [ ] `python references/scripts/boot_remote.py --role skill --dry-run` output unchanged from before patch
- [ ] `python references/scripts/boot_remote.py --all --json` JSON schema unchanged
- [ ] `.pid` file after fresh boot contains a single integer (no trailing whitespace or extra lines)
- [ ] Wrapper heartbeat (`.health` file) updates within 10 seconds of boot

## Regression Risks
- **boot_remote.py API change**: If reboot_agent imports or calls boot_remote functions, ensure boot_remote's public interface (`boot_agent`, `boot_all`, `main`) is not altered. Any refactoring to expose spawn logic must not break existing callers.
- **Clone-path resolution change**: Unifying clone-path parsing could change which path is resolved for roles not listed in `~/.squidsquad/clones/`. Verify fallback to `REPO_ROOT` still works for single-clone setups.
- **--all dict regression (#2353)**: The fix for iterating `agent['id'] if isinstance(agent, dict) else agent` must be preserved. Confirm `get_agents()` return type is handled correctly.
- **Exit code semantics**: Current behavior returns 0 for "not running". New behavior (boot instead of no-op) should still return 0 on success. Ensure timeout still returns 1.
- **Health file gating in boot_remote**: `_needs_boot()` uses `.health` as primary signal. If reboot_agent calls boot_remote's spawn path after killing, the stale `.health=alive` from the just-killed wrapper could cause `_needs_boot()` to return `False`. Reboot must either bypass `_needs_boot()` or call the spawn function directly.
- **Windows process tree**: `taskkill /F /PID` on Windows kills the wrapper but child processes may survive. Verify child cleanup on Windows (may need `/T` flag for tree kill).

## Comprehension Questions

### CQ-1: What does reboot_agent.py do when .pid exists but the process is dead?
- **Files**: `references/scripts/reboot_agent.py`
- **Expected**: After the patch, it boots the agent (calls boot_remote spawn logic) instead of returning 0 as a no-op. "Reboot == ensure running" per CONTEXT.md locked decisions.

### CQ-2: What happens if reboot times out waiting for idle?
- **Files**: `references/scripts/reboot_agent.py`
- **Expected**: The `.restart` sentinel is cleaned up, the process is NOT killed, and NO new wrapper is spawned. Exit code 1. The agent continues running its current work undisturbed.

### CQ-3: How does reboot_agent.py resolve the clone path for a role?
- **Files**: `references/scripts/reboot_agent.py`, `references/scripts/boot_remote.py`
- **Expected**: After the patch, it uses the same resolution as boot_remote: `~/.squidsquad/clones/` (shared filesystem) first, then `.local-config` (legacy markdown format) fallback, then `REPO_ROOT` default. Not the old `_get_clone_path()` that only parsed `.local-config`.

### CQ-4: What does .pid represent?
- **Files**: `references/scripts/reboot_agent.py`, `.squidsquad/pm/planning/FEAT-PM-2496-CONTEXT.md`
- **Expected**: `.pid` always stores the wrapper process PID (not the child Claude PID). Killing the wrapper PID stops both wrapper and child. Singleton enforcement checks the wrapper PID.

### CQ-5: Does reboot respawn an agent that has a .stop sentinel?
- **Files**: `references/scripts/reboot_agent.py`, `references/scripts/boot_remote.py`
- **Expected**: No. If `.stop` exists, reboot does not respawn. It prints a message indicating the agent is explicitly stopped. This applies to both normal and force reboot.
