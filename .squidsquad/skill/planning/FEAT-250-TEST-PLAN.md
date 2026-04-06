# FEAT-250 Test Plan — Auto-Restart Agent on Loop Limit / Context Pressure

**Feature**: #250 — Auto-restart agent when loop limit or context pressure is reached
**Files under test**: `references/templates/start-role.sh`, `references/templates/start-role.ps1`
**Test approach**: Unit tests via stub scripts; integration tests via real boot script execution with mock `claude` command
**Platform**: Bash (Linux/macOS/WSL), PowerShell (Windows)

---

## Test Infrastructure

### Conventions
- All test artifacts created in a temp directory, cleaned up in `finally` / teardown
- `claude` command is replaced by a stub script that exits after a controlled delay
- PID files, stop sentinels, and restart logs are created in the temp `.squidsquad/[role]/` directory
- Tests validate both bash and PowerShell templates where noted; otherwise bash is primary

### Stub Claude Script
A minimal script that simulates `claude` behavior:
```bash
#!/usr/bin/env bash
# stub-claude.sh — exits with configurable code after configurable delay
DELAY=${STUB_CLAUDE_DELAY:-0}
EXIT_CODE=${STUB_CLAUDE_EXIT:-0}
sleep "$DELAY"
exit "$EXIT_CODE"
```

---

## A. Unit Tests — PID Lock

**TC-001: PID file created on wrapper start**
- Precondition: No `.squidsquad/[role]/.pid` file exists
- Steps: Start boot script with stub claude (exits immediately)
- Expected: `.pid` file is created before `claude` invocation, contains a numeric PID

**TC-002: Running PID detected — wrapper aborts**
- Precondition: `.pid` file exists containing the PID of a currently running process (e.g., `sleep 999 &`)
- Steps: Attempt to start boot script
- Expected: Wrapper prints "Already running" message and exits without launching `claude`

**TC-003: Stale PID detected — wrapper cleans up and proceeds**
- Precondition: `.pid` file exists containing a PID that is not running (e.g., `99999`)
- Steps: Start boot script with stub claude
- Expected: Wrapper detects stale PID, removes old `.pid` file, creates new one, launches `claude`

**TC-004: PID file cleaned up on normal exit**
- Precondition: None
- Steps: Start boot script with stub claude that exits 0 after 1s; place `.stop` file to prevent restart loop
- Expected: After wrapper exits, `.pid` file does not exist

---

## B. Unit Tests — Stop Sentinel

**TC-005: Stop sentinel prevents restart after claude exit**
- Precondition: `.squidsquad/[role]/.stop` file exists
- Steps: Start boot script; stub claude exits 0
- Expected: Wrapper detects `.stop` file, prints "Stop file detected", does NOT restart, exits

**TC-006: Stop sentinel checked after each claude exit, not before first start**
- Precondition: No `.stop` file initially
- Steps: Start boot script; stub claude runs 1s then exits; during the cooldown window, create `.stop` file; wrapper restarts claude once
- Expected: After the second claude exit, wrapper detects `.stop` and exits. Total claude invocations: 2

**TC-007: Stop sentinel is removed after stopping**
- Precondition: `.stop` file exists
- Steps: Start boot script; stub claude exits
- Expected: After wrapper stops, `.stop` file has been removed (or left — per dev discretion; verify whichever behavior is implemented)

**TC-008: Status bar shows stopped state after sentinel stop**
- Precondition: `.stop` file exists
- Steps: Start boot script; stub claude exits
- Expected: `current-state` file contains `stopped|Agent stopped by user`

---

## C. Unit Tests — Restart Counter

**TC-009: Restart counter increments on each restart**
- Precondition: Stub claude exits immediately (fast crash, <2min runtime)
- Steps: Let wrapper restart claude 3 times, then place `.stop` file
- Expected: Restart log shows count incrementing: 1, 2, 3

