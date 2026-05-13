# FEAT-PM-7630 Test Plan — Event-Driven Agent Architecture

> Cross-referenced from Claude and DeepSeek test plans — 46 test cases total (32 TCs + 10 smoke checks + 4 CQs).

## Overview

This test plan covers the 4-phase EPIC that replaces SquidSquad's cycle-based polling model with a pure event-driven architecture. Phases are tested in dependency order. Phase 1.5 prerequisites gate all Phase 2 testing. Phase 3 template migration gates Phase 4 validation.

**Scope**: harness.py event infrastructure, Monitor tool wake mechanism, event closure API, template migration across all roles, regression of cycle model fallback, race condition mitigations, Windows-specific process and file behavior, failure modes.

**Zero-gap gate**: Any TC failure sends the work back to dev. No "noted for follow-up" exceptions.

---

## 1. Prerequisites — Phase 1.5 Infrastructure

### TC-P1: Event Bus Disk Persistence Survives Harness Restart

- **Precondition**: Harness running with `event-driven: yes`. At least one event emitted and stored (e.g., `scan-due` for pm role). Event visible via `GET /events`. Event bus has a disk-persistent storage backend (dev-chosen format: file-per-event, append-only log, or SQLite per CONTEXT.md dev discretion). `EventStream` in harness.py backed by persistent store rather than the current pure in-memory deque (harness.py line 352: `maxlen=1000`).
- **Steps**:
  1. Record the event ID from `GET /events`.
  2. Hard-kill the harness process (`taskkill /F /PID <harness_pid>` on Windows, `kill -9` on Unix).
  3. Confirm harness is dead: `tasklist /FI "PID eq <harness_pid>"` (Windows) or `kill -0 <harness_pid>` (Unix) — should report not found.
  4. Restart harness: `python references/scripts/harness.py`.
  5. Wait for harness to finish `deferred_init` (watch for "Auto-starting all agents..." and "Port file distributed" log lines).
  6. Query `GET /events` again.
- **Expected**: The previously stored event is still present with the same ID and payload. No data loss from kill-and-restart. Event status preserved (if `dispatched` before kill, it should appear as `dispatched` or `abandoned` after restart — never absent).
- **Verification**:
  ```bash
  # Before restart: capture event ID
  EVENT_ID=$(curl -s http://localhost:<PORT>/events | python -c "import sys,json; evts=json.load(sys.stdin); print(evts[0]['id'] if evts else 'NO_EVENTS')")
  echo "Captured event ID: $EVENT_ID"
  # ... kill and restart harness ...
  # After restart: verify same ID present
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  target = next((e for e in evts if e['id'] == '$EVENT_ID'), None)
  print('PASS' if target is not None else 'FAIL: event lost on restart')
  print('Payload:', target.get('payload') if target else 'N/A')
  "
  ```

---

### TC-P2: Clone Event Bus Discovery Works for Sibling Directories

- **Precondition**: Primary repo at known path (e.g., `D:\Dev\Dev\SquidSquad`). A clone exists as a sibling directory (e.g., `D:\Dev\Dev\SquidSquad-skill`). Harness running in the primary repo. `deferred_init` has completed and distributed `.harness-port` into the clone's `.squidsquad/` directory.
- **Steps**:
  1. Verify harness distributed the port file: `cat <clone_root>/.squidsquad/.harness-port` — should contain the port number.
  2. From within the clone directory, invoke `EventBusReader._discover_port()` directly:
     ```python
     import sys; sys.path.insert(0, '<primary_repo>/references/scripts')
     from event_bus_reader import EventBusReader
     r = EventBusReader(role='skill')
     print(r._discover_port())
     ```
  3. Using the discovered port, query `GET /events`.
- **Expected**: Port is discovered (non-None). `GET /events` returns 200 OK with a JSON list. Agent in clone can successfully reach the harness event bus. No silent `[]` return from `event_bus_reader.query()` fallthrough.
- **Verification**:
  ```bash
  # From clone directory
  python -c "
  import sys, json, urllib.request
  from pathlib import Path

  squid_dir = Path('.').resolve() / '.squidsquad'
  port_file = squid_dir / '.harness-port'
  port = None
  if port_file.exists():
      port = int(port_file.read_text(encoding='utf-8').strip())
  else:
      current = Path('.').resolve().parent
      for _ in range(5):
          candidate = current / '.squidsquad' / '.harness-port'
          if candidate.exists():
              port = int(candidate.read_text(encoding='utf-8').strip())
              break
          parent = current.parent
          if parent == current: break
          current = parent

  print('Port discovered:', port)
  assert port is not None, 'FAIL: port not found for sibling clone'
  url = f'http://127.0.0.1:{port}/events?limit=1'
  resp = urllib.request.urlopen(url, timeout=2)
  data = json.loads(resp.read().decode('utf-8'))
  print(f'Response OK')
  print('PASS')
  "
  ```
- **Regression signal**: If `_discover_port` returns `None`, the harness port distribution during `deferred_init` did not land in the clone's `.squidsquad/` directory, or the parent-walk fix for sibling clones is missing.

---

### TC-P3: Per-Role In-Flight Event Queue Prevents Double-Dispatch

- **Precondition**: Harness running with `event-driven: yes`. Per-role in-flight tracking exists — `in_flight_events` dict in `.harness-state.json`. One event dispatched to the `pm` role but not yet closed (simulate by having the agent not respond, or by injecting state directly).
- **Steps**:
  1. Emit an event targeted at the `pm` role. Confirm it enters `in_flight_events["pm"]` in `.harness-state.json`.
  2. Attempt to emit a second event to `pm` — trigger the idle-check timer or POST another event via API.
  3. Inspect the event bus and harness state.
- **Expected**: The second event is NOT dispatched while the first is unclosed. It is either queued internally (visible as `pending` per role) or emission is skipped with a log message. Only one event per role is in-flight at any time. `in_flight_events["pm"]` contains exactly one event ID.
- **Verification**:
  ```bash
  python -c "
  import json
  state = json.load(open('.squidsquad/.harness-state.json'))
  in_flight = state.get('in_flight_events', {})
  print('In-flight events:', in_flight)
  assert isinstance(in_flight, dict), 'FAIL: in_flight_events not present or not dict'
  "
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  pm_evts = [e for e in evts if e.get('role') == 'pm' and e.get('status') == 'dispatched']
  print('PM in-flight count:', len(pm_evts))
  print('PASS' if len(pm_evts) <= 1 else f'FAIL: {len(pm_evts)} dispatched events for pm — double dispatch')
  "
  ```

---

### TC-P4: Harness Thread Safety Under Concurrent Event and Health Polling

- **Precondition**: Harness running. Multiple roles active. Health polling thread running at 5-second interval (harness.py: `HEALTH_POLL_INTERVAL = 5`). Event receiver endpoint active. `_update_agent_from_event` and `update_health` are thread-safe after fix (previously both mutated `AgentState` fields outside the lock).
- **Steps**:
  1. Send 20 rapid `POST /events` requests concurrently using `concurrent.futures.ThreadPoolExecutor`.
  2. Simultaneously, trigger 5 health poll calls to `GET /agents/{role}/health` from a separate thread.
  3. Let all calls complete.
  4. Check harness process for exceptions or corrupted state.
