# FEAT-PM-4709 Test Plan — Harness Phase 2: Event Bus + Agent Communication

## Test Cases

### TC-1: cycle_pre.py emits cycle-start event after writing cycle-input.json

- **Precondition**: Harness running and serving HTTP on a known port. `.squidsquad/.harness-port` written to the agent clone's `.squidsquad/` directory. A valid agent role (e.g. `skill`) configured.
- **Steps**:
  1. Run `python references/scripts/cycle_pre.py skill`
  2. Inspect the harness event log (console or GET /events if implemented)
- **Expected**: A `cycle-start` event appears with `event_type: "cycle-start"`, `role: "skill"`, a valid ISO timestamp, and `cycle_number` matching the current cycle count. Event emitted only AFTER `cycle-input.json` is written (not before).
- **Verification**: Query harness state: `curl http://localhost:<port>/events` (or inspect console output). Confirm event present with correct schema fields. Confirm `cycle-input.json` exists and is non-empty at event time.

---

### TC-2: cycle_post.py emits cycle-end event after commit/push

- **Precondition**: Harness running. `.squidsquad/.harness-port` present. A completed `cycle-output.json` exists for the role.
- **Steps**:
  1. Run `python references/scripts/cycle_post.py skill`
  2. Inspect the harness event log
- **Expected**: A `cycle-end` event appears with `event_type: "cycle-end"`, `role: "skill"`, valid timestamp, `cycle_number`, `cycle_type`, and `summary` in `payload`. Event emitted only AFTER commit and push complete.
- **Verification**: Inspect harness `/events` or console. Confirm event is after the git push step (check sequence against git log timestamp). Confirm `payload` contains `cycle_number`, `cycle_type`, and `summary`.

---

### TC-3: Harness /events endpoint receives and stores events

- **Precondition**: Harness running and serving HTTP. No prior events in the stream.
- **Steps**:
  1. POST a well-formed event to `http://localhost:<port>/events`:
     ```json
     {"event_type": "cycle-start", "role": "pm", "timestamp": "2026-05-01T18:00:00", "cycle_number": 1, "payload": {}}
     ```
  2. POST a second event with a different role.
  3. Retrieve the event stream (GET /events or inspect console state).
- **Expected**: Both events are stored and retrievable. Events are appended in order. Each stored event contains all schema fields: `event_type`, `role`, `timestamp`, `cycle_number`, `payload`.
- **Verification**: `curl -X POST http://localhost:<port>/events -H 'Content-Type: application/json' -d '...'` returns HTTP 200. Subsequent GET or console output shows both events in insertion order.

---

### TC-4: Harness console displays events in real-time

- **Precondition**: Harness running with console output visible. No prior events.
- **Steps**:
  1. Emit a `cycle-start` event from a mechanical script (or via direct POST).
  2. Emit a `phase-change` event.
  3. Emit a `cycle-end` event.
  4. Observe the harness console.
- **Expected**: Each event appears in the console as it arrives, in the format: `[HH:MM:SS] <role> <event_type> [<detail>]`. No delay beyond network round-trip. Events are not batched — each prints immediately on receipt.
- **Verification**: Observe console output timing matches event POST timing (within ~1 second). Format matches the documented pattern (e.g. `[18:32:55] skill cycle-start #862`).

---

### TC-5: AgentState updates from received events

- **Precondition**: Harness running. AgentState for role `skill` initialized (or absent — first event creates it).
- **Steps**:
  1. POST a `cycle-start` event for `skill` with `cycle_number: 862`.
  2. POST a `phase-change` event for `skill` with `payload: {"phase": "verifying"}`.
  3. POST a `cycle-end` event for `skill` with `cycle_number: 862`.
  4. Inspect AgentState for `skill` via harness state model.
- **Expected**:
  - After step 1: `current_cycle = 862`, `last_cycle_start` is populated.
  - After step 2: `current_phase = "verifying"`.
  - After step 3: `last_cycle_end` is populated, `last_cycle_type` reflects `cycle_type` from payload.
- **Verification**: Expose AgentState via a GET /agents endpoint (if implemented) or instrument the harness state object in a test fixture. Assert each field matches expected value after each POST.

---

### TC-6: Bounded event stream (does not exceed 1000 events)

- **Precondition**: Harness running. EventStream empty.
- **Steps**:
  1. POST 1001 distinct events to `/events` in sequence.
  2. Inspect the event stream length.
