# FEAT-PM-4439 Test Plan — SquidSquad Harness Phase 1

## Overview

FastAPI harness on localhost managing agent lifecycle via HTTP API. Agents run in visible terminal
windows. CLI (`squidsquad.py`) communicates with harness over HTTP. Default port 7373,
discovery via `.squidsquad/.harness-port`.

---

## Test Cases

### TC-1: Harness starts in visible terminal tab

- **Precondition**: No harness process running. `wt.exe` available.
- **Steps**:
  1. Run `python squidsquad.py start` (or invoke harness start directly).
  2. Observe Windows Terminal.
- **Expected**: A new `wt.exe` tab appears titled `squidsquad-harness`. FastAPI startup log is
  visible in that tab. Ctrl+C in the tab stops the harness cleanly.
- **Verification**: Check Task Manager for a Python process hosting FastAPI. Confirm tab title
  via visual inspection or `wt.exe` process listing.

---

### TC-2: Harness writes `.harness-port` discovery file

- **Precondition**: No existing `.squidsquad/.harness-port`. Harness not running.
- **Steps**:
  1. Start the harness.
  2. Wait for FastAPI startup to complete (poll until `/status` responds or file exists).
  3. Read `.squidsquad/.harness-port`.
- **Expected**: File exists and contains a valid port number (integer, 1024–65535). Port matches
  the port FastAPI is actually listening on (default 7373 if available).
- **Verification**:
  ```
  cat .squidsquad/.harness-port
  curl http://localhost:$(cat .squidsquad/.harness-port)/status
  ```

---

### TC-3: CLI detects running harness via discovery file

- **Precondition**: Harness is running. `.squidsquad/.harness-port` exists with correct port.
- **Steps**:
  1. Run `python squidsquad.py status`.
- **Expected**: CLI reads `.harness-port`, sends `GET /status` to the correct port, and prints
  health output. Exit code 0.
- **Verification**: Confirm port used by CLI matches file content. Response includes agent list
  and harness uptime or similar health fields.

---

### TC-4: POST /agents/\<role\>/start spawns agent in visible terminal

- **Precondition**: Harness running. Target agent (e.g. `skill`) not currently running.
- **Steps**:
  1. `curl -X POST http://localhost:7373/agents/skill/start`
- **Expected**:
  - HTTP 200 with JSON body indicating spawn accepted.
  - A new visible terminal window/tab opens for the `skill` agent (same behaviour as current
    `boot_remote.boot_agent()`).
  - Harness internal state shows `skill` as `starting` or `running`.
- **Verification**:
  - `curl http://localhost:7373/status` — `skill` shows non-stopped state.
  - Visual: terminal window for skill agent present.

---

### TC-5: POST /agents/\<role\>/stop stops agent gracefully

- **Precondition**: Harness running. `skill` agent running and healthy.
- **Steps**:
  1. `curl -X POST http://localhost:7373/agents/skill/stop`
- **Expected**:
  - HTTP 200.
  - Harness writes `.stop` sentinel for the agent (consistent with current graceful-stop
    mechanism).
  - Agent process exits at end of its current cycle. Harness state transitions to `stopped`.
- **Verification**:
  - `curl http://localhost:7373/status` — `skill` shows `stopped` after a cycle boundary.
  - `.squidsquad/skill/.stop` sentinel file exists immediately after the POST.

---

### TC-6: POST /agents/\<role\>/restart kills and respawns agent

- **Precondition**: Harness running. `skill` agent running.
- **Steps**:
  1. Note the current PID of the skill agent process.
  2. `curl -X POST http://localhost:7373/agents/skill/restart`
  3. Wait for respawn.
- **Expected**:
  - HTTP 200.
  - Old PID is killed (using `reboot_agent._kill_process()`).
  - A new terminal window/tab opens for `skill` with a new PID.
  - Harness state shows `skill` as `running` after respawn.
- **Verification**:
  - Old PID no longer appears in process list.
  - `curl http://localhost:7373/status` — `skill` `running` with new PID.
  - New terminal tab visible.

---

### TC-7: POST /agents/all/start spawns all configured agents

- **Precondition**: Harness running. No dev agents running. `config.md` lists `qa` and `skill`.
- **Steps**:
  1. `curl -X POST http://localhost:7373/agents/all/start`
- **Expected**:
  - HTTP 200.
  - `boot_remote.boot_agent()` called for each agent listed in config.
  - One visible terminal per agent opens.
  - All agents appear in `GET /status` with non-stopped state within poll window.
- **Verification**:
  - `curl http://localhost:7373/status` — both `qa` and `skill` show `starting` or `running`.
  - Two new terminal windows present.

---

### TC-8: GET /status returns health for all agents

- **Precondition**: Harness running. At least one agent running.
- **Steps**:
  1. `curl http://localhost:7373/status`