- **Expected**: No `RuntimeError` about dictionary size change during iteration. No corrupted `AgentState` fields. All 20 events stored correctly. Health responses return valid data. Harness alive and responsive after test.
- **Verification**:
  ```bash
  python -c "
  import concurrent.futures, requests, time

  BASE = 'http://localhost:<PORT>'

  def post_event(i):
      r = requests.post(f'{BASE}/events', json={
          'event_type': 'test-thread', 'role': 'pm',
          'payload': {'seq': i, 'ts': time.time()}
      }, timeout=5)
      return r.status_code

  def poll_health():
      r = requests.get(f'{BASE}/agents/pm/health', timeout=5)
      return r.status_code, r.json().get('status')

  with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
      post_futs = [ex.submit(post_event, i) for i in range(20)]
      health_futs = [ex.submit(poll_health) for _ in range(5)]
      concurrent.futures.wait(post_futs + health_futs, timeout=30)

  post_codes = [f.result() for f in post_futs]
  health_results = [f.result() for f in health_futs]

  post_fails = [c for c in post_codes if c >= 500]
  health_fails = [(c, s) for c, s in health_results if c >= 500]

  evts = requests.get(f'{BASE}/events').json()
  test_evts = [e for e in evts if e.get('event_type') == 'test-thread']

  print(f'POST failures: {len(post_fails)}/{len(post_codes)}')
  print(f'Health failures: {len(health_fails)}/{len(health_results)}')
  print(f'Test events stored: {len(test_evts)}')

  if not post_fails and not health_fails and len(test_evts) >= 20:
      print('PASS')
  else:
      print('FAIL')
  "
  # Also inspect harness logs/stdout for RuntimeError or lock contention
  ```

---

## 2. Phase 2 — Event Wake and Closure

### TC-2-01: Happy Path — Full Event Lifecycle (Emit → Wake → Work → Close)

- **Precondition**: `event-driven: yes` in config.md. Claude Code upgraded to v2.1.98+. Monitor tool validated per CONTEXT.md checklist (lines 76-81). Harness running. PM agent running with event-driven template (no `/loop`). Agent is idle, Monitor tool watching event bus. `POST /events/{id}/complete` endpoint implemented.
- **Steps**:
  1. Trigger an event emission — either wait 10 minutes for `scan-due`, or manually emit via:
     ```json
     {"event_type": "scan-due", "role": "pm", "payload": {"reason": "idle-timeout", "scan_targets": ["vault", "pipeline"]}}
     ```
  2. Observe that Monitor tool detects the event and the agent session wakes (visible in terminal or agent log).
  3. Agent reads event context from the payload.
  4. Agent performs creative work (e.g., improvement scan for `scan-due` type).
  5. Agent posts `POST /events/{event_id}/complete` with a valid result payload (see TC-2-02 for schema).
  6. Harness processes the closure callback: executes status transitions, tracker comments, git commit/push.
  7. Harness marks the event `closed`.
- **Expected**: Event transitions from `dispatched` → `closed`. Harness executes all side effects from the closure payload. Agent returns to idle. `in_flight_events["pm"]` is cleared.
- **Verification**:
  ```bash
  EVENT_ID="<from_emission>"
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  target = next((e for e in evts if e['id'] == '$EVENT_ID'), None)
  print('Event status:', target['status'] if target else 'NOT FOUND')
  assert target is not None, 'FAIL: event not found in bus'
  assert target['status'] == 'closed', f'FAIL: status is {target.get(\"status\")}'
  print('PASS')
  "
  git log --oneline -3
  python -c "
  import json
  s = json.load(open('.squidsquad/.harness-state.json'))
  in_flight = s.get('in_flight_events', {})
  pm_flight = in_flight.get('pm')
  assert pm_flight is None or pm_flight == [], f'FAIL: pm still has in-flight events: {pm_flight}'
  print('PASS')
  "
  ```

---

### TC-2-02: Event Closure API — Full Payload Contract

- **Precondition**: Harness running with `event-driven: yes`. A `work-available` event dispatched to the `pm` role (event_id known). `POST /events/{id}/complete` endpoint implemented. Closure payload schema preserves all role-specific extras from cycle-runner.md (code_commit, pr_actions, vault_writes, issues_filed, etc.).
- **Steps**:
  1. POST to `POST /events/{event_id}/complete` with a full structured payload including role-specific extras:
     ```json
     {
       "status": "completed",
       "status_transitions": [
         {"number": 123, "from": "in-progress", "to": "pending-test"}
       ],
       "tracker_comments": [
         {"number": 123, "message": "Work done via event closure API. Status → Pending Test."}
       ],
       "commit_message": "pm: #123 — task complete via event closure",
       "summary": "Completed improvement scan. Filed 1 task.",
       "working_state_update": "# Working State\n\n- **Task**: none\n",
       "role_extras": {
         "pm": {
           "human_input_processed": "No new human input",
           "issues_filed": 1,
           "issues_verified": 0,
           "tasks_verified": 0,
           "tasks_shipped": 0,
           "external_issues_triaged": 0,
           "health_alerts": 0,
           "vault_writes": 2
         }
       }
     }
     ```
  2. Check the HTTP response.
  3. Verify each field was acted upon by the harness.
- **Expected**: 200 OK with closed event record (`status: "closed"`). Tracker transition `#123 in-progress → pending-test` executed. Tracker comment posted. Git commit created. `working-state.md` updated. Role-specific extras recorded.
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

- **Precondition**: `event-driven: yes`. Event-type-specific timeouts configured: short tasks (`scan-due`, comment) = 5 min, long tasks (implementation) = 60 min per CONTEXT.md. A `scan-due` event dispatched to `pm`. Agent does NOT post closure (simulate: block agent or kill it before closure POST).
- **Steps**:
  1. Dispatch a `scan-due` event to pm. Record the dispatch timestamp.
  2. Verify the event enters `in_flight_events["pm"]` with dispatch timestamp.
  3. Wait for the configured timeout (5 minutes for `scan-due`, or use a shorter test-only override if harness supports one).
  4. Observe harness behavior at timeout.
- **Expected**: Harness detects the unclosed event and logs a diagnostic (event type, role, elapsed time). Harness action: if agent PID is alive → re-emit event or log warning; if agent PID is dead → mark event `abandoned` and trigger auto-reboot; if ambiguous → alert human. No silent hang.
- **Verification**:
  ```bash
  grep -i "timeout\|unclosed\|abandoned\|event-timeout" .squidsquad/harness.log 2>/dev/null || echo "Check harness stdout for timeout messages"

  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  t = next((e for e in evts if e['id'] == '<EVENT_ID>'), None)
  if t is None:
      print('FAIL: event not found')
  elif t.get('status') in ('abandoned', 'reemitted', 'timed-out'):
      print('PASS: event status =', t.get('status'))
  elif t.get('status') == 'dispatched':
      print('FAIL: event still dispatched after timeout — no diagnosis performed')
  else:
      print('UNEXPECTED:', t.get('status'))
  "
  ```

---

### TC-2-04: Agent Crash Mid-Event — Harness Detects via PID and Re-Emits