- **Expected**: Stream contains exactly 1000 events. The oldest event (event 1) is evicted. Event 1001 is the newest entry. No memory growth beyond the bounded deque capacity.
- **Verification**: After 1001 POSTs, query stream length (GET /events count or internal state assertion). Confirm len == 1000. Confirm the first event in the stream has `cycle_number` matching the 2nd posted event (oldest was evicted).

---

### TC-7: .harness-port written to all agent clone directories on startup

- **Precondition**: `.squidsquad/.local-config` exists and lists paths for at least 2 agent clone directories. Harness not yet started.
- **Steps**:
  1. Start the harness.
  2. Read `.squidsquad/.harness-port` in each listed clone's `.squidsquad/` directory.
- **Expected**: Each agent clone directory has a `.squidsquad/.harness-port` file containing the harness port number (integer, matches the port the harness is actually listening on). All files written before harness begins accepting connections (or within startup window).
- **Verification**: After harness starts, run: `for path in <clone-paths>; do cat "$path/.squidsquad/.harness-port"; done`. All outputs match the harness port. Confirm port matches `curl http://localhost:<port>/health` response.

---

### TC-8: event_bus.py no-ops silently when harness is down

- **Precondition**: `.squidsquad/.harness-port` exists but contains a port where no harness is running (harness stopped or wrong port).
- **Steps**:
  1. Call `event_bus.emit("cycle-start", "skill", {"cycle_number": 1})` directly (or via `cycle_pre.py`).
  2. Observe output and return value.
- **Expected**: No exception raised. No error printed to stdout or stderr. Function returns silently. The calling script continues normally.
- **Verification**: Run the emit call and capture stdout/stderr. Assert both are empty. Assert the script completes with exit code 0. Confirm agent cycle proceeds normally afterward.

---

### TC-9: event_bus.py no-ops when .harness-port file missing

- **Precondition**: `.squidsquad/.harness-port` does not exist in the agent clone's directory.
- **Steps**:
  1. Remove or rename `.squidsquad/.harness-port` if present.
  2. Call `event_bus.emit("cycle-start", "pm", {"cycle_number": 1})`.
  3. Observe output, return value, and any exceptions.
- **Expected**: No exception raised. No error output. Function returns silently without attempting any HTTP connection. Calling script proceeds normally.
- **Verification**: Capture stdout/stderr — both empty. Exit code 0. No HTTP attempt logged (confirm via network capture or mock). `cycle_pre.py` completes and writes `cycle-input.json` as normal.

---

### TC-10: 500ms timeout — never blocks agent cycle

- **Precondition**: Harness port exists but the server deliberately delays responses (simulated slow server, e.g. `nc -l <port>` without responding).
- **Steps**:
  1. Write `.squidsquad/.harness-port` pointing to the slow server port.
  2. Record start time.
  3. Call `event_bus.emit("cycle-start", "skill", {"cycle_number": 1})`.
  4. Record end time.
- **Expected**: The emit call completes (silently) within approximately 500ms (±100ms tolerance). No blocking beyond the timeout. No exception propagated to caller.
- **Verification**: `elapsed = end_time - start_time`. Assert `elapsed < 0.7` seconds. Assert no exception raised. The emit uses urllib with a 500ms connect+read timeout.

---

### TC-11: Existing cycle behavior unchanged (events are additive)

- **Precondition**: Harness is NOT running. `.squidsquad/.harness-port` is absent. A valid role setup exists.
- **Steps**:
  1. Run a complete cycle: `python references/scripts/cycle_pre.py pm`, simulate creative work, run `python references/scripts/cycle_post.py pm`.
  2. Verify all standard cycle outputs: `cycle-input.json` written, iteration log appended, git commit made, `cycle-output.json` processed.
- **Expected**: All pre-existing cycle behaviors function identically to Phase 1 behavior. No errors. No missing files. Git commit and push complete. Status bar updated. The absence of harness and event_bus has zero effect on cycle mechanics.
- **Verification**: Diff `cycle-input.json` and `cycle-output.json` schema against Phase 1 baseline. Check iteration log for new entry. Run `git log -1` to confirm commit. Confirm `cycle_pre.py` and `cycle_post.py` exit with code 0.

---

### TC-12: Full test suite regression