**TC-010: Restart counter resets on healthy run**
- Precondition: Stub claude exits immediately twice (fast crash), then runs for >MIN_RUNTIME on third invocation
- Steps: Let wrapper restart through the sequence
- Expected: After the healthy run, restart counter resets to 0 (visible in restart log or wrapper output)

**TC-011: Wrapper stops at MAX_RESTARTS (50)**
- Precondition: Stub claude always exits immediately (fast crash)
- Steps: Let wrapper run until it hits the max restart limit
- Expected: Wrapper prints "Max restarts (50) reached", exits. `current-state` contains `error|Max restarts reached`
- Note: Use a reduced MAX_RESTARTS value (e.g., 5) for test speed, or verify the logic path rather than running 50 iterations

---

## D. Unit Tests — Exponential Backoff

**TC-012: Fast crash triggers exponential backoff delay**
- Precondition: Stub claude exits in <2s (well under MIN_RUNTIME_SECONDS)
- Steps: Let wrapper restart 3 times, record timestamps of each restart
- Expected: Delay between restarts increases exponentially (approximately 2x each iteration). First delay ~30s, second ~60s, third ~120s (or per implemented curve)

**TC-013: Backoff caps at COOLDOWN_MAX (300s)**
- Precondition: Stub claude exits immediately, restart count is high enough that backoff would exceed 300s
- Steps: Observe the cooldown value in wrapper output
- Expected: Cooldown never exceeds 300s regardless of restart count

**TC-014: Healthy run resets backoff to base cooldown**
- Precondition: Stub claude exits immediately twice (triggering backoff), then runs for >MIN_RUNTIME
- Steps: After the healthy run, stub claude exits immediately again
- Expected: Backoff restarts from the base value (30s), not from the escalated value

**TC-015: Healthy run uses standard 10s cooldown, not exponential**
- Precondition: Stub claude runs for >MIN_RUNTIME_SECONDS, then exits
- Steps: Observe cooldown value in wrapper output
- Expected: Wrapper waits 10s before restart (not exponential backoff). Output contains "Restarting in 10s"

---

## E. Unit Tests — Restart Log

**TC-016: Restart log entry appended on each restart**
- Precondition: No `restart-log.txt` exists
- Steps: Start boot script; stub claude exits; wrapper restarts once; place `.stop` file
- Expected: `restart-log.txt` exists with at least one entry

**TC-017: Restart log entry contains required fields**
- Precondition: None
- Steps: Trigger one restart cycle
- Expected: Each log entry contains: timestamp (ISO or local format), exit code, restart count, and runtime of previous session

**TC-018: Restart log is append-only across multiple restarts**
- Precondition: `restart-log.txt` already has 2 entries
- Steps: Start boot script; trigger one more restart
- Expected: File now has 3 entries; previous 2 entries unchanged

**TC-019: Restart log handles missing file gracefully**
- Precondition: `restart-log.txt` does not exist
- Steps: Trigger first restart
- Expected: File is created (not an error). Entry is written normally.

---

## F. Integration Tests

**TC-020: Full restart cycle — boot, exit, restart**
- Precondition: Clean temp directory with `.squidsquad/[role]/` structure; stub claude in PATH
- Steps: Run actual boot script template (with `{{ROLE}}` substituted); stub claude exits 0 after 5s; wrapper restarts; stub claude exits 0 again; place `.stop` file
- Expected: Claude invoked exactly twice. Restart log has 1 entry. Wrapper exits cleanly.

**TC-021: Stop file prevents restart (integration)**
- Precondition: `.stop` file created before boot script starts
- Steps: Run boot script; stub claude exits
- Expected: Claude invoked exactly once. Wrapper exits. Output contains "Stop file detected."

**TC-022: PID lock prevents double-start (integration)**
- Precondition: Start boot script instance A in background (with long-running stub claude)
- Steps: Attempt to start boot script instance B
- Expected: Instance B prints "Already running" and exits immediately. Instance A continues unaffected.