- **Precondition**: `event-driven: yes`. Agent running with a dispatched event in-flight. Agent PID tracked in `.harness-state.json` (field `claude_pid`).
- **Steps**:
  1. Dispatch a `work-available` event to `pm`. Confirm it appears in `in_flight_events["pm"]`.
  2. Hard-kill the agent: `taskkill /F /PID <claude_pid>` (Windows) or `kill -9 <claude_pid>` (Unix).
  3. Wait one health poll cycle (5 seconds).
  4. Observe harness behavior: check logs, agent status, event bus.
- **Expected**: Harness detects agent death via PID check within 5 seconds. Agent `status` transitions to `stalled` or `stopped`. Agent `intent` set to `restarting` (auto-reboot). Harness re-emits the in-flight event (new event with same payload, or original event status set to `reemitted`). New agent instance starts and receives the re-emitted event.
- **Verification**:
  ```bash
  curl -s http://localhost:<PORT>/agents/pm | python -c "
  import sys, json
  a = json.load(sys.stdin)
  print('Status:', a.get('status'))
  print('Intent:', a.get('intent'))
  assert a.get('status') in ('stalled', 'stopped', 'starting'), f'FAIL: unexpected status {a.get(\"status\")}'
  "
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  reemitted = [e for e in evts if e.get('status') == 'reemitted' or (e.get('payload', {}).get('original_event_id') == '<EVENT_ID>')]
  print('Re-emission candidates:', len(reemitted))
  assert len(reemitted) >= 1, 'FAIL: no re-emitted event found'
  print('PASS')
  "
  ```

---

### TC-2-05: Harness Crash During Closure Processing — Event Replays Without Duplicates

- **Precondition**: `event-driven: yes`. Agent has just posted `POST /events/{event_id}/complete`. Harness is mid-processing the closure callback. The atomicity contract (at-most-once or at-least-once with idempotency per CONTEXT.md) is implemented.
- **Steps**:
  1. Dispatch an event, have agent complete work and POST closure.
  2. Immediately hard-kill the harness after it receives the closure POST but before it finishes persisting `status: closed` to disk. (Requires a test hook — e.g., a flag `.delay-closure` that makes harness pause after receiving the POST.)
  3. Restart the harness.
  4. Observe what harness does with the event on restart.
