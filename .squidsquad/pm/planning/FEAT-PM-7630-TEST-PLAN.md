# FEAT-PM-7630 Test Plan — Event-Driven Agent Architecture

## Overview

This test plan covers the 4-phase EPIC that replaces SquidSquad's cycle-based polling model with a pure event-driven architecture. Phases are tested in dependency order. Phase 1.5 prerequisites gate all Phase 2 testing. Phase 3 template migration gates Phase 4 validation.

**Scope**: harness.py event infrastructure, Monitor tool wake mechanism, event closure API, template migration across all roles, regression of cycle model fallback, race condition mitigations.

**Zero-gap gate**: Any TC failure sends the work back to dev. No "noted for follow-up" exceptions.

---

## Prerequisites — Phase 1.5 Infrastructure

### TC-P1: Event Bus Disk Persistence Survives Harness Restart

- **Precondition**: Harness running with `event-driven: yes`. At least one event emitted and stored (e.g., `scan-due` for pm role). Event is visible via `GET /events`.
- **Steps**:
  1. Record the event ID from `GET /events`.
  2. Hard-kill the harness process (`taskkill /F /PID <harness_pid>` on Windows, `kill -9` on Unix).
  3. Restart harness: `python references/scripts/harness.py`.
  4. Wait for harness to finish `deferred_init`.
  5. Query `GET /events` again.
- **Expected**: The previously stored event is still present in the event list with the same ID and payload. No data loss from the kill-and-restart.
- **Verification**:
  ```bash
  # Before restart: capture event ID
  curl -s http://localhost:<PORT>/events | python -c "import sys,json; evts=json.load(sys.stdin); print(evts[0]['id'])"
  # After restart: verify same ID present
  curl -s http://localhost:<PORT>/events | python -c "import sys,json; evts=json.load(sys.stdin); ids=[e['id'] for e in evts]; print('PASS' if '<captured_id>' in ids else 'FAIL')"
  ```

---

### TC-P2: Clone Event Bus Discovery Works for Sibling Directories

- **Precondition**: Primary repo at `D:\Dev\Dev\SquidSquad`. A clone exists as a sibling at `D:\Dev\Dev\SquidSquad-skill` (or equivalent sibling path). Harness running in the primary repo. Port file distributed to the clone by `deferred_init`.
- **Steps**:
  1. Verify harness has distributed the `.harness-port` file into the clone's directory (should happen during `deferred_init`).
  2. From within the clone directory, run `event_bus_reader.py` `_discover_port` directly (or via a short test script):
     ```python
     import sys; sys.path.insert(0, 'references/scripts')
     from event_bus_reader import EventBusReader
     r = EventBusReader(role='skill')
     print(r._discover_port())
     ```
  3. Query `GET /events` using the discovered port.
- **Expected**: Port is discovered (non-None value returned). `GET /events` returns a valid response (200 OK, JSON list). Agent in clone can receive events without returning an empty list.
- **Verification**:
  ```bash
  # From clone directory
  python -c "
  import sys; sys.path.insert(0, 'references/scripts')
  from event_bus_reader import EventBusReader
  r = EventBusReader(role='skill')
  port = r._discover_port()
  print('Port discovered:', port)
  assert port is not None, 'FAIL: port not found for sibling clone'
  print('PASS')
  "
  ```
- **Regression signal**: If `_discover_port` returns `None`, the parent-walk fix for sibling clones did not land correctly.

---

### TC-P3: Per-Role In-Flight Event Queue Prevents Double-Dispatch

- **Precondition**: Harness running with `event-driven: yes`. One role (`pm`) has an event dispatched but not yet closed (simulate by pausing the agent or having it not respond).
- **Steps**:
  1. Emit an event to the `pm` role and confirm it is in the in-flight queue (visible in harness state, `in_flight_events["pm"]` is set).
  2. Attempt to emit a second event to the same `pm` role via harness internal logic (trigger the condition that would normally emit another event, e.g., a second `scan-due`).
  3. Inspect the harness event queue and the event bus.