**TC-023: Double Ctrl+C breaks wrapper loop (bash)**
- Precondition: Boot script running with long-running stub claude
- Steps: Send SIGINT to wrapper process; wait 1s; send SIGINT again
- Expected: Wrapper exits. If first SIGINT only kills the claude child, second SIGINT kills the wrapper. (Exact behavior depends on trap implementation — verify whichever pattern is used.)
- Note: May require manual verification if signal timing is unreliable in CI

---

## G. Side Effect Regression Tests

**TC-024: Normal claude run — no wrapper interference**
- Precondition: Stub claude that runs for 30s, exits 0
- Steps: Run boot script; let stub claude complete; place `.stop` to prevent second iteration
- Expected: Claude receives correct args (`--dangerously-skip-permissions`, `--name`, `--append-system-prompt`, init message). Status bar reset to `idle|Initializing...` before launch. No unexpected env vars or modified behavior.

**TC-025: working-state.md resume works after restart**
- Precondition: `.squidsquad/[role]/working-state.md` contains an in-progress task
- Steps: Run boot script; stub claude exits (simulating context pressure); wrapper restarts; second stub claude exits; check that `working-state.md` was not modified by the wrapper
- Expected: `working-state.md` is untouched by wrapper logic — the file persists across restarts for the agent to read on next boot

**TC-026: .gitignore covers restart artifacts**
- Precondition: `.gitignore` updated per FEAT-250
- Steps: Check `.gitignore` patterns
- Expected: `.pid`, `.stop`, and `restart-log.txt` patterns are present. Running `git status` does not show these files as untracked after a restart cycle.

**TC-027: Status bar shows restarting state between sessions**
- Precondition: Stub claude exits after healthy run (>MIN_RUNTIME)
- Steps: After claude exits, read `current-state` before next claude launch
- Expected: `current-state` contains `restarting|Restarting in 10s...` (or similar). After next claude launch, `current-state` resets to `idle|Initializing...`

**TC-028: Status bar shows backoff state on fast crash**
- Precondition: Stub claude exits immediately (<MIN_RUNTIME)
- Steps: After fast exit, read `current-state`
- Expected: `current-state` contains `waiting|Restart backoff ([N]s)` with the appropriate backoff duration

**TC-029: Status bar shows error on max restarts**
- Precondition: Stub claude always exits immediately; MAX_RESTARTS reduced to 3 for test
- Steps: Let wrapper exhaust all restarts
- Expected: `current-state` contains `error|Max restarts reached`

---

## H. Smoke Tests (Manual)

**TC-030: Real agent context pressure restart**
- Steps: Launch a real agent with a low context threshold (e.g., 50%). Let it work until context pressure triggers exit.
- Verify: Agent saves working-state.md, commits, exits. Wrapper restarts. New session reads working-state.md and resumes.

**TC-031: Stop file stops real agent**
- Steps: While agent is running, create `.squidsquad/[role]/.stop`. Wait for agent to exit naturally (or trigger context pressure).
- Verify: Wrapper does not restart. Status bar shows stopped.

**TC-032: Double Ctrl+C stops real agent (interactive)**
- Steps: Launch agent in terminal. Press Ctrl+C once. Wait 2s. Press Ctrl+C again.
- Verify: Agent and wrapper both stop. No orphan processes.

**TC-033: PowerShell wrapper parity**
- Steps: Run the PowerShell boot script on Windows with stub claude. Trigger restart, stop file, and PID lock scenarios.
- Verify: Behavior matches bash wrapper for TC-020, TC-021, TC-022.

**TC-034: Boot script regeneration via compose.py**
- Steps: Run `python references/scripts/compose.py boot skill`. Inspect generated `.squidsquad/start-skill.sh`.
- Verify: Wrapper loop code is present. `{{ROLE}}` placeholders are substituted. Script is executable.