- **Expected**:
  - HTTP 200 with JSON body.
  - Body includes harness health (port, uptime or version).
  - Body includes per-agent health derived from sentinel files (`.pid`, `.claude-pid`, `.health`).
  - Health values reflect actual on-disk state (e.g., if `.health` heartbeat is stale, agent
    reported as `stalled`).
- **Verification**:
  - Kill agent process externally; wait 15 s; re-query `/status` — agent shows `stalled` or
    `stopped` (not `running`).
  - Confirm JSON structure includes at least `harness` and `agents` keys.

---

### TC-9: POST /shutdown stops all agents then exits harness

- **Precondition**: Harness running. One or more agents running.
- **Steps**:
  1. `curl -X POST http://localhost:7373/shutdown`
- **Expected**:
  - HTTP 200 (or 202 Accepted).
  - Harness writes `.stop` sentinels for all running agents.
  - Harness waits for agents to idle (reads `current-state`) or kills remaining processes after
    a timeout.
  - `.squidsquad/.harness-port` is deleted.
  - Harness process exits cleanly.
- **Verification**:
  - After completion: `.squidsquad/.harness-port` does not exist.
  - No `squidsquad-harness` tab in terminal (or process gone).
  - All agent processes gone (or their `.stop` sentinels present).

---

### TC-10: CLI error when harness not running

- **Precondition**: No harness running. `.squidsquad/.harness-port` absent (or stale/unreachable).
- **Steps**:
  1. `python squidsquad.py status`
  2. `python squidsquad.py stop skill`
  3. `python squidsquad.py restart qa`
- **Expected**: Each command prints exactly:
  ```
  Harness not running. Start with: squidsquad start
  ```
  Exit code non-zero. No stack trace or urllib exception leaked to user.
- **Verification**: Capture stdout/stderr. Assert message matches required string. Assert exit
  code != 0.

---

### TC-11: Port fallback when default port taken

- **Precondition**: Port 7373 is occupied by another process (bind a listener before test).
- **Steps**:
  1. Bind a socket to 127.0.0.1:7373.
  2. Start the harness.
  3. Read `.squidsquad/.harness-port`.
- **Expected**:
  - Harness starts successfully on the next available free port (not 7373).
  - `.squidsquad/.harness-port` contains the actual port used (not 7373).
  - `GET /status` responds on the fallback port.
  - CLI reads discovery file and communicates on the correct port.
- **Verification**:
  ```
  PORT=$(cat .squidsquad/.harness-port)
  # PORT should NOT be 7373
  curl http://localhost:$PORT/status  # must return 200
  python squidsquad.py status          # must succeed (not "harness not running")
  ```

---

### TC-12: Harness crash does not kill agents

- **Precondition**: Harness running. `skill` agent running in its own terminal.
- **Steps**:
  1. Note `skill` agent PID and confirm it is healthy.
  2. Kill the harness process forcefully (`kill -9` or Task Manager).
  3. Wait 10 seconds.
  4. Check `skill` agent.
- **Expected**:
  - `skill` agent process still running.
  - `skill` terminal still visible and active.
  - Agent continues cycling (heartbeat in `.squidsquad/skill/.health` still updating).
- **Verification**:
  - PID from step 1 still in process list.
  - `.squidsquad/skill/.health` mtime is < 10 s old after harness is gone.

---

### TC-13: Existing standalone scripts still work without harness

- **Precondition**: No harness running. `boot_remote.py` and `reboot_agent.py` present and
  unchanged from pre-harness baseline.
- **Steps**:
  1. `python references/scripts/boot_remote.py skill` (or equivalent invocation).
  2. Observe that `skill` agent spawns in a visible terminal normally.
  3. `python references/scripts/reboot_agent.py skill` — confirm kill + respawn.
  4. `python references/scripts/health_check.py` — confirm it reads sentinel files correctly.
- **Expected**: All three scripts execute successfully and produce the same behaviour as before
  the harness was introduced. No import errors, no missing function signatures.
- **Verification**:
  - Exit code 0 for each script.
  - Agent terminal opens for boot test.
  - `health_check.py` output lists agents with correct health state.
  - Confirm `boot_remote.boot_agent()` and `reboot_agent._kill_process()` function signatures
    are intact (harness imports them — breaking their signatures would break the harness too).

---

### TC-14: Full test suite regression

- **Precondition**: Codebase at the PR commit. No external processes needed beyond Python.
- **Steps**:
  1. `python tests/run_tests.py`
- **Expected**: All existing tests pass. Zero new failures introduced by harness changes.
- **Verification**: Exit code 0. No test marked FAILED or ERROR in output.

---

## Smoke Tests