- **Expected**: The second event is NOT dispatched while the first is unclosed. Harness queues it internally or skips emission. Only one event per role is in-flight at any time.
- **Verification**:
  ```bash
  # Inspect harness state file
  python -c "
  import json
  state = json.load(open('.squidsquad/.harness-state.json'))
  in_flight = state.get('in_flight_events', {})
  print('In-flight events:', in_flight)
  # Manually verify only one event per role in the bus
  "
  # Confirm event bus does not contain two open events for the same role
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  pm_evts = [e for e in evts if e.get('role') == 'pm' and e.get('status') == 'dispatched']
  print('PM in-flight count:', len(pm_evts))
  print('PASS' if len(pm_evts) <= 1 else 'FAIL: double dispatch detected')
  "
  ```

---

### TC-P4: Harness Thread Safety Under Concurrent Event and Health Polling

- **Precondition**: Harness running. Multiple roles active. Health polling thread running at 5-second interval. Event receiver endpoint active.
- **Steps**:
  1. Send 20 rapid `POST /events` requests concurrently (use a script with `concurrent.futures.ThreadPoolExecutor`).
  2. Simultaneously, trigger 5 health poll calls to `GET /agents/{role}/health` from a separate thread.
  3. Let all calls complete.
  4. Check harness process for exceptions, panics, or corrupted state.
- **Expected**: No race conditions, no `RuntimeError` about dictionary size change during iteration, no corrupted `AgentState` fields. All 20 events stored correctly. Health responses return valid data.
- **Verification**:
  ```bash
  python -c "
  import concurrent.futures, requests, time
  BASE = 'http://localhost:<PORT>'
  def post_event(i):
      return requests.post(f'{BASE}/events', json={'event_type': 'test', 'role': 'pm', 'payload': {'seq': i}})
  def poll_health():
      return requests.get(f'{BASE}/agents/pm/health')
  with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
      futs = [ex.submit(post_event, i) for i in range(20)]
      futs += [ex.submit(poll_health) for _ in range(5)]
      results = [f.result().status_code for f in futs]
  fails = [r for r in results if r >= 500]
  print('PASS' if not fails else f'FAIL: {len(fails)} 5xx errors')
  "
  # Inspect harness logs for RuntimeError or lock contention errors
  ```

---

## Phase 2 — Event Wake and Closure

### TC-2-01: Happy Path — Full Event Lifecycle

- **Precondition**: `event-driven: yes` in config.md. Claude Code upgraded to v2.1.98+. Monitor tool validated. Harness running. PM agent running with event-driven template (no `/loop`). Agent is idle, Monitor tool watching event bus.
- **Steps**:
  1. Trigger an event emission by harness (e.g., wait 10 minutes for `scan-due`, or manually emit a `work-available` event via `POST /events`).
  2. Observe that Monitor tool detects the event (agent session wakes — visible in terminal or agent log).
  3. Agent reads event context from the event payload.
  4. Agent performs creative work (e.g., improvement scan for `scan-due`).
  5. Agent posts `POST /events/{event_id}/complete` with a valid result payload.
  6. Harness processes the closure callback (executes status transitions, commits, pushes).
  7. Harness marks the event as closed.
- **Expected**: Event transitions from `dispatched` → `closed`. Harness executes all side effects specified in the closure payload (transitions, comments, git commit). Agent returns to idle state. `in_flight_events["pm"]` is cleared.
- **Verification**:
  ```bash
  # Check event state after closure
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  target = next((e for e in evts if e['id'] == '<event_id>'), None)
  print('Event status:', target['status'] if target else 'NOT FOUND')
  print('PASS' if target and target['status'] == 'closed' else 'FAIL')
  "
  # Verify git commit exists
  git log --oneline -3
  # Verify no in-flight events remain
  python -c "
  import json
  s = json.load(open('.squidsquad/.harness-state.json'))
  print('In-flight:', s.get('in_flight_events', {}))
  "
  ```

---

### TC-2-02: Event Closure API Returns Structured Result

- **Precondition**: Harness running with `event-driven: yes`. A `work-available` event has been dispatched to the `pm` role (event_id known).
- **Steps**:
  1. POST to `POST /events/{event_id}/complete` with a full structured payload:
     ```json
     {
       "status": "completed",
       "status_transitions": [{"number": 123, "from": "in-progress", "to": "pending-test"}],
       "tracker_comments": [{"number": 123, "message": "Work done. Status -> Pending Test."}],
       "commit_message": "pm: #123 — task complete via event closure",
       "summary": "Completed improvement scan. Filed 1 task.",
       "working_state_update": "# Working State\n\n- **Task**: none\n"
     }
     ```
  2. Check harness response (200 OK with event record, or appropriate error).
  3. Verify each field in the payload was acted upon by the harness.