- **Precondition**: All Phase 2 changes merged. Test suite at `tests/run_tests.py`.
- **Steps**:
  1. Run `python tests/run_tests.py`.
  2. Observe results.
- **Expected**: All existing tests pass. No regressions introduced by event_bus.py additions to cycle_pre.py or cycle_post.py. New unit tests for event_bus.py (emit success, emit with harness down, emit with missing port file, timeout behavior) all pass.
- **Verification**: Exit code 0. Zero test failures. New tests for `event_bus.py` present in `tests/` and passing (e.g. `tests/test_event_bus.py`).

---

## Smoke Tests

- [ ] Start harness → confirm `.harness-port` written to all configured clone directories
- [ ] Run `cycle_pre.py skill` with harness running → confirm `cycle-start` appears in harness console within 1 second
- [ ] Run `cycle_post.py skill` with harness running → confirm `cycle-end` appears in harness console
- [ ] Kill harness → run `cycle_pre.py pm` → confirm cycle completes without error (no-op path)
- [ ] Delete `.harness-port` → run `event_bus.emit(...)` directly → confirm silent no-op
- [ ] POST 1001 events → confirm stream length is capped at 1000
- [ ] Confirm `python tests/run_tests.py` exits 0 after all changes

---

## Regression Risks

- **cycle_pre.py / cycle_post.py import errors**: If `event_bus.py` is missing or has a syntax error and the import is not wrapped in `try/except`, mechanical scripts fail — breaking all agent cycles. Verify import is guarded.
- **Timeout misconfiguration**: If timeout is set in seconds instead of milliseconds (e.g. `timeout=500` vs `timeout=0.5` in urllib), the 500ms guarantee is violated and agents stall for 500 seconds. Verify the unit.
- **Port file written to wrong path**: If `.harness-port` is written to the project root rather than each clone's `.squidsquad/` directory, event_bus.py won't find it. Verify path resolution uses `.local-config` clone paths.
- **Thread safety gap**: If the FastAPI `/events` handler and the EventStream deque share state without a lock or asyncio queue, concurrent events may corrupt the deque or miss updates in the console. Verify thread-safe access.
- **Phase 1 regression**: Harness HTTP server from Phase 1 must still serve existing endpoints correctly after Phase 2 `/events` endpoint is added. Run Phase 1 smoke tests against the updated harness.
- **event_bus.py not deployed to clone directories**: If the file lives only in the main repo and not in agent clone directories (clone isolation architecture), mechanical scripts in clones will silently skip emission even with harness running. Verify deployment.
- **AgentState not initialized for first event**: If the harness expects `AgentState` to pre-exist before updating it from events, the first `cycle-start` for a new role may raise a KeyError. Verify upsert (create if not exists) behavior.

---

## Comprehension Questions

### CQ-1: Port discovery path

- **Files**: `event_bus.py`, harness startup code, `.squidsquad/.local-config`
- **Question**: Where does `event_bus.py` look for the `.harness-port` file, and how does the harness know which directories to write it to at startup?
- **Expected**: `event_bus.py` reads from its own clone's `.squidsquad/.harness-port` (relative to the script's clone root, not a global path). The harness reads `.squidsquad/.local-config` for all agent clone paths and writes `.squidsquad/.harness-port` into each clone's `.squidsquad/` directory at startup.

### CQ-2: Silent failure contract

- **Files**: `event_bus.py`
- **Question**: List all conditions under which `event_bus.emit()` exits silently without raising an exception, and what mechanism ensures this?
- **Expected**: (1) `.harness-port` file missing — checked before any network call, returns early. (2) HTTP POST fails for any reason (connection refused, network error, non-200 response) — all exceptions caught by a top-level `except Exception`. (3) Timeout exceeded (500ms) — caught by the same handler. The mechanism is a broad `try/except Exception` wrapping the entire emit body, with no re-raise.

### CQ-3: Event emission ordering guarantee

- **Files**: `cycle_pre.py`, `cycle_post.py`, context document
- **Question**: At what point in `cycle_pre.py` is the `cycle-start` event emitted relative to writing `cycle-input.json`, and why does this ordering matter?
- **Expected**: The `cycle-start` event is emitted AFTER `cycle-input.json` is written. This ordering ensures that if the harness or a downstream consumer reads `cycle-input.json` upon receiving the event, the file is guaranteed to exist and be populated. Emitting before the write would create a race condition where the harness receives the event but the file is not yet available.