- [ ] `python squidsquad.py status` responds in < 2 s when harness is running.
- [ ] `.squidsquad/.harness-port` is created within 5 s of harness startup.
- [ ] `GET /agents` returns a JSON list with at least the roles defined in `config.md`.
- [ ] `POST /agents/all/stop` does not error when all agents are already stopped (idempotent).
- [ ] Harness log output is human-readable in the terminal tab (not binary / garbled).
- [ ] `python squidsquad.py start` when harness is already running does NOT spawn a second
  harness (detects existing via `.harness-port` ping).
- [ ] CLI has no hard-coded port — always reads from `.harness-port`.

---

## Regression Risks

- **boot_remote / reboot_agent API surface**: Harness imports these directly. Any refactor to
  their public function signatures during this PR will silently break the harness. Verify
  function signatures are preserved (TC-13).
- **Sentinel file semantics**: `.stop`, `.pid`, `.claude-pid`, `.health`, `current-state` are
  read by multiple parties (wrapper, health_check.py, harness poller, PM). If the harness
  writes or deletes these files unexpectedly, existing scripts break. Confirm harness only reads
  sentinel files during health polling; writes only `.stop` on graceful shutdown.
- **Port discovery race**: If CLI reads `.harness-port` before harness finishes binding (file
  written before `uvicorn` bind completes), CLI gets a port that isn't listening yet. Harness
  must write the port file only after the server is ready to accept connections.
- **Stale `.harness-port` on crash**: If harness crashes without deleting `.harness-port`, CLI
  will read a stale port on next run. The startup sequence (TC-1 / startup in CONTEXT.md step 1)
  must handle this: ping `/status` after reading the file; if no response, treat as "not running"
  and spawn fresh harness. Verify this path explicitly.
- **Windows Terminal dependency**: `wt.exe` may not be available in all environments (CI, SSH
  sessions, Server Core). Harness should fail with a clear error rather than a silent crash if
  `wt.exe` is absent.
- **`POST /agents/all/start` with already-running agents**: Should not double-spawn. Verify
  idempotency — if an agent is already running (`.pid` present and process alive), skip it.
- **Concurrent requests**: Two CLI invocations hitting `/agents/skill/start` simultaneously
  should not spawn two skill agents. Harness needs a per-role lock or in-flight guard.

---

## Comprehension Questions

The following questions should be answerable by a fresh agent reading only the implementation
files (harness server, CLI, and CONTEXT.md). They serve as a comprehension gate for the
implementing developer.

### CQ-1: Port discovery contract

- **Question**: How does the CLI determine which port to use when communicating with the harness,
  and what happens if that file does not exist or the harness at that address does not respond?
- **Files**: `squidsquad.py` (CLI), `.squidsquad/.harness-port` (runtime artifact),
  `FEAT-PM-4439-CONTEXT.md`
- **Expected answer**: The CLI reads `.squidsquad/.harness-port` to get the port. If the file is
  absent, or if the port is present but `/status` does not respond (stale crash remnant), the CLI
  prints `"Harness not running. Start with: squidsquad start"` and exits non-zero. It does NOT
  fall back to a hard-coded 7373.

### CQ-2: Agent process isolation guarantee

- **Question**: What is the architectural reason that crashing the harness does NOT terminate the
  agent processes, and where in the implementation is this boundary enforced?
- **Files**: Harness server implementation, `boot_remote.py`, `FEAT-PM-4439-CONTEXT.md`
- **Expected answer**: Each agent is spawned in its own `wt.exe` tab via `boot_remote.boot_agent()`,
  which creates an independent OS process. The harness has no parent–child ownership over the
  agent processes — it only tracks their PIDs via sentinel files. When the harness dies, the
  agent processes are unaffected because they are not children of the harness process.

### CQ-3: Graceful shutdown sequence and sentinel semantics

- **Question**: Walk through exactly what happens — in order — when `POST /shutdown` is received.
  Which files are written or deleted, and when does the harness process itself exit?
- **Files**: Harness `/shutdown` endpoint implementation, `FEAT-PM-4439-CONTEXT.md` (Graceful
  Shutdown section)
- **Expected answer** (derived from CONTEXT.md):
  1. Harness writes `.stop` sentinel for every running agent.
  2. Harness polls `current-state` files, waiting for agents to reach idle.
  3. Any agent processes still alive after the wait are killed via `reboot_agent._kill_process()`.
  4. Harness deletes `.squidsquad/.harness-port`.
  5. Harness process exits (FastAPI shuts down).
  The harness does NOT delete agent sentinel files (`.pid`, `.health`, etc.) — those are the
  agents' own domain.

---

## Notes

- TC-12 (harness crash) and TC-11 (port fallback) are the highest-risk cases; both should be
  automated if possible.
- TC-14 (full regression) is a hard gate — no ship if any existing test fails.
- CQ-1 through CQ-3 should be used in a comprehension-test subagent spawn per the project
  standard (see `feedback_comprehension_tests_required.md` in MEMORY.md).