- **Expected**:
  - Response: 200 OK with the closed event record (including `status: "closed"`).
  - Tracker transition `#123 in-progress → pending-test` executed via `tracker.py`.
  - Tracker comment posted on `#123`.
  - Git commit created with the provided commit message.
  - `working-state.md` updated with the provided content.
  - All role-specific extras in the payload schema (code_commit, pr_actions, vault_writes, etc.) processed without error if present.
- **Verification**:
  ```bash
  # Check tracker transition
  python references/scripts/tracker.py get-labels 123
  # Check comment posted
  gh issue view 123 --json comments --jq '.comments[-1].body'
  # Check git commit
  git log --oneline -1
  # Check working state
  cat .squidsquad/pm/working-state.md
  ```

---

### TC-2-03: Unclosed Event Detected After Timeout — Harness Diagnoses and Acts

- **Precondition**: `event-driven: yes`. A `work-available` event has been dispatched to `pm`. Agent does NOT post a closure (simulate: block agent or don't respond). Short-task timeout configured (e.g., 5 minutes for `scan-due` type).
- **Steps**:
  1. Dispatch a `scan-due` event to pm.
  2. Wait for the configured timeout (5 minutes for short tasks, or set a test timeout shorter if harness supports it).
  3. Observe harness behavior at timeout.
- **Expected**: Harness detects the unclosed event. Harness logs a diagnostic (event type, role, elapsed time). Harness takes one of: re-emits the event (if agent is alive), marks it `abandoned` (if agent is dead), or alerts the human (if ambiguous). No silent hang — the system self-diagnoses.
- **Verification**:
  ```bash
  # Check harness logs for timeout detection
  grep "event-timeout\|unclosed\|abandoned" .squidsquad/harness.log 2>/dev/null || \
  grep -i "timeout" <(curl -s http://localhost:<PORT>/events)
  # Check event status
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  t = next((e for e in evts if e['id'] == '<event_id>'), None)
  print('Status:', t['status'] if t else 'NOT FOUND')
  print('PASS' if t and t['status'] in ('abandoned', 'reemitted', 'timed-out') else 'FAIL')
  "
  ```

---

### TC-2-04: Agent Crash Mid-Event — Harness Detects via PID and Re-Emits

- **Precondition**: `event-driven: yes`. Agent running with a dispatched event in-flight. Agent PID tracked in `.harness-state.json`.
- **Steps**:
  1. Dispatch a `work-available` event to the `pm` role. Confirm it is in-flight.
  2. Hard-kill the agent process (`taskkill /F /PID <claude_pid>` on Windows).
  3. Wait one health poll cycle (5 seconds).
  4. Observe harness behavior.
- **Expected**: Harness detects agent death via PID check within 5 seconds. Harness records the crash. Harness re-emits the in-flight event (since agent never posted closure). `intent` is set to `restarting` (auto-reboot). New agent instance starts and receives the re-emitted event.
- **Verification**:
  ```bash
  # Verify harness detected death
  grep "agent.*dead\|PID.*not alive\|crash" <harness_log> || \
  curl -s http://localhost:<PORT>/agents/pm | python -c "import sys,json; a=json.load(sys.stdin); print('Health:', a.get('health_status'))"
  # Verify event was re-emitted (new event with same payload, or status = 'reemitted')
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  reemitted = [e for e in evts if e.get('payload', {}).get('original_event_id') == '<event_id>' or e.get('status') == 'reemitted']
  print('Re-emitted events:', len(reemitted))
  print('PASS' if reemitted else 'FAIL')
  "
  ```

---

### TC-2-05: Harness Crash During Closure Processing — Event Replays Without Duplicates

- **Precondition**: `event-driven: yes`. Agent has just posted `POST /events/{event_id}/complete`. Harness is mid-processing (simulate by hard-killing harness immediately after receiving the POST but before persisting `status: closed`).
- **Steps**:
  1. In a test harness or via timing, hard-kill the harness immediately after it receives the closure POST (before side effects complete).
  2. Restart the harness.
  3. Observe what harness does with the in-flight event on restart.
- **Expected**: Harness replays the unclosed event. Side effects (tracker transitions, git commit) execute exactly once — either because they are idempotent (at-least-once model) or because the event was marked closed before execution (at-most-once model). No duplicate tracker comments. No duplicate git commits.
- **Verification**:
  ```bash
  # Check for duplicate tracker comments
  gh issue view 123 --json comments --jq '[.comments[] | select(.body | contains("event closure"))] | length'
  # Expected: 1 (not 2)
  # Check git log for duplicate commits
  git log --oneline | grep "<commit_message>" | wc -l
  # Expected: 1
  # Check event status after restart
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  t = next((e for e in evts if e['id'] == '<event_id>'), None)
  print('Status:', t['status'] if t else 'NOT FOUND')
  "
  ```

---

### TC-2-06: scan-due Event Emitted After 10-Minute Idle with Issue Gate

- **Precondition**: `event-driven: yes`. `scan-idle-timeout: 10` in config. PM role has completed its last event more than 10 minutes ago (set `last_event_completed["pm"]` to a past timestamp in harness state, or simply wait). No open issues assigned to PM role.
- **Steps**:
  1. Verify no open issues exist for pm: `python references/scripts/tracker.py list-issues pm --status open` → empty.
  2. Confirm `last_event_completed["pm"]` is older than 10 minutes.
  3. Wait for the harness idle-check thread to fire (or trigger manually if harness has a test endpoint).
  4. Inspect the event bus.
- **Expected**: Harness emits a `scan-due` event to the pm role. Event appears in `GET /events` with `event_type: "scan-due"` and `role: "pm"`.
- **Variation (issue gate active)**: Repeat with one open issue assigned to pm. Expected: harness does NOT emit `scan-due`. Issue gate suppressed the scan.
- **Verification**:
  ```bash
  # Confirm scan-due event emitted
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  scan = [e for e in evts if e.get('event_type') == 'scan-due' and e.get('role') == 'pm']
  print('scan-due events:', len(scan))
  print('PASS' if scan else 'FAIL')
  "
  # Issue gate test: create a test issue, re-run, confirm NO new scan-due
  python references/scripts/tracker.py create-issue --title "Test gate issue" --body "test" --role pm --severity low --reporter pm-lead
  # Wait for next idle-check interval
  # Confirm no additional scan-due events were emitted
  ```

---

### TC-2-07: stop-requested Event — Agent Detects, Checkpoints, Exits Cleanly

- **Precondition**: `event-driven: yes`. Agent running (idle or mid-work). Monitor tool watching event bus.
- **Steps**:
  1. Trigger graceful stop via `python references/scripts/start_team.py --stop pm` (or equivalent harness API call).
  2. Harness emits `stop-requested` event on the event bus.
  3. Monitor tool detects the event.
  4. Agent reads the event.
  5. Agent checkpoints `working-state.md`.
  6. Agent exits.
- **Expected**: Agent checkpoint visible in `working-state.md`. Agent process exits (PID no longer alive). Harness transitions agent `intent` to `stopped`. No orphaned Claude Code process.
- **Verification**:
  ```bash
  # Check working state was updated (non-empty checkpoint)
  cat .squidsquad/pm/working-state.md
  # Check agent PID is dead
  python -c "
  import json, os
  state = json.load(open('.squidsquad/.harness-state.json'))
  pm = state.get('agents', {}).get('pm', {})
  pid = pm.get('claude_pid')
  try:
      os.kill(pid, 0)
      print('FAIL: process still alive')
  except ProcessLookupError:
      print('PASS: process exited')
  "
  # Check harness intent
  curl -s http://localhost:<PORT>/agents/pm | python -c "import sys,json; a=json.load(sys.stdin); print('Intent:', a.get('intent')); print('PASS' if a.get('intent') == 'stopped' else 'FAIL')"
  ```

---

### TC-2-08: Terminal Window Closed on Clean Stop (Windows)

- **Precondition**: Windows platform. `event-driven: yes`. Agent spawned via `boot_remote.py` (Windows Terminal or cmd). `terminal_pid` tracked in `.harness-state.json`.
- **Steps**:
  1. Boot a pm agent and confirm `terminal_pid` is populated in `.harness-state.json`.
  2. Issue a graceful stop: `python references/scripts/start_team.py --stop pm`.
  3. Wait for agent to exit cleanly (TC-2-07 passes).
  4. Observe terminal window.
- **Expected**: Terminal window closes (not just the Claude process — the terminal window itself). `terminal_pid` process is no longer alive. No zombie terminal windows remaining.
- **Verification**:
  ```bash
  python -c "
  import json, os, sys
  state = json.load(open('.squidsquad/.harness-state.json'))
  pm = state.get('agents', {}).get('pm', {})
  term_pid = pm.get('terminal_pid')
  if term_pid is None:
      print('FAIL: terminal_pid not tracked')
      sys.exit(1)
  try:
      os.kill(term_pid, 0)
      print('FAIL: terminal process still alive, PID', term_pid)
  except (ProcessLookupError, PermissionError):
      print('PASS: terminal window closed, PID', term_pid, 'gone')
  "
  ```
- **Note**: On Windows, `PermissionError` from `os.kill` can also mean the process is not owned by current user but still alive. Use `tasklist /FI "PID eq <terminal_pid>"` as a secondary check if needed.

---

## Phase 3 — Template Migration

### TC-3-01: Agents Boot Without /loop Command

- **Precondition**: `event-driven: yes`. All templates migrated (Phase 3 complete). `compose.py deploy-all` run successfully. Fresh agent session started (no prior context).
- **Steps**:
  1. Boot a pm agent via `python references/scripts/start_team.py --role pm`.
  2. Observe the agent's startup behavior in its terminal.
  3. Wait 30 seconds for any `/loop` invocation that might occur.
- **Expected**: Agent boots and enters idle state without invoking `/loop`. No `/loop` command appears in the session. Agent is awake and waiting for events via Monitor tool. Terminal shows event-driven orientation message (or equivalent).
- **Verification**:
  - Review agent terminal output: no `/loop 30m` or `/loop` invocation present.
  - Check agent's startup prompt in `thin_launcher.py` output — confirm it no longer contains "Boot. Begin your first Ralph Loop cycle now."
  - Agent is alive (PID in `.harness-state.json`) and health status is `running`.
  ```bash
  curl -s http://localhost:<PORT>/agents/pm | python -c "import sys,json; a=json.load(sys.stdin); print('Health:', a.get('health_status')); print('Intent:', a.get('intent'))"
  ```

---

### TC-3-02: Agent Templates Contain No Cycle Step Prose

- **Precondition**: Phase 3 template migration complete. `compose.py deploy-all` run. All `.squidsquad/*/CLAUDE.md` files regenerated.
- **Steps**:
  1. Search composed CLAUDE.md files for cycle-specific prose patterns.
  2. Search source template files in `references/roles/` and `references/sub-skills/` for removed patterns.
- **Expected**: None of the following patterns appear in composed output for any role:
  - `/loop` invocation
  - `cycle_pre.py` references
  - `cycle_post.py` references
  - `cycle-input.json` read instructions
  - `cycle-output.json` write instructions
  - Ralph Loop step numbers (Step 1, Step 2, etc. in the old cycle prose format)
  - `iter-N.md` iteration log references
  - `current-state` file write instructions (cycle-based)
- **Verification**:
  ```bash
  # Check composed CLAUDE.md files for banned patterns
  for pattern in "/loop" "cycle_pre" "cycle_post" "cycle-input.json" "cycle-output.json" "iter-N.md"; do
    matches=$(grep -rl "$pattern" .squidsquad/*/CLAUDE.md 2>/dev/null)
    if [ -n "$matches" ]; then
      echo "FAIL: '$pattern' found in: $matches"
    else
      echo "PASS: '$pattern' not found in composed output"
    fi
  done
  ```

---

### TC-3-03: compose deploy-all Produces Valid CLAUDE.md Without Cycle Sub-Skills

- **Precondition**: Phase 3 source changes complete (cycle-related includes removed from all includes.yml files). New `event-driven-workflow.md` sub-skill created.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`.
  2. Check exit code (must be 0).
  3. Verify each role's composed CLAUDE.md exists and is non-empty.
  4. Verify removed includes are absent from composed files.
  5. Verify `event-driven-workflow.md` content appears in composed files.
- **Expected**: `compose.py deploy-all` exits 0. All role CLAUDE.md files updated. None contain `common/cycle-runner`, `common/context-pressure`, `common/self-restart`, or `common/interval-sync` content (these sub-skills removed). All contain `event-driven-workflow` sub-skill content.
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all
  echo "compose exit code: $?"

  # Verify event-driven-workflow content present
  for role in pm qa dev dm skill; do
    if grep -q "event-driven" .squidsquad/$role/CLAUDE.md 2>/dev/null; then
      echo "PASS: $role has event-driven-workflow"
    else
      echo "FAIL: $role missing event-driven-workflow"
    fi
  done

  # Verify removed sub-skills absent
  for removed in "context-pressure.md" "self-restart.md" "interval-sync.md" "cycle-runner.md"; do
    if grep -q "$removed" .squidsquad/pm/CLAUDE.md 2>/dev/null; then
      echo "FAIL: $removed still present in composed output"
    else
      echo "PASS: $removed absent from composed output"
    fi
  done
  ```

---

## Regression Tests

### TC-R01: event-driven: no Preserves Full Cycle Model Unchanged

- **Precondition**: `event-driven: no` in config.md (default). Code changes for Phase 2 are present but gated.
- **Steps**:
  1. Boot a pm agent normally.
  2. Verify it invokes `/loop 30m`.
  3. Wait for one complete cycle (cycle_pre → creative → cycle_post).
  4. Verify cycle-input.json is written.
  5. Verify cycle-output.json is consumed by cycle_post.
  6. Verify iteration log (iter-N.md or equivalent) written.
  7. Verify git commit produced.
- **Expected**: Full existing cycle model functions without degradation. All cycle_pre/cycle_post operations complete. No event-driven behavior activates. No errors related to missing event-driven infrastructure.
- **Verification**:
  ```bash
  python references/scripts/config.py get event-driven
  # Expected: no
  ls -la .squidsquad/pm/cycle-input.json
  ls -la .squidsquad/pm/cycle-output.json
  ls -la .squidsquad/pm/iterations/
  git log --oneline -1  # should show cycle commit
  ```

---

### TC-R02: Mixed-Mode Warning on Harness Startup

- **Precondition**: `event-driven: yes` for pm role but `event-driven: no` (or not set) for skill role. Harness starting up.
- **Steps**:
  1. Set config so pm is event-driven and skill is cycle-based.
  2. Start harness: `python references/scripts/harness.py`.
  3. Check harness startup output and logs.
- **Expected**: Harness prints a visible warning that roles are running in mixed mode (some event-driven, some cycle-based). Warning identifies which roles are in which mode. Harness still starts (does not abort). Both roles function in their respective modes.
- **Verification**:
  ```bash
  python references/scripts/harness.py 2>&1 | grep -i "mixed\|warning\|event-driven.*no\|cycle.*event"
  # At least one warning line expected
  ```

---

### TC-R03: Existing Tracker Transitions Work Through Closure API

- **Precondition**: `event-driven: yes`. A real GitHub Issue exists at a known status (e.g., `#42` at `in-progress`). Closure API implemented.
- **Steps**:
  1. POST to `POST /events/{event_id}/complete` with a status transition in the payload:
     ```json
     {
       "status": "completed",
       "status_transitions": [{"number": 42, "from": "in-progress", "to": "pending-test"}],
       "tracker_comments": [{"number": 42, "message": "Verified via event closure API. Status -> Pending Test."}],
       "commit_message": "pm: regression TC-R03 — closure API transition test",
       "summary": "Regression test for tracker transitions via closure API"
     }
     ```
  2. Harness processes the closure and calls `tracker.py transition`.
  3. Verify the transition succeeded.
- **Expected**: Issue `#42` transitions from `in-progress` to `pending-test` exactly as if `tracker.py transition 42 in-progress pending-test --role pm-lead` was called directly. Comment posted. No difference in behavior from direct tracker.py calls.
- **Verification**:
  ```bash
  python references/scripts/tracker.py get-labels 42
  # Expected: status:pending-test label present
  gh issue view 42 --json labels --jq '[.labels[].name] | sort'
  gh issue view 42 --json comments --jq '.comments[-1].body'
  ```

---

## Race Condition Tests

### TC-RC01: Startup Race — Agents Don't POST Before Server Ready

- **Precondition**: `event-driven: yes`. Fresh harness start. Agents configured to auto-boot via `deferred_init`.
- **Steps**:
  1. Start harness.
  2. Monitor network connections for any `POST /events/{id}/complete` or `POST /events` calls made before the harness server is fully accepting connections (before `yield` in the lifespan).
  3. If any such early POSTs occur, capture their response.
- **Expected**: No agent POST attempts before server is ready. Either: (a) harness delays agent spawn until server is accepting (preferred), or (b) agent closure POST includes retry logic (3 attempts with backoff) that handles 503/connection-refused gracefully. No events lost due to startup timing.
- **Verification**:
  ```bash
  # Time the harness startup and first agent activity
  python -c "
  import subprocess, time, requests
  t0 = time.time()
  proc = subprocess.Popen(['python', 'references/scripts/harness.py'])
  # Poll for server readiness
  for i in range(30):
      try:
          r = requests.get('http://localhost:<PORT>/health', timeout=1)
          if r.status_code == 200:
              print(f'Server ready at t+{time.time()-t0:.2f}s')
              break
      except Exception:
          time.sleep(0.5)
  "
  # Check harness logs: look for agent boot times vs. server ready time
  grep "server.*ready\|deferred_init\|agent.*spawned" <harness_log>
  ```

---

### TC-RC02: Event ID Uniqueness Under High Volume

- **Precondition**: Harness running. Event emission working.
- **Steps**:
  1. Emit 1,000 events rapidly via concurrent `POST /events` calls.
  2. Retrieve all events via `GET /events`.
  3. Check for duplicate event IDs.
- **Expected**: All 1,000 events have unique IDs. No collisions. The unified ID generation scheme (one scheme, sufficient entropy — at least 12 hex chars or equivalent) produces no duplicates in this volume.
- **Verification**:
  ```bash
  python -c "
  import concurrent.futures, requests, json
  BASE = 'http://localhost:<PORT>'
  def emit(i):
      r = requests.post(f'{BASE}/events', json={'event_type': 'test', 'role': 'pm', 'payload': {'seq': i}})
      return r.json().get('id')
  with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
      ids = list(ex.map(emit, range(1000)))
  ids = [i for i in ids if i]
  unique = len(set(ids))
  print(f'Emitted: {len(ids)}, Unique IDs: {unique}')
  print('PASS' if unique == len(ids) else f'FAIL: {len(ids) - unique} collisions')
  "
  ```

---

### TC-RC03: Shutdown — In-Flight Events Marked Abandoned

- **Precondition**: `event-driven: yes`. At least one event is in-flight (dispatched, not closed) for the pm role.
- **Steps**:
  1. Dispatch an event to pm. Confirm it is in-flight (agent does not close it).
  2. Trigger harness shutdown (Ctrl+C or `start_team.py --stop --all`).
  3. Wait for harness to fully shut down.
  4. Restart harness.
  5. Inspect event status in the restored event bus.
- **Expected**: On shutdown, harness marks all in-flight events as `abandoned` before exiting. On restart, harness does NOT re-emit `abandoned` events automatically (they are stale). Human or harness logic must decide whether to replay abandoned events. No silent event loss — the abandoned status is visible and queryable.
- **Verification**:
  ```bash
  # After restart
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  abandoned = [e for e in evts if e.get('status') == 'abandoned']
  print('Abandoned events:', len(abandoned))
  print('IDs:', [e['id'] for e in abandoned])
  print('PASS' if abandoned else 'FAIL: no abandoned events found — may indicate data loss')
  "
  ```

---

## Smoke Tests

Quick go/no-go checks before full TC execution. All must pass before investing in deep TC runs.

- [ ] Harness starts without error: `python references/scripts/harness.py` exits cleanly or runs stably with no traceback.
- [ ] `GET /health` returns 200 OK within 2 seconds of harness start.
- [ ] `GET /events` returns 200 OK with a JSON list (empty list is acceptable).
- [ ] `POST /events` with a minimal payload returns 200 OK and a valid event ID.
- [ ] `.harness-state.json` exists and contains `in_flight_events` and `last_event_completed` fields after harness starts.
- [ ] `compose.py deploy-all` exits 0 with `event-driven: yes` config.
- [ ] Composed `pm/CLAUDE.md` does not contain `/loop` after deploy-all.
- [ ] Composed `pm/CLAUDE.md` does contain `event-driven-workflow` content after deploy-all.
- [ ] `event_bus_reader.py` returns non-empty list when called from within a sibling clone (requires TC-P2 environment).
- [ ] `start_team.py --stop pm` completes within 30 seconds with no hanging process.

---

## Comprehension Questions (CQ)

These questions verify that a fresh agent, given only the migrated template files, can correctly derive the event-driven workflow. No prior context or conversation memory permitted. QA spawns a fresh subagent, provides only the listed files, and scores answers against the expected derivations.

### CQ-1: How Does an Agent Wait for Work in Event-Driven Mode?

- **Files to provide**:
  - `.squidsquad/pm/CLAUDE.md` (composed output, post-migration)
  - `references/sub-skills/common/event-driven-workflow.md`
  - `references/sub-skills/common/agent-lifecycle.md` (rewritten)
- **Question to ask fresh agent**: "You are a PM agent that has just booted. There is no `/loop` command and no cycle_pre.py to run. How do you wait for work to arrive? What tool or mechanism keeps you active between work items?"
- **Expected derivation**: Agent must answer that the Monitor tool (Claude Code v2.1.98+) watches the event bus for incoming events. The agent does not poll manually, does not sleep, and does not invoke `/loop`. The Monitor tool wakes the agent when an event with the agent's role arrives. The agent sits in an idle/persistent session state between events.
- **Pass criteria**: Answer mentions Monitor tool, event bus watching, and passive idle state. Answer must NOT mention `/loop`, `cycle_pre`, or manual polling.

---

### CQ-2: What Must an Agent Do After Completing Event Work?

- **Files to provide**:
  - `.squidsquad/pm/CLAUDE.md` (composed output, post-migration)
  - `references/sub-skills/common/event-driven-workflow.md`
- **Question to ask fresh agent**: "You have just finished the creative work for an event (e.g., an improvement scan triggered by a scan-due event). The work is done. What must you do next? What happens if you skip this step?"
- **Expected derivation**: Agent must answer that it is required to call `POST /events/{event_id}/complete` with a structured result payload (including status transitions, tracker comments, commit message, summary). Skipping this call leaves the event unclosed, which the harness detects as a diagnostic signal — the harness may diagnose a crash, re-emit the event, or alert the human. The harness (not the agent) executes git commits, pushes, and tracker transitions after receiving the closure.
- **Pass criteria**: Answer mentions the POST closure call with event_id, structured payload, and consequence of not closing. Must NOT say the agent commits or pushes directly.

---

### CQ-3: What Happens If a stop-requested Event Arrives?

- **Files to provide**:
  - `.squidsquad/pm/CLAUDE.md` (composed output, post-migration)
  - `references/sub-skills/common/event-driven-workflow.md`
  - `references/sub-skills/common/agent-lifecycle.md` (rewritten)
- **Question to ask fresh agent**: "While you are idle (or mid-work), a stop-requested event arrives on the event bus and the Monitor tool wakes you with it. What do you do? In what order?"
- **Expected derivation**: Agent must answer: (1) checkpoint current working state to `working-state.md`, (2) if mid-event, attempt to post a partial closure or note the interruption, (3) exit the session cleanly. Agent must NOT attempt to ignore the event, defer it, or continue working. The stop-requested event is the unified stop channel — same Monitor tool that delivers work events also delivers the stop signal.
- **Pass criteria**: Answer includes checkpointing working state and clean exit. Answer must NOT say the agent polls a sentinel file or waits for `/loop` to end — the stop arrives via event bus, not via cycle end.

---

## Regression Risks

- **cycle_pre/cycle_post removed from templates but left in codebase**: If these scripts are accidentally removed from `references/scripts/`, agents running with `event-driven: no` will break. The scripts must remain present even after template migration.
- **compose.py deploy-all race**: If compose runs while an agent is mid-cycle reading its CLAUDE.md, the agent may read a partially-written file. The existing atomic write pattern (`.tmp` → `mv`) must be preserved in compose output.
- **tracker.py comment dedup by event_id**: Without this fix (GAP-7), re-emitted events produce duplicate comments. Any closure API test with re-emission must verify comment count.
- **context-pressure path for clone agents**: GAP-8 (harness reads primary repo path instead of clone path). If not fixed, harness may not detect context pressure for clone-based agents, leading to missed restarts.
- **Event bus overflow at 1000 events**: If disk persistence is implemented but the in-memory deque cap is not removed or raised, high-volume scenarios will still lose events. Smoke test TC-RC02 implicitly covers this.
- **statusline.sh cycle-timer display**: statusline.sh uses `iter-N.md` mtime and `current-state` file for cycle display. After Phase 3, these files may not be updated. Status bar display may show stale or broken cycle timer. Not a blocking regression but should be noted as a known degraded-display risk pending statusline.sh updates (out of scope for this EPIC per CONTEXT.md).
- **health_check.py legacy fallback**: With event-driven architecture, health_check.py is fully deprecated. Its continued presence in harness as a fallback (lines 201-214) should not cause errors but should produce no false-positive health signals for event-driven agents.