- **Expected (at-most-once model)**: Event was persisted as `closed` before side effects, so harness skips side effects on replay. OR event was not persisted → replays but all side effects are idempotent (no duplicate tracker comments, no duplicate git commits).
- **Expected (at-least-once model)**: Harness replays the unclosed event. Side effects execute again but are idempotent (comments dedup by event_id per GAP-7, git commits idempotent if same tree). Zero duplicates visible.
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
  t = next((e for e in evts if e['id'] == '<EVENT_ID>'), None)
  print('Status:', t['status'] if t else 'NOT FOUND')
  "
  ```

---

### TC-2-06: scan-due Event Emitted After 10-Minute Idle with Issue Gate

- **Precondition**: `event-driven: yes`. `scan-idle-timeout: 10` in config.md. PM role has `last_event_completed["pm"]` older than 10 minutes (set in harness state or simply wait). No open issues assigned to PM role (issue gate clear). Harness idle-check thread active.
- **Steps**:
  1. Verify no open issues for pm: `python references/scripts/tracker.py list-issues pm --status open` → empty.
  2. Confirm `last_event_completed["pm"]` is older than 10 minutes (inspect `.harness-state.json`).
  3. Wait for the harness idle-check thread to fire (within 30 seconds of the 10-minute mark, or trigger manually if harness has a test endpoint).
  4. Inspect the event bus for a new `scan-due` event.
- **Expected**: Harness emits a `scan-due` event to `pm`. Event appears in `GET /events` with `event_type: "scan-due"` and `role: "pm"`. Payload includes scan targets, quiet-cycle context, and last scan timestamp.
- **Variation (issue gate active)**: Create an open issue assigned to pm. Reset `last_event_completed` to older than 10 minutes. Expected: harness does NOT emit `scan-due` — issue gate suppressed it.
- **Verification**:
  ```bash
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  scans = [e for e in evts if e.get('event_type') == 'scan-due' and e.get('role') == 'pm']
  print('scan-due events for pm:', len(scans))
  assert len(scans) >= 1, 'FAIL: no scan-due event emitted'
  for s in scans:
      print('  Payload:', s.get('payload'))
  print('PASS')
  "

  # Issue gate test:
  python references/scripts/tracker.py create-issue \
    --title "Test gate issue for TC-2-06" --body "Temporary — delete after test" \
    --role pm --severity low --reporter pm-lead
  # Reset last_event_completed timestamp in .harness-state.json to an old value
  # Wait for idle-check interval
  # Confirm no new scan-due events (count unchanged from above)
  ```

---

### TC-2-07: stop-requested Event — Agent Detects, Checkpoints, Exits Cleanly

- **Precondition**: `event-driven: yes`. PM agent running (idle or mid-work). Monitor tool watching event bus. `stop-requested` event type exists in event_catalog.py.
- **Steps**:
  1. Trigger graceful stop: `python references/scripts/start_team.py --stop pm` (or `POST /agents/pm/stop`).
  2. Harness sets agent `intent=stopping` and emits `stop-requested` event on the event bus.
  3. Monitor tool detects the `stop-requested` event (same channel as work events — unified stop channel, no sentinel file).
  4. Agent reads the event, checkpoints `working-state.md`, and exits cleanly.
- **Expected**: `working-state.md` updated with a non-empty checkpoint. Agent PID no longer alive. Harness transitions agent `intent` to `stopped`. No orphaned Claude Code process.
- **Verification**:
  ```bash
  cat .squidsquad/pm/working-state.md
  stat .squidsquad/pm/working-state.md  # check mtime is recent

  python -c "
  import json, os
  state = json.load(open('.squidsquad/.harness-state.json'))
  pm = state.get('agents', {}).get('pm', {})
  pid = pm.get('claude_pid')
  print('Agent PID:', pid)
  try:
      os.kill(pid, 0)
      print('FAIL: process still alive')
  except ProcessLookupError:
      print('PASS: process exited')
  except PermissionError:
      print('WARNING: PermissionError — use tasklist /FI as secondary check')
  "

  curl -s http://localhost:<PORT>/agents/pm | python -c "
  import sys, json
  a = json.load(sys.stdin)
  print('Intent:', a.get('intent'))
  assert a.get('intent') == 'stopped', f'FAIL: intent is {a.get(\"intent\")}'
  print('PASS')
  "
  ```

---

### TC-2-08: Terminal Window Closed on Clean Stop (Windows)

- **Precondition**: Windows platform. `event-driven: yes`. PM agent spawned via `boot_remote.py` `_spawn_windows`. `terminal_pid` captured at spawn and stored in `.harness-state.json` (new field `terminal_pid` in `AgentState` — separate from `claude_pid`). Harness has platform-specific terminal close logic.
- **Steps**:
  1. Boot a pm agent and confirm `terminal_pid` is populated in `.harness-state.json`.
     ```bash
     python -c "import json; s=json.load(open('.squidsquad/.harness-state.json')); print(s['agents']['pm'].get('terminal_pid'))"
     ```
  2. Issue a graceful stop: `python references/scripts/start_team.py --stop pm`.
  3. Wait for TC-2-07 to pass (agent intent transitions to `stopped`).
  4. Observe the terminal window.
- **Expected**: Terminal window closes — not just the Claude process, but the terminal window itself. `terminal_pid` process no longer alive. No zombie terminal windows remaining.
- **Verification**:
  ```bash
  python -c "
  import json, os, sys, subprocess
  state = json.load(open('.squidsquad/.harness-state.json'))
  pm = state.get('agents', {}).get('pm', {})
  term_pid = pm.get('terminal_pid')
  if term_pid is None:
      print('FAIL: terminal_pid not tracked in state file')
      sys.exit(1)
  try:
      os.kill(term_pid, 0)
      print('FAIL: terminal process still alive, PID', term_pid)
  except (ProcessLookupError, PermissionError):
      result = subprocess.run(
          ['tasklist', '/FI', f'PID eq {term_pid}'],
          capture_output=True, text=True
      )
      if 'No tasks are running' in result.stdout or 'INFO: No tasks' in result.stdout:
          print('PASS: terminal window closed, PID', term_pid, 'gone')
      else:
          print('WARNING: tasklist output:', result.stdout[:200])
  "
  ```
- **Note on Windows feasibility**: `_spawn_windows` currently uses `wt.exe new-tab` or `cmd /c start` — neither reliably returns the terminal window PID. The `subprocess.Popen` PID may be the `wt.exe` invoker, not the terminal tab. This TC may need revision once the dev agent designs the actual terminal PID capture mechanism. The TC verifies end-state (window closed), not the specific capture method.

---

## 3. Phase 3 — Template Migration

### TC-3-01: Agents Boot Without /loop Command

- **Precondition**: `event-driven: yes`. All templates migrated (Phase 3 complete). `compose.py deploy-all` run successfully. Fresh agent session started (no prior context). Monitor tool validated (or stateless spawn chosen as fallback).
- **Steps**:
  1. Boot a pm agent: `python references/scripts/start_team.py --role pm`.
  2. Observe startup behavior in the agent terminal.
  3. Wait 30 seconds for any `/loop` invocation that might occur.
- **Expected**: Agent boots and enters idle state without invoking `/loop`. No `/loop` command appears in the session. Agent waits for events via Monitor tool. Terminal shows event-driven orientation message (replacing the previous "Boot. Begin your first Ralph Loop cycle now." from `thin_launcher.py`).
- **Verification**:
  - Review agent terminal output: no `/loop 30m` or `/loop` invocation present.
  - Agent startup prompt must NOT contain "Boot. Begin your first Ralph Loop cycle now."
  - Agent is alive (PID in `.harness-state.json`) with health status `running`.
  ```bash
  curl -s http://localhost:<PORT>/agents/pm | python -c "
  import sys, json
  a = json.load(sys.stdin)
  print('Status:', a.get('status'))
  print('Intent:', a.get('intent'))
  assert a.get('status') == 'running', f'FAIL: status is {a.get(\"status\")}'
  print('PASS')
  "
  ```

---

### TC-3-02: Agent Templates Contain No Cycle Step Prose

- **Precondition**: Phase 3 template migration complete. `compose.py deploy-all` run. All `.squidsquad/*/CLAUDE.md` files regenerated. Source templates in `references/roles/` and `references/sub-skills/` updated.
- **Steps**:
  1. Search composed CLAUDE.md files for cycle-specific prose patterns.
  2. Search source template files for removed patterns.
- **Expected**: None of the following patterns appear in any role's composed output:
  - `/loop` invocation
  - `cycle_pre.py` references
  - `cycle_post.py` references
  - `cycle-input.json` read instructions
  - `cycle-output.json` write instructions
  - Ralph Loop phase descriptions ("Phase 1 — Pre-Cycle", "Phase 2 — Creative Work", "Phase 3 — Post-Cycle")
  - `iter-N.md` iteration log references
  - `current-state` file write instructions (cycle-based)
  - `cycle_number` field references
  - `quiet-cycle` concept (cycle-count-based quiet detection)
- **Verification**:
  ```bash
  for pattern in "/loop" "cycle_pre" "cycle_post" "cycle-input.json" "cycle-output.json" "Ralph Loop" "cycle_number" "quiet.cycle" "iter-N.md"; do
    echo "--- Checking '$pattern' ---"
    matches=$(grep -rli "$pattern" .squidsquad/*/CLAUDE.md 2>/dev/null)
    if [ -n "$matches" ]; then
      echo "FAIL: '$pattern' found in: $matches"
    else
      echo "PASS: '$pattern' not found in composed output"
    fi
  done
  ```

---

### TC-3-03: compose deploy-all Produces Valid CLAUDE.md Without Cycle Sub-Skills

- **Precondition**: Phase 3 source changes complete. Cycle-related includes removed from all `includes.yml` files (`common/cycle-runner`, `common/context-pressure`, `common/self-restart`, `common/interval-sync`). New `event-driven-workflow.md` sub-skill created at `references/sub-skills/common/event-driven-workflow.md`.
- **Steps**:
  1. Run `python references/scripts/compose.py deploy-all`.
  2. Check exit code — must be 0.
  3. Verify each role's composed CLAUDE.md exists and is non-empty.
  4. Verify removed includes are absent from composed files.
  5. Verify `event-driven-workflow.md` content appears in composed files.
- **Expected**: `compose.py deploy-all` exits 0. All role CLAUDE.md files updated. None contain content from `common/cycle-runner`, `common/context-pressure`, `common/self-restart`, or `common/interval-sync`. All contain `event-driven-workflow` content. No compose errors about missing includes.
- **Verification**:
  ```bash
  python references/scripts/compose.py deploy-all
  echo "compose exit code: $?"

  for role in pm qa dev dm skill; do
    claude_md=".squidsquad/$role/CLAUDE.md"
    if [ -f "$claude_md" ]; then
      if grep -q "event-driven" "$claude_md" 2>/dev/null; then
        echo "PASS: $role has event-driven-workflow content"
      else
        echo "FAIL: $role missing event-driven-workflow content"
      fi
    else
      echo "FAIL: $claude_md does not exist"
    fi
  done

  for removed in "cycle-runner.md" "context-pressure.md" "self-restart.md" "interval-sync.md"; do
    echo "--- Checking '$removed' ---"
    if grep -rq "$removed" .squidsquad/*/CLAUDE.md 2>/dev/null; then
      echo "FAIL: '$removed' still present in composed output"
    else
      echo "PASS: '$removed' absent from all composed output"
    fi
  done
  ```

---

## 4. Regression Tests

### TC-R01: event-driven: no Preserves Full Cycle Model Unchanged

- **Precondition**: `event-driven: no` in config.md (default). All #7630 code changes present but gated behind the flag. `cycle_pre.py` and `cycle_post.py` still present at `references/scripts/`.
- **Steps**:
  1. Verify config: `python references/scripts/config.py get event-driven` → should output `no` or empty.
  2. Run `compose.py deploy-all` — should produce cycle-model CLAUDE.md files (with `/loop`, cycle-runner, etc.).
  3. Boot a pm agent: `python references/scripts/start_team.py --role pm`.
  4. Confirm agent invokes `/loop [INTERVAL]m` at startup.
  5. Wait for one complete cycle (cycle_pre → creative work → cycle_post).
  6. Verify `cycle-input.json` written.
  7. Verify `cycle-output.json` consumed.
  8. Verify iteration log written (`iter-N.md` in `.squidsquad/pm/iterations/`).
  9. Verify git commit produced.
- **Expected**: Full existing cycle model functions without degradation. No event-driven behavior activates. No errors related to missing event-driven infrastructure. `/loop` works as before.
- **Verification**:
  ```bash
  python references/scripts/config.py get event-driven
  # Expected: no (or empty)

  ls -la .squidsquad/pm/cycle-input.json
  ls -la .squidsquad/pm/cycle-output.json
  ls -la .squidsquad/pm/iterations/
  git log --oneline -1  # should show cycle commit

  curl -s http://localhost:<PORT>/agents/pm | python -c "
  import sys, json
  a = json.load(sys.stdin)
  print('Status:', a.get('status'))
  assert a.get('status') == 'running', f'FAIL: status={a.get(\"status\")}'
  print('PASS: cycle model functioning')
  "
  ```

---

### TC-R02: Mixed-Mode Warning on Harness Startup

- **Precondition**: `event-driven: yes` for pm role. `event-driven: no` (or not set) for skill role. Harness configured to detect mismatched intent/config across roles.
- **Steps**:
  1. Set config so one role is event-driven and another is cycle-based (exact mechanism depends on implementation — per CONTEXT.md: "Both models cannot run simultaneously for the same role").
  2. Start harness: `python references/scripts/harness.py`.
  3. Check harness startup output (stdout) and logs.
- **Expected**: Harness prints a visible warning that roles are running in mixed mode. Warning identifies which roles are in which mode. Harness still starts (warning only, no abort). Both roles function in their respective modes.
- **Verification**:
  ```bash
  python references/scripts/harness.py 2>&1 | grep -i "mixed\|warning\|event-driven.*no\|cycle.*event"
  # At least one warning line expected. Empty output = FAIL.
  ```

---

### TC-R03: Existing Tracker Transitions Work Through Closure API

- **Precondition**: `event-driven: yes`. A real GitHub Issue at a known status (e.g., `#42` at `in-progress`). Closure API fully implemented. `tracker.py transition()` interface unchanged.
- **Steps**:
  1. POST to `POST /events/{event_id}/complete` with a tracker transition payload:
     ```json
     {
       "status_transitions": [
         {"number": 42, "from": "in-progress", "to": "pending-test"}
       ],
       "tracker_comments": [
         {"number": 42, "message": "Verified via event closure API. Status → Pending Test."}
       ],
       "commit_message": "pm: regression TC-R03 — closure API transition test",
       "summary": "Regression test for tracker transitions via closure API"
     }
     ```
  2. Harness processes closure and calls `tracker.py transition 42 in-progress pending-test --role pm-lead`.
  3. Verify the transition and comment.
- **Expected**: Issue `#42` transitions from `in-progress` to `pending-test` exactly as if `tracker.py transition` was called directly. Comment posted with correct content. No behavioral difference from direct `tracker.py` calls — closure API is a pass-through to the same tracker functions.
- **Verification**:
  ```bash
  python references/scripts/tracker.py get-labels 42
  # Expected: status:pending-test label present

  gh issue view 42 --json labels --jq '[.labels[].name] | sort'
  gh issue view 42 --json comments --jq '.comments[-1].body'
  # Expected: contains "Verified via event closure API"

  # Revert after test
  python references/scripts/tracker.py transition 42 pending-test in-progress --role pm-lead
  ```

---

## 5. Race Conditions

### TC-RC01: Startup Race — Agents Don't POST Before Server Ready

- **Precondition**: `event-driven: yes`. Fresh harness start. Agents configured to auto-boot via `deferred_init`. Fix in place: either server accepts connections before agents are spawned (reordered in lifespan), or agent closure POST includes retry logic with backoff.
- **Steps**:
  1. Start harness with timing instrumentation.
  2. Monitor for any `POST /events/{id}/complete` or `POST /events` calls made before the harness FastAPI server is fully accepting connections (before `yield` in the lifespan).
  3. Observe agent behavior on startup.
- **Expected**: No agent POST attempts before server is ready. Either agent spawn is delayed until after server `yield`, or closure POST retries with backoff on connection-refused/503. No events lost due to startup timing.
- **Verification**:
  ```bash
  python -c "
  import subprocess, time, requests, threading

  t0 = time.time()
  proc = subprocess.Popen(
      ['python', 'references/scripts/harness.py'],
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
  )

  lines = []
  def reader():
      for line in proc.stdout:
          lines.append(line)
  threading.Thread(target=reader, daemon=True).start()

  ready_at = None
  for i in range(60):
      try:
          r = requests.get('http://localhost:<PORT>/status', timeout=0.5)
          if r.status_code == 200:
              ready_at = time.time()
              print(f'Server ready at t+{ready_at - t0:.2f}s')
              break
      except Exception:
          pass
      time.sleep(0.25)

  time.sleep(5)

  early_errors = [l for l in lines if 'connection refused' in l.lower() or '503' in l]
  if early_errors:
      print('FAIL: early connection errors detected')
      for l in early_errors[:5]:
          print(f'  {l.strip()}')
  elif ready_at:
      print('PASS: server ready before agent activity')
  else:
      print('FAIL: server did not become ready')

  proc.terminate()
  "
  ```

---

### TC-RC02: Event ID Uniqueness Under High Volume

- **Precondition**: Harness running. Event emission working. The two ID generation schemes in `event_bus.py` and `harness.py` have been unified to one scheme with sufficient entropy (at least 12 hex chars).
- **Steps**:
  1. Emit 1,000 events rapidly via concurrent `POST /events` calls.
  2. Retrieve all events via `GET /events`.
  3. Check for duplicate event IDs.
- **Expected**: All 1,000 events have unique IDs. No collisions. The unified scheme produces no duplicates at this volume.
- **Verification**:
  ```bash
  python -c "
  import concurrent.futures, requests

  BASE = 'http://localhost:<PORT>'

  def emit(i):
      try:
          r = requests.post(f'{BASE}/events', json={
              'event_type': 'test-collision', 'role': 'pm',
              'payload': {'seq': i}
          }, timeout=5)
          return r.json().get('id')
      except Exception:
          return None

  with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
      ids = list(ex.map(emit, range(1000)))

  ids = [i for i in ids if i]
  unique = len(set(ids))
  print(f'Emitted: {len(ids)}, Unique IDs: {unique}')
  if unique == len(ids):
      print('PASS')
  else:
      print(f'FAIL: {len(ids) - unique} collisions detected')
      from collections import Counter
      dupes = [id for id, cnt in Counter(ids).items() if cnt > 1]
      print(f'Duplicate IDs (first 5): {dupes[:5]}')
  "
  ```

---

### TC-RC03: Shutdown — In-Flight Events Marked Abandoned

- **Precondition**: `event-driven: yes`. At least one event in-flight (dispatched, not closed) for the pm role. `in_flight_events["pm"]` populated in harness state.
- **Steps**:
  1. Dispatch an event to pm. Confirm it is in-flight (agent does not close it).
  2. Trigger harness shutdown via Ctrl+C or `POST /shutdown`.
  3. Wait for harness to fully shut down. Observe shutdown log output.
  4. Restart harness.
  5. Inspect event status in the restored event bus.
- **Expected**: On shutdown, harness marks all in-flight events as `abandoned` before exiting (or during `load_state` on restart). On restart, harness does NOT automatically re-emit `abandoned` events — they are stale and require human or harness logic decision. No silent event loss — the event remains visible with `abandoned` status.
- **Verification**:
  ```bash
  # After restart
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  abandoned = [e for e in evts if e.get('status') == 'abandoned']
  print('Abandoned events:', len(abandoned))
  for a in abandoned:
      print(f'  ID: {a[\"id\"]}, type: {a.get(\"event_type\")}, role: {a.get(\"role\")}')
  print('PASS' if abandoned else 'WARNING: no abandoned events — event may have been silently lost')
  "

  # Verify no auto-replay of abandoned events (no new dispatched events)
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  dispatched = [e for e in evts if e.get('status') == 'dispatched' and e.get('role') == 'pm']
  print(f'Dispatched events for pm after restart: {len(dispatched)}')
  # If auto-replay is NOT the design, should be 0
  "
  ```

---

### TC-RC04: Compose-Completed Before Reboot — Agent Reads Correct Templates

- **Precondition**: `event-driven: yes`. Harness has compose-completed event logic where it emits `compose-completed` before rebooting affected agents. An agent is alive when `compose deploy-all` runs.
- **Steps**:
  1. Start a pm agent and let it reach idle state (Monitor tool watching).
  2. Trigger `compose.py deploy-all` (which emits `compose-completed` and then triggers `_reboot_affected_agents`).
  3. Observe whether the agent wakes on `compose-completed` before it is rebooted.
  4. If agent wakes on `compose-completed` before reboot, check which CLAUDE.md it reads.
- **Expected**: Agent either: (a) does not wake on `compose-completed` (harness reboots it before the Monitor tool sees the event), or (b) if it wakes, it reads the newly composed CLAUDE.md (not a stale version). No scenario where the agent wakes, reads old templates, processes work with stale instructions, and then is rebooted discarding that work.
- **Verification**:
  ```bash
  # Check compose-completed event timing vs. reboot timing in harness logs
  grep -E "compose-completed|reboot|restarting" .squidsquad/harness.log 2>/dev/null || echo "Check harness stdout"
  # Expected: reboot signal occurs BEFORE or CONCURRENT WITH compose-completed event delivery
  # Also verify agent reads fresh CLAUDE.md after reboot
  curl -s http://localhost:<PORT>/agents/pm | python -c "
  import sys, json
  a = json.load(sys.stdin)
  print('Status after compose+reboot:', a.get('status'))
  print('Intent:', a.get('intent'))
  "
  ```

---

## 6. Windows-Specific Tests

### TC-WIN01: File Locking on Context-Pressure Reads — No PermissionError

- **Precondition**: Windows platform. Harness running. An agent (or `statusline.sh`) actively writing context-pressure files via atomic `.tmp` → `mv` pattern. Harness reading context-pressure via `Path.read_text()`.
- **Steps**:
  1. Simulate high-frequency context-pressure writes: a loop that rapidly writes to `.squidsquad/pm/context-pressure` via atomic `.tmp` → `mv`.
  2. Simultaneously, repeatedly query `GET /agents/pm/health` from harness.
  3. Run for 60 seconds.
  4. Check harness output for `PermissionError`, `OSError`, or file-read failures.
- **Expected**: No file locking exceptions. Harness reads either old or new data but never crashes. If a `PermissionError` occurs, the harness `try/except OSError` block handles it gracefully (returns `context_pressure: None`).
- **Verification**:
  ```bash
  # In one terminal: rapid context-pressure writes
  python -c "
  import time
  from pathlib import Path
  ctx_file = Path('.squidsquad/pm/context-pressure')
  for i in range(300):
      tmp = ctx_file.with_suffix('.tmp')
      tmp.write_text(str(30 + (i % 40)), encoding='utf-8')
      tmp.replace(ctx_file)
      time.sleep(0.2)
  "

  # In another terminal: rapid health reads
  for i in $(seq 1 60); do
    curl -s http://localhost:<PORT>/agents/pm/health | python -c "import sys,json; print(json.load(sys.stdin).get('context_pressure'))"
    sleep 1
  done

  # Check harness stdout for tracebacks or OSError
  # Expected: no PermissionError, no crashes
  ```

---

### TC-WIN02: PID Reuse — Harness Detects Agent Death Despite Fast PID Recycle

- **Precondition**: Windows platform. Harness running with health polling at 5-second intervals. Agent PID tracked in `.harness-state.json`. Process start time or process name also stored for disambiguation (per RESEARCH.md Windows-Specific Risks).
- **Steps**:
  1. Boot an agent and record its PID and process start time.
  2. Kill the agent (`taskkill /F /PID <pid>`).
  3. Simulate PID reuse (difficult to orchestrate naturally — test harness checks harness behavior when PID is alive but process name does not match expected agent process).
  4. Wait one health poll cycle (5 seconds).
  5. Check harness detection.
- **Expected**: Harness detects the original agent is dead even if PID is reused. Uses a secondary factor (process name via `tasklist /FI "PID eq <pid>" /FO CSV`, or process start time comparison) to disambiguate. If PID is alive but process name does not match expected (e.g., not `claude` or `node`), harness marks agent `stalled` and triggers reboot.
- **Verification**:
  ```bash
  python -c "
  import json, subprocess, os, time

  state = json.load(open('.squidsquad/.harness-state.json'))
  pid = state.get('agents', {}).get('pm', {}).get('claude_pid')
  print(f'Agent PID: {pid}')

  subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)

  time.sleep(7)

  state2 = json.load(open('.squidsquad/.harness-state.json'))
  pm2 = state2.get('agents', {}).get('pm', {})
  status = pm2.get('status')
  intent = pm2.get('intent')
  print(f'After kill — status: {status}, intent: {intent}')
  assert status != 'running', f'FAIL: agent still marked running after kill'
  print('PASS' if status != 'running' else 'FAIL')
  "
  ```

---

### TC-WIN03: Terminal PID Tracking — PID Captured at Spawn

- **Precondition**: Windows platform. `boot_remote.py` `_spawn_windows` modified to capture and return the terminal PID alongside the agent PID. `boot_remote.boot_agent()` returns `terminal_pid` in result dict. Harness stores `terminal_pid` in `.harness-state.json` for the pm agent.
- **Steps**:
  1. Boot a pm agent: `python references/scripts/start_team.py --role pm`.
  2. Immediately check `.harness-state.json` for `terminal_pid` in the pm agent entry.
  3. Verify `terminal_pid` is non-None and corresponds to a real process.
  4. On Windows, verify via `tasklist /FI "PID eq <terminal_pid>"` that the process is a terminal host (`conhost.exe`, `WindowsTerminal.exe`, or `wt.exe`).
- **Expected**: `terminal_pid` is captured and stored at spawn time. It is different from `claude_pid`. The terminal PID corresponds to the actual window the agent runs in.
- **Verification**:
  ```bash
  python -c "
  import json, subprocess

  state = json.load(open('.squidsquad/.harness-state.json'))
  pm = state.get('agents', {}).get('pm', {})
  claude_pid = pm.get('claude_pid')
  term_pid = pm.get('terminal_pid')

  print(f'Claude PID: {claude_pid}')
  print(f'Terminal PID: {term_pid}')

  assert term_pid is not None, 'FAIL: terminal_pid not captured'
  assert term_pid != claude_pid, f'FAIL: terminal_pid == claude_pid ({term_pid}) — must be different'

  result = subprocess.run(
      ['tasklist', '/FI', f'PID eq {term_pid}'],
      capture_output=True, text=True
  )
  print('tasklist output:')
  print(result.stdout[:300])
  print('PASS' if term_pid and term_pid != claude_pid else 'FAIL')
  "
  ```

---

### TC-WIN04: Detached Process Stop Signal — stop-requested Event Works Without OS Signal

- **Precondition**: Windows platform. Agent spawned with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` flags (boot_remote.py). The harness cannot send SIGTERM or Ctrl+C to the agent — stop MUST be cooperative (event bus `stop-requested`) per CONTEXT.md Locked Decision #2.
- **Steps**:
  1. Boot a pm agent (detached process). Confirm agent is alive and processing events.
  2. Initiate graceful stop: `POST /agents/pm/stop` or `start_team.py --stop pm`.
  3. Harness emits `stop-requested` event on event bus.
  4. Monitor tool detects the stop event (same channel as work events).
  5. Wait for agent to exit (up to 30 seconds for checkpoint + exit).
- **Expected**: Agent detects `stop-requested` event via Monitor tool, checkpoints and exits cleanly — no OS signal needed. Harness detects exit via PID check. No `taskkill /F` needed for a clean stop.
- **Verification**:
  ```bash
  curl -s -X POST http://localhost:<PORT>/agents/pm/stop

  sleep 35

  python -c "
  import json, os
  state = json.load(open('.squidsquad/.harness-state.json'))
  pm = state.get('agents', {}).get('pm', {})
  pid = pm.get('claude_pid')
  print(f'Agent PID: {pid}, Intent: {pm.get(\"intent\")}')
  try:
      os.kill(pid, 0)
      print('FAIL: agent still alive')
  except (ProcessLookupError, PermissionError, TypeError):
      print('PASS: agent exited cleanly')
  "

  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  stop_evts = [e for e in evts if e.get('event_type') == 'stop-requested' and e.get('role') == 'pm']
  print(f'stop-requested events found: {len(stop_evts)}')
  "
  ```

---

## 7. Failure Modes

### TC-FM01: Monitor Tool Disconnect/Reconnect — Events Not Lost

- **Precondition**: `event-driven: yes`. Persistent session + Monitor tool wake model. Agent running with Monitor tool watching event bus. Disk-persistent event bus (TC-P1 passes) so events survive reconnection gaps.
- **Steps**:
  1. Simulate Monitor tool disconnection — temporarily block network access to harness port from agent, or wait for Monitor tool timeout to expire.
  2. During the disconnection gap, emit 3 events to the agent's role via `POST /events`.
  3. Restore Monitor tool connection (or unblock network).
  4. Agent's Monitor tool reconnects. Agent queries `GET /events?since=<last_processed_event_id>`.
- **Expected**: All 3 events emitted during the disconnection gap are delivered to the agent on reconnect. No events silently lost. Disk-persistent event bus retains them. Agent processes them in order.
- **Verification**:
  ```bash
  curl -s "http://localhost:<PORT>/events?event_type=test-disconnect" | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  closed = [e for e in evts if e.get('status') == 'closed']
  print(f'Events closed after reconnection: {len(closed)}')
  assert len(closed) >= 3, f'FAIL: only {len(closed)}/3 events processed'
  print('PASS')
  "
  ```

---

### TC-FM02: Git Push Failure in Closure — Push Failure Reflected in Event Status

- **Precondition**: `event-driven: yes`. A git remote temporarily unreachable (simulate by setting remote URL to a non-existent endpoint). An event dispatched to an agent that would normally produce a commit+push.
- **Steps**:
  1. Configure remote to cause push failure: `git remote set-url origin http://127.0.0.1:1/fake`.
  2. Dispatch a `work-available` event to pm.
  3. Agent does work, posts closure with `commit_message`.
  4. Harness processes closure — attempts `git push`, push fails.
  5. Observe harness behavior.
- **Expected**: Harness logs the push failure. Event closure is either: (a) marked `closed-with-errors` (commit succeeded locally but push failed), or (b) event remains `dispatched` with error note and is retried. Harness does NOT silently mark event `closed` if push failed — the closure API contract requires commit AND push before event is truly closed per CONTEXT.md ("Harness owns git commit/push"). Error handling from `cycle_post.py _do_commit_push` must be replicated in the harness closure handler.
- **Verification**:
  ```bash
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  t = next((e for e in evts if e['id'] == '<EVENT_ID>'), None)
  print('Event status:', t.get('status'))
  if t.get('status') == 'closed':
      print('FAIL: event closed but push failed — harness did not detect push failure')
  elif t.get('status') in ('dispatched', 'error', 'closed-with-errors'):
      print('PASS: push failure captured in event status')
  "
  # Restore remote after test
  git remote set-url origin <original_url>
  ```

---

### TC-FM03: Event Bus Overflow — Old Events Evicted Gracefully

- **Precondition**: Harness running. Event bus with a bounded size (1000 events if still using in-memory deque, or configurable limit if disk-persistent). Volume high enough to approach the limit.
- **Steps**:
  1. Emit 1,200 events rapidly via `POST /events`.
  2. Query `GET /events` and check total event count.
  3. Verify: with disk persistence, all 1,200 events stored. With in-memory deque (maxlen=1000), oldest 200 are evicted.
  4. Query `GET /events?since=<old_event_id>` using an ID that would have been evicted.
- **Expected**: Event bus handles overflow gracefully. No crash, no corruption. Evicted-cursor handling: returns oldest available events with a warning rather than empty response or 500 error. With disk persistence, the deque cap should be removed or significantly raised.
- **Verification**:
  ```bash
  python -c "
  import requests
  BASE = 'http://localhost:<PORT>'
  for i in range(1200):
      requests.post(f'{BASE}/events', json={
          'event_type': 'test-overflow', 'role': 'pm',
          'payload': {'seq': i}
      }, timeout=2)
      if i % 100 == 0: print(f'Emitted {i}...')
  print('Done emitting')
  "

  python -c "
  import requests
  evts = requests.get('http://localhost:<PORT>/events?limit=2000', timeout=2).json()
  test_evts = [e for e in evts if e.get('event_type') == 'test-overflow']
  print(f'Test events stored: {len(test_evts)}')
  if len(test_evts) == 1200:
      print('PASS: all events retained (disk persistence active)')
  elif len(test_evts) == 1000:
      print('PASS: deque bounded at 1000 — oldest 200 evicted as expected')
  else:
      print(f'UNEXPECTED: {len(test_evts)} events')
  "

  # Test evicted cursor handling
  FIRST_EVENT_ID="<id_of_first_emitted_event>"
  curl -s "http://localhost:<PORT>/events?since=$FIRST_EVENT_ID&limit=5" | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  print(f'Events returned with evicted cursor: {len(evts)}')
  print('PASS' if len(evts) > 0 else 'FAIL: empty response on evicted cursor — should return oldest available')
  "
  ```

---

## 8. Smoke Tests

Quick go/no-go checks before full TC execution. All must pass before investing in deep TC runs.

- [ ] Harness starts without error: `python references/scripts/harness.py` runs stably with no traceback.
- [ ] `GET /health` returns 200 OK within 2 seconds of harness start.
- [ ] `GET /events` returns 200 OK with a JSON list (empty list is acceptable).
- [ ] `POST /events` with a minimal payload returns 200 OK and a valid event ID.
- [ ] `.harness-state.json` exists and contains `in_flight_events` and `last_event_completed` fields after harness starts.
- [ ] `compose.py deploy-all` exits 0 with `event-driven: yes` config.
- [ ] Composed `pm/CLAUDE.md` does NOT contain `/loop` after deploy-all.
- [ ] Composed `pm/CLAUDE.md` DOES contain `event-driven-workflow` content after deploy-all.
- [ ] `event_bus_reader.py` `_discover_port()` returns non-None when called from within a sibling clone (requires TC-P2 environment).
- [ ] `start_team.py --stop pm` completes within 30 seconds with no hanging process.

---

## 9. Regression Risks

These are known risks that cannot be fully covered by test cases but must be monitored during QA:

- **cycle_pre/cycle_post scripts accidentally removed**: `references/scripts/cycle_pre.py` and `references/scripts/cycle_post.py` must remain present even after template migration. If removed, agents running with `event-driven: no` will break with `FileNotFoundError`. TC-R01 covers behavior; add a file-existence check to smoke tests.
- **compose.py deploy-all race**: If `compose deploy-all` runs while an agent is mid-cycle reading its `CLAUDE.md`, the agent may read a partially-written file. The existing atomic write pattern (`.tmp` → `mv`) in compose output must be preserved. Not easily automated — requires manual race-condition-injection testing.
- **tracker.py comment dedup by event_id (GAP-7)**: Without the `event_id` parameter on `tracker.comment()`, re-emitted events will post duplicate comments. TC-2-05 verifies at-most-once/idempotent behavior. If comments appear duplicated, GAP-7 is not fixed.
- **context-pressure path for clone agents (GAP-8)**: harness.py `GET /agents/{role}/health` reads context-pressure from the primary repo's path. For clone agents, `statusline.sh` writes to the clone's path. Harness reads the wrong file, potentially missing context pressure spikes. TC-WIN01 may inadvertently catch this if testing with a clone agent.
- **Event bus overflow at 1000 events**: If disk persistence is implemented but the in-memory deque cap is not removed or raised, high-volume scenarios still lose events. TC-FM03 covers this.
- **statusline.sh cycle-timer display**: `statusline.sh` uses `current-state` file mtime and `iter-N.md` files for cycle display. After Phase 3, these files are not updated. Status bar may show stale/broken cycle timer. Known degraded-display risk — `statusline.sh` redesign is out of scope for this EPIC per CONTEXT.md.
- **health_check.py legacy fallback**: `harness.py update_health()` calls `health_check.check_agent_health()` as fallback. Under `event-driven: yes`, this must not produce false-positive health signals. TC-R01 should verify `health_check.py` fallback does not activate in event-driven mode.
- **Per-event log format migration**: Historical `iter-N.md` files in `.squidsquad/<role>/iterations/` must coexist with new per-event log format. No migration path defined in this EPIC — discovery risk during QA.
- **Human input as event source**: `human-input-received` event type is not currently in `event_catalog.py` RECOGNIZED tier. If human input mid-event is not handled, it will be silently ignored or dropped. Flag for dev to confirm human input routing.

---

## 10. Comprehension Questions

These verify that a fresh agent, given only the migrated template files, can correctly derive the event-driven workflow. QA spawns a fresh subagent, provides only the listed files, and scores answers against expected derivations. No prior context or conversation memory permitted.

### CQ-1: How Does an Agent Wait for Work in Event-Driven Mode?

- **Files to provide**:
  - `.squidsquad/pm/CLAUDE.md` (composed output, post-migration — no `/loop`, no cycle prose)
  - `references/sub-skills/common/event-driven-workflow.md`
  - `references/sub-skills/common/agent-lifecycle.md` (rewritten for persistent session)
- **Question to ask fresh agent**: "You are a PM agent that has just booted. There is no `/loop` command and no `cycle_pre.py` to run. How do you wait for work to arrive? What tool or mechanism keeps you active between work items?"
- **Expected derivation**: Agent must answer that the Monitor tool (Claude Code v2.1.98+) watches the event bus for incoming events. The agent does not poll manually, does not sleep, and does not invoke `/loop`. The Monitor tool wakes the agent when an event with the agent's role arrives. The agent sits in an idle/persistent session state between events.
- **Pass criteria**: Answer mentions Monitor tool, event bus watching, and passive idle state. Must NOT mention `/loop`, `cycle_pre`, or manual polling.

---

### CQ-2: What Must an Agent Do After Completing Event Work?

- **Files to provide**:
  - `.squidsquad/pm/CLAUDE.md` (composed output, post-migration)
  - `references/sub-skills/common/event-driven-workflow.md`
- **Question to ask fresh agent**: "You have just finished the creative work for an event (e.g., an improvement scan triggered by a `scan-due` event). The work is done. What must you do next? What happens if you skip this step?"
- **Expected derivation**: Agent must answer that it is required to call `POST /events/{event_id}/complete` with a structured result payload (including status transitions, tracker comments, commit message, summary). Skipping this call leaves the event unclosed, which the harness detects as a diagnostic signal — the harness may diagnose a crash, re-emit the event, or alert the human. The harness (not the agent) executes git commits, pushes, and tracker transitions after receiving the closure.
- **Pass criteria**: Answer mentions the POST closure call with event_id, structured payload, and consequence of not closing. Must NOT say the agent commits or pushes directly.

---

### CQ-3: What Happens If a stop-requested Event Arrives?

- **Files to provide**:
  - `.squidsquad/pm/CLAUDE.md` (composed output, post-migration)
  - `references/sub-skills/common/event-driven-workflow.md`
  - `references/sub-skills/common/agent-lifecycle.md` (rewritten)
- **Question to ask fresh agent**: "While you are idle (or mid-work), a `stop-requested` event arrives on the event bus and the Monitor tool wakes you with it. What do you do? In what order?"
- **Expected derivation**: Agent must answer: (1) checkpoint current working state to `working-state.md`, (2) if mid-event, attempt to post a partial closure or note the interruption, (3) exit the session cleanly. Agent must NOT attempt to ignore the event, defer it, or continue working. The `stop-requested` event is the unified stop channel — the same Monitor tool that delivers work events also delivers the stop signal.
- **Pass criteria**: Answer includes checkpointing working state and clean exit. Must NOT say the agent polls a sentinel file or waits for `/loop` to end — the stop arrives via event bus, not via cycle end.

---

### CQ-4: How Does the Agent Know Which Event to Process Next?

- **Files to provide**:
  - `.squidsquad/pm/CLAUDE.md` (composed output, post-migration)
  - `references/sub-skills/common/event-driven-workflow.md`
- **Question to ask fresh agent**: "Multiple events may arrive for your role over time. How do you know which event to process now? Can you work on two events at once? What ensures you don't miss events?"
- **Expected derivation**: Agent must answer that the harness dispatches exactly one event at a time per role (per-role in-flight queue — TC-P3). The Monitor tool detects the event, the agent reads its payload and processes it. Agent must NOT work on two events simultaneously — it processes one, closes it, then waits for the next dispatch. The harness queues subsequent events and delivers them one at a time.
- **Pass criteria**: Answer mentions single-event processing, harness queueing, and sequential dispatch. Must NOT say the agent picks from a list of events or processes events concurrently.
