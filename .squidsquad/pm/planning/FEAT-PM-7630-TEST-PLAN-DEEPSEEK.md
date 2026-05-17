Now I have all the information needed. Let me produce the comprehensive test plan.

```markdown
# FEAT-PM-7630-TEST-PLAN-DS Research — Event-Driven Agent Architecture Test Plan

## Summary

This document is the comprehensive test plan for FEAT-PM-7630, drawn from locked CONTEXT.md decisions, RESEARCH.md-validated gaps, GAP-REVIEW-confirmed race conditions and failure modes, and the actual codebase at `references/scripts/`. Every line number reference is verified against current code. The plan covers seven areas: Prerequisites (4 TCs for Phase 1.5 infrastructure), Phase 2 event wake/closure (8 TCs), Phase 3 template migration (3 TCs), Regression (3 TCs), Race Conditions (3 TCs), Windows-specific (4 TCs), and Failure Modes (3 TCs). All 28 test cases include preconditions, step-by-step instructions, expected results, and bash/python verification commands.

**Primary risks the tests must catch**: (1) event bus disk persistence silently losing events on restart (GAP-6, harness.py line 352 — in-memory deque only), (2) `_discover_port()` parent-dir walk failing for sibling clones (GAP unresolved, event_bus_reader.py lines 42-53), (3) `_update_agent_from_event` mutating AgentState outside the lock (RACE-3, harness.py lines 737-757), (4) Windows terminal PID tracking being impossible with current `wt.exe new-tab` spawn (boot_remote.py line 395-417), (5) the closure API crash window where events replay as duplicates (RACE-5, cycle_post.py lines 588-630 pattern).

**The zero-gap gate applies**: any TC failure sends work back to dev. No "noted for follow-up" exceptions.

## Vault Context

- **BRIEFING.md priorities**: #7630 is the active top priority — "next major architectural shift — all mechanical cycle steps move to harness." Supersedes #6056, #5775, #5613.
- **Related decisions**: [[decision-cycle-runner-architecture]] — #2057 split mechanical/creative; #7630 completes the transfer. [[decision-clone-isolation-architecture]] — agents in sibling clones, not children; test TC-P2 validates port discovery for this. [[decision-pid-primary-liveness]] — OS-level PID checks preferred; tests use `os.kill(pid, 0)` pattern.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — all cycle orchestration prose becomes harness code. [[pattern-windows-utf8-subprocess]] — subprocess encoding handling applies to new spawn paths.
- **Human preferences**: "Cyclic/mechanical agent work must be programmatic, not LLM-interpreted prose." Context pressure threshold: 70%. "Systems should self-heal: detect stuck states → unstick immediately." Prefers direct/mechanical checks over indirect state files. Primary platform: Windows 11.
- **Related learnings**: [[learning-atomic-migration-strategy]] — all templates, scripts, harness changes in one deploy. [[learning-commit-code-state-exclusion]] — original motivation for #2057.

## Impact Analysis

- **Files touched**: 30+ files (see RESEARCH.md lines 23-72 for full list). Core: `harness.py` (1415 lines → major expansion), `cycle_pre.py` (1058 lines → absorbed), `cycle_post.py` (746 lines → absorbed), `event_bus.py` (103 lines → new event types), `event_catalog.py` (216 lines → 10+ new event types), `boot_remote.py` (652 lines → terminal PID tracking), `thin_launcher.py` (117 lines → new boot prompt), 24 `includes.yml` files, 4+ `instructions.md` files, 6 sub-skills rewritten or removed.
- **Behavior changes**: 9 major shifts (RESEARCH.md lines 76-93): agent activation, mechanical ops ownership, cycle concept elimination, stop mechanism, improvement scanning, terminal cleanup, context pressure management, git operations, status bar.
- **Dependencies**: FastAPI+uvicorn (existing), Claude Code v2.1.98+ (critical new dependency for Monitor tool, unvalidated), possible new `event_store.py` for disk persistence.

## Side Effects

- **Risk 1**: Monitor tool unvalidated — entire wake model lock depends on infrastructure that doesn't exist in installed Claude Code v2.1.86 — Severity: H — Mitigation: human must upgrade and validate before Phase 2 TC execution; TC-2-01 precondition includes "Claude Code upgraded to v2.1.98+. Monitor tool validated."
- **Risk 2**: Event closure API undefined — zero code for `POST /events/{id}/complete` — Severity: H — Mitigation: TC-2-02 defines and validates the payload schema before any other Phase 2 TCs can run.

## Edge Cases

- **Zero events on first boot**: Agent sits idle — must not appear stalled. Harness must emit `agent-ready` or equivalent. Captured in TC-2-01 preconditions: agent idle waiting for first event.
- **Event arrives while agent closing previous**: Agent mid-POST when new event queued. Harness per-role in-flight queue (TC-P3) ensures only one event dispatched at a time.
- **Human sends message mid-event**: Human input must become a `human-input-received` event — new event source not in current event_catalog.py RECOGNIZED tier (lines 91-117). Covered in comprehension question CQ-1 (agent must understand the event-driven wake mechanism).
- **Mixed-mode team**: PM event-driven but dev on cycles — cross-role detection warning. Covered in TC-R02.
- **Config flag `event-driven: no` while old cycle code removed from templates**: Old scripts must remain in codebase. Covered in TC-R01 and Regression Risks item 1.

## Integration Risks

- **Tracker comment dedup by event_id**: Without GAP-7 fix, re-emitted events post duplicate comments. TC-2-05 verifies at-most-once or idempotent behavior. tracker.py `comment()` (line 1069) currently has no `event_id` parameter.
- **Compose-completed → reboot race**: harness.py `_do_merge` (line 1147) emits compose-completed before `_reboot_affected_agents` (line 1156). If agent wakes on compose-completed before reboot, reads stale templates. TC-RC02 (not TC-RC02 — this is separate) — covered in Race Conditions section.
- **Status bar redesign**: statusline.sh lines 88-119 use `current-state` file mtime for cycle timer. With cycles eliminated, status bar display may break. Noted in Regression Risks as known degraded-display risk (statusline.sh updates out of scope per CONTEXT.md).
- **health_check.py legacy fallback**: harness.py `update_health()` lines 201-214 use health_check.py as fallback. With event-driven, this should be fully removed. Regression risk — TC-R01 must confirm no false-positive health signals.

## Upgrade & Migration

- **New config values**:
  - `event-driven: yes/no` (default `no`, must be explicitly set to `yes`)
  - `scan-idle-timeout: 10` (minutes, default `10`)
  - `wake-mechanism: monitor` (default `monitor`; future `spawn` fallback)
  - All added to `config.py` FIELD_MAP (lines 38-95)
- **New files**:
  - `references/sub-skills/common/event-driven-workflow.md`
  - Possibly `references/scripts/event_store.py`
  - Possibly `references/scripts/watcher.sh` (Monitor tool bridge)
  - New fields in `.squidsquad/.harness-state.json`
- **Template changes**: 24 includes.yml files remove `common/cycle-runner`, `common/context-pressure`, `common/self-restart`, `common/interval-sync`. 4+ instructions.md files strip ~60% content. New `event-driven-workflow.md` sub-skill added. All changes atomic — one `compose.py deploy-all`.
- **Upgrade steps**:
  1. Human upgrades Claude Code to v2.1.98+ and validates Monitor tool API
  2. Set `event-driven: yes` in config.md
  3. Set `wake-mechanism: monitor` and `scan-idle-timeout: 10`
  4. Run `python references/scripts/compose.py deploy-all`
  5. Restart harness
  6. Harness detects `event-driven: yes` and switches to event-driven mode
  7. Agents boot with new templates
  8. Monitor tool watches event bus; agents process events as they arrive
- **Graceful degradation**: When `event-driven: no` (default), existing cycle model runs unchanged. Both models cannot run simultaneously for same role — mixed-mode warning (TC-R02). Rollback: set `event-driven: no`, `compose.py deploy-all`, restart harness.

## Open Questions

- **Q1**: Does Monitor tool exist and work as assumed? — **Why**: The entire wake model lock (Persistent session + Monitor tool) depends on this. Before Phase 2 TCs can run, human must upgrade Claude Code to v2.1.98+ and validate against the Monitor Tool Validation Checklist (CONTEXT.md lines 76-81). If Monitor tool fails, the test plan must be revised to stateless spawn (PHASE2-PREP Option A).
- **Q2**: At-most-once vs at-least-once for event closure? — **Why**: TC-2-05 (harness crash during closure) verification depends on which atomicity contract is chosen. If at-most-once, test must verify NO duplicate work. If at-least-once, test must verify ALL work is idempotent (no double transitions, no double comments).
- **Q3**: How does the closure API payload schema preserve role-specific extras? — **Why**: cycle-runner.md lines 73-92 define role-specific extras (code_commit, pr_actions, vault_writes, version_bump, human_input_processed, issues_filed, etc.). TC-2-02 must validate that the closure API processes ALL these fields without loss. If the schema doesn't capture them, role-specific business logic is lost.

## Recommendation

**Feasible with caveats.** The test plan below is comprehensive and executable, but Phase 2 TCs (TC-2-01 through TC-2-08) are blocked on two prerequisites: (a) Monitor tool validation (human upgrade to Claude Code v2.1.98+), and (b) event closure API design (payload schema + atomicity contract). Phase 1.5 prerequisite tests (TC-P1 through TC-P4) can execute immediately — they test infrastructure that benefits both old and new models. Phase 3 and Regression tests can also execute independently once template migration is complete.

---

# TEST PLAN

---

## Smoke Tests

Quick go/no-go checks before full TC execution. All must pass before investing in deep TC runs.

- [ ] Harness starts without error: `python references/scripts/harness.py` runs stably with no traceback.
- [ ] `GET /health` returns 200 OK within 2 seconds of harness start.
- [ ] `GET /events` returns 200 OK with a JSON list (empty list is acceptable).
- [ ] `POST /events` with a minimal payload returns 200 OK and a valid event ID.
- [ ] `.harness-state.json` exists and contains `in_flight_events` and `last_event_completed` fields after harness starts.
- [ ] `compose.py deploy-all` exits 0 with `event-driven: yes` config.
- [ ] Composed `pm/CLAUDE.md` does not contain `/loop` after deploy-all.
- [ ] Composed `pm/CLAUDE.md` does contain `event-driven-workflow` content after deploy-all.
- [ ] `event_bus_reader.py` `_discover_port()` returns non-None when called from within a sibling clone (requires TC-P2 environment).
- [ ] `start_team.py --stop pm` completes within 30 seconds with no hanging process.

---

## (1) Prerequisites — Phase 1.5 Infrastructure

### TC-P1: Event Bus Disk Persistence Survives Harness Restart

- **Precondition**: Harness running with `event-driven: yes`. At least one event emitted and stored (e.g., `scan-due` for pm role). Event visible via `GET /events`. Event bus has disk-persistent storage backend (dev-chosen: file-per-event, append-only log, or SQLite per CONTEXT.md dev discretion line 47). `EventStream` in harness.py (line 348-384) backed by persistent store rather than pure in-memory deque.
- **Steps**:
  1. Record the event ID from `GET /events`: `curl -s http://localhost:<PORT>/events | python -c "import sys,json; evts=json.load(sys.stdin); print(evts[0]['id'] if evts else 'NO_EVENTS')"`. Store as `$EVENT_ID`.
  2. Hard-kill the harness process (`taskkill /F /PID <harness_pid>` on Windows, `kill -9` on Unix).
  3. Confirm harness is dead: `tasklist /FI "PID eq <harness_pid>"` (Windows) or `kill -0 <harness_pid>` (Unix) — should report not found.
  4. Restart harness: `python references/scripts/harness.py`.
  5. Wait for harness to finish `deferred_init` (watch for "Auto-starting all agents..." and "Port file distributed" log lines — harness.py lines 450-491).
  6. Query `GET /events` again.
- **Expected**: The previously stored event is still present in the event list with the same ID and payload. No data loss from the kill-and-restart. Event status preserved (if the event was `dispatched`, it should still be `dispatched` or `abandoned` — not gone).
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

- **Precondition**: Primary repo at known path (e.g., `D:\Dev\Dev\SquidSquad`). A clone exists as a sibling directory (e.g., `D:\Dev\Dev\SquidSquad-skill` or equivalent sibling path). Harness running in primary repo. `deferred_init` has completed and distributed `.harness-port` file into clone's `.squidsquad/` directory (harness.py lines 450-464).
- **Steps**:
  1. Verify harness distributed the port file: `cat <clone_root>/.squidsquad/.harness-port` — should contain the harness port number.
  2. From the clone directory, run a short test to invoke `_discover_port()`:
     ```python
     import sys; sys.path.insert(0, '<primary_repo>/references/scripts')
     from event_bus_reader import EventBusReader
     r = EventBusReader(role='skill')
     print(r._discover_port())
     ```
     (Note: `EventBusReader` expects `REPO_ROOT` derived from `SCRIPT_DIR.parent.parent` — for clone testing, may need to set `REPO_ROOT` to clone path or test `event_bus._discover_port()` directly.)
  3. Using discovered port, query `GET /events`.
- **Expected**: Port is discovered (non-None value returned). `GET /events` returns 200 OK with JSON list (empty or populated). Agent in clone can successfully reach the harness event bus. No silent `[]` return from `event_bus_reader.query()` (line 89 fallthrough).
- **Verification**:
  ```bash
  # From clone directory
  cd <clone_root>
  python -c "
  import sys, json, urllib.request
  # Direct test of _discover_port logic matching both event_bus.py and event_bus_reader.py
  from pathlib import Path
  squid_dir = Path('.').resolve() / '.squidsquad'
  port_file = squid_dir / '.harness-port'
  port = None
  if port_file.exists():
      port = int(port_file.read_text(encoding='utf-8').strip())
  else:
      # Parent walk — check up to 5 levels
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
  # Try to reach harness
  url = f'http://127.0.0.1:{port}/events?limit=1'
  resp = urllib.request.urlopen(url, timeout=2)
  data = json.loads(resp.read().decode('utf-8'))
  print(f'Response OK — {len(data.get(\"events\", []))} events returned')
  print('PASS')
  "
  ```
- **Regression signal**: If `_discover_port` returns `None`, the direct-path check (harness port distribution) or parent-walk fix for sibling clones did not land correctly. Check that `deferred_init` actually wrote the port file into the clone's `.squidsquad/` directory.

---

### TC-P3: Per-Role In-Flight Event Queue Prevents Double-Dispatch

- **Precondition**: Harness running with `event-driven: yes`. Per-role in-flight tracking exists — `in_flight_events` dict in `HarnessState` or `.harness-state.json`. One event dispatched to PM role but not yet closed (simulate by having the agent not respond or by injecting state directly).
- **Steps**:
  1. Emit an event targeted at the `pm` role and confirm it enters `in_flight_events["pm"]` in `.harness-state.json`.
  2. Attempt to emit a second event to the same `pm` role — trigger the idle-check timer or post another event via API.
  3. Inspect the event bus and harness state.
- **Expected**: The second event is NOT dispatched while the first is unclosed. It is either queued internally (visible in a `pending` queue per role) or emission is skipped with a log message. Only one event per role is in-flight at any time. The `in_flight_events["pm"]` field in `.harness-state.json` contains exactly one event ID.
- **Verification**:
  ```bash
  # Inspect harness state file
  python -c "
  import json
  state = json.load(open('.squidsquad/.harness-state.json'))
  in_flight = state.get('in_flight_events', {})
  print('In-flight events:', in_flight)
  assert isinstance(in_flight, dict), 'FAIL: in_flight_events not present or not dict'
  "
  # Confirm event bus doesn't contain two dispatched events for same role
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  pm_evts = [e for e in evts if e.get('role') == 'pm' and e.get('status') == 'dispatched']
  print('PM in-flight count:', len(pm_evts))
  assert len(pm_evts) <= 1, f'FAIL: {len(pm_evts)} dispatched events for pm — double dispatch'
  print('PASS')
  "
  ```

---

### TC-P4: Harness Thread Safety Under Concurrent Event and Health Polling

- **Precondition**: Harness running. Multiple roles active. Health polling thread running at 5-second interval (harness.py line 44: `HEALTH_POLL_INTERVAL = 5`). Event receiver endpoint active. `_update_agent_from_event` (harness.py lines 737-757) and `update_health` (lines 155-262) are both thread-safe after fix.
- **Steps**:
  1. Send 20 rapid `POST /events` requests concurrently (use `concurrent.futures.ThreadPoolExecutor`).
  2. Simultaneously, trigger 5 health poll calls to `GET /agents/{role}/health` from a separate thread.
  3. Let all calls complete. Check for exceptions in harness stdout/stderr.
  4. Inspect harness state for corruption.
- **Expected**: No `RuntimeError` about dictionary size change during iteration. No corrupted `AgentState` fields (e.g., `current_cycle` with mixed values). All 20 events stored correctly in event stream. Health responses return valid data. Harness process alive and responsive after test.
- **Verification**:
  ```bash
  python -c "
  import concurrent.futures, requests, time, json
  
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
  
  print(f'POST failures: {len(post_fails)}/{len(post_codes)}')
  print(f'Health failures: {len(health_fails)}/{len(health_results)}')
  
  # Also verify event count
  evts = requests.get(f'{BASE}/events').json()
  test_evts = [e for e in evts if e.get('event_type') == 'test-thread']
  print(f'Test events stored: {len(test_evts)}')
  
  if not post_fails and not health_fails and len(test_evts) >= 20:
      print('PASS')
  else:
      print('FAIL')
  "
  # Also check harness logs for RuntimeError or lock contention
  ```

---

## (2) Phase 2 — Event Wake and Closure

### TC-2-01: Happy Path — Full Event Lifecycle (Event → Wake → Work → Close)

- **Precondition**: `event-driven: yes` in config.md. Claude Code upgraded to v2.1.98+. Monitor tool validated per CONTEXT.md checklist (lines 76-81). Harness running. PM agent running with event-driven template (no `/loop`). Agent is idle, Monitor tool watching event bus. `POST /events/{id}/complete` endpoint implemented.
- **Steps**:
  1. Trigger an event emission by harness — either wait 10 minutes for `scan-due` (per scan-idle-timeout), or manually emit a `work-available` event via `POST /events`:
     ```json
     {"event_type": "scan-due", "role": "pm", "payload": {"reason": "idle-timeout", "scan_targets": ["vault", "pipeline"]}}
     ```
  2. Observe that Monitor tool detects the event — agent session wakes (visible in agent terminal or agent log).
  3. Agent reads event context from the event payload.
  4. Agent performs creative work (e.g., improvement scan for `scan-due` type).
  5. Agent posts `POST /events/{event_id}/complete` with a valid result payload (see TC-2-02 for schema).
  6. Harness processes the closure callback: executes status transitions, tracker comments, git commit/push.
  7. Harness marks the event as `closed`.
- **Expected**: Event transitions from `dispatched` → `closed`. Harness executes all side effects specified in closure payload. Agent returns to idle state. `in_flight_events["pm"]` cleared. Event status in event bus is `closed`.
- **Verification**:
  ```bash
  # Check event state after closure
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
  # Verify git commit exists
  git log --oneline -3
  # Verify no in-flight events remain for pm
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

### TC-2-02: Event Closure API Returns Structured Result — Full Payload Contract

- **Precondition**: Harness running with `event-driven: yes`. A `work-available` event has been dispatched to the `pm` role (event_id known). `POST /events/{id}/complete` endpoint implemented. The closure API payload schema defined (preserves all role-specific extras from cycle-runner.md lines 73-92).
- **Steps**:
  1. POST to `POST /events/{event_id}/complete` with a full structured payload including all role-specific extras:
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
  2. Check harness HTTP response.
  3. Verify each field was acted upon by the harness.
- **Expected**:
  - HTTP response: 200 OK with the closed event record (including `status: "closed"`).
  - Tracker transition `#123 in-progress → pending-test` executed via `tracker.py transition`.
  - Tracker comment posted on `#123` with the message text.
  - Git commit created with provided commit message.
  - `working-state.md` updated in `.squidsquad/pm/working-state.md`.
  - Role-specific extras recorded (visible in closure event payload or harness log).
- **Verification**:
  ```bash
  # POST closure
  curl -s -X POST http://localhost:<PORT>/events/<EVENT_ID>/complete \
    -H "Content-Type: application/json" \
    -d @test_closure_payload.json | python -c "
  import sys, json
  resp = json.load(sys.stdin)
  print('Response status:', resp.get('status'))
  assert resp.get('status') == 'closed', f'FAIL: {resp}'
  print('PASS')
  "
  # Check tracker transition (if test issue exists)
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

- **Precondition**: `event-driven: yes`. Event-type-specific timeouts configured: short tasks (scan, comment) = 5 min, long tasks (implementation) = 60 min per CONTEXT.md (lines 86-87). A `scan-due` event (short task) has been dispatched to `pm`. Agent does NOT post closure (simulate: block agent or kill it before closure POST).
- **Steps**:
  1. Dispatch a `scan-due` event to pm. Record timestamp.
  2. Verify the event enters `in_flight_events["pm"]` with dispatch timestamp.
  3. Wait for the configured timeout (5 minutes for `scan-due` short task, or use a shorter test-only timeout if harness supports a config override for testing).
  4. Observe harness behavior at timeout.
- **Expected**: Harness detects unclosed event. Harness logs a diagnostic message (event type, role, elapsed time) to harness console. Harness action: if agent PID is still alive → re-emit event (or log warning); if agent PID is dead → mark event `abandoned` and trigger auto-reboot; if ambiguous → alert. No silent hang.
- **Verification**:
  ```bash
  # Check harness logs for timeout detection (stdout or .squidsquad/harness.log if implemented)
  # Look for diagnostic keywords
  grep -i "timeout\|unclosed\|abandoned\|event-timeout" .squidsquad/harness.log 2>/dev/null || echo "Check harness stdout for timeout messages"
  
  # Check event status after timeout
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

- **Precondition**: `event-driven: yes`. Agent running with a dispatched event in-flight. Agent PID tracked in `.harness-state.json` (field `claude_pid`, harness.py line 303).
- **Steps**:
  1. Dispatch a `work-available` event to the `pm` role. Confirm it appears in `in_flight_events["pm"]`.
  2. Hard-kill the agent process: `taskkill /F /PID <claude_pid>` (Windows) or `kill -9 <claude_pid>` (Unix).
  3. Wait one health poll cycle (5 seconds, harness.py line 44: `HEALTH_POLL_INTERVAL = 5`).
  4. Observe harness behavior: check logs, check agent status, check event bus.
- **Expected**: Harness detects agent death via PID check (`update_health()`, lines 155-262). Harness logs the crash. Agent `status` transitions to `stalled` or `stopped`. Agent `intent` set to `restarting` (auto-reboot, line 235-243). Harness re-emits the in-flight event (new event with same payload, or original event status set to `reemitted`). New agent instance starts (auto-booted) and receives the re-emitted event.
- **Verification**:
  ```bash
  # Verify harness detected death
  curl -s http://localhost:<PORT>/agents/pm | python -c "
  import sys, json
  a = json.load(sys.stdin)
  print('Status:', a.get('status'))
  print('Intent:', a.get('intent'))
  # After crash, should be 'stalled'/'stopped' with intent 'restarting'
  assert a.get('status') in ('stalled', 'stopped', 'starting'), f'FAIL: unexpected status {a.get(\"status\")}'
  "
  # Verify event was re-emitted
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  reemitted = [e for e in evts if e.get('status') == 'reemitted' or (e.get('payload', {}).get('original_event_id') == '<EVENT_ID>')]
  print('Re-emission candidates:', len(reemitted))
  assert len(reemitted) >= 1, 'FAIL: no re-emitted event found'
  print('PASS')
  "
  # Verify agent was auto-rebooted (new PID appears within 30s)
  sleep 30
  python -c "
  import json
  s = json.load(open('.squidsquad/.harness-state.json'))
  pm = s.get('agents', {}).get('pm', {})
  pid = pm.get('claude_pid')
  intent = pm.get('intent')
  print(f'New PID: {pid}, Intent: {intent}')
  assert pid is not None and intent == 'running', f'FAIL: agent not re-booted'
  print('PASS')
  "
  ```

---

### TC-2-05: Harness Crash During Closure Processing — Event Replays Without Duplicates

- **Precondition**: `event-driven: yes`. Agent has just posted `POST /events/{event_id}/complete`. Harness is mid-processing the closure callback. The atomicity contract (at-most-once or at-least-once with idempotency per CONTEXT.md lines 51, 86) is implemented.
- **Steps**:
  1. Set up test: dispatch event, have agent complete work and POST closure.
  2. Immediately hard-kill the harness process after it receives the closure POST but before it finishes persisting `status: closed` to disk. (This may require a test hook — e.g., a file `.delay-closure` that makes harness pause after receiving POST but before persisting, giving the tester time to kill.)
  3. Restart harness.
  4. Observe what harness does with the event on restart.
- **Expected (at-most-once model)**: Harness detects event was `closed` (persisted before side effects) → skips side effects. OR event was NOT persisted → replays but all side effects are idempotent (no duplicate tracker comments, no duplicate git commits).
- **Expected (at-least-once model)**: Harness replays the unclosed event. Side effects execute again. Because they are idempotent (tracker comments dedup by event_id per GAP-7, git commits idempotent if same tree), no duplicates appear.
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
  1. Verify no open issues for pm: `python references/scripts/tracker.py list-issues pm --status open` → empty (or check via GitHub Issues API).
  2. Confirm `last_event_completed["pm"]` is older than 10 minutes (inspect `.harness-state.json`).
  3. Wait for the harness idle-check thread to fire (within 30 seconds of the 10-minute mark, or trigger manually if harness has a test endpoint for idle-check).
  4. Inspect the event bus for a new `scan-due` event.
- **Expected**: Harness emits a `scan-due` event to the `pm` role. Event appears in `GET /events` with `event_type: "scan-due"` and `role: "pm"`. Event payload includes scan targets, quiet-cycle count, last scan timestamp.
- **Variation (issue gate active)**: Create an open issue assigned to pm. Reset `last_event_completed` older than 10 minutes. Expected: harness does NOT emit `scan-due`. Issue gate suppressed the scan.
- **Verification**:
  ```bash
  # Confirm scan-due event emitted
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
  # 1. Create test issue
  python references/scripts/tracker.py create-issue \
    --title "Test gate issue for TC-2-06" --body "Temporary — delete after test" \
    --role pm --severity low --reporter pm-lead
  # 2. Reset last_event_completed timestamp (manually set to old value in .harness-state.json)
  # 3. Wait for idle-check interval
  # 4. Confirm no new scan-due events (count unchanged from above)
  ```

---

### TC-2-07: stop-requested Event — Agent Detects, Checkpoints, Exits Cleanly

- **Precondition**: `event-driven: yes`. PM agent running (idle or mid-work). Monitor tool watching event bus. `stop-requested` event type exists in event bus and event_catalog.py.
- **Steps**:
  1. Trigger graceful stop via `python references/scripts/start_team.py --stop pm` (or `POST /agents/pm/stop` on harness API).
  2. Harness sets agent `intent=stopping` and emits `stop-requested` event on the event bus.
  3. Monitor tool detects the `stop-requested` event (same channel as work events).
  4. Agent reads the event.
  5. Agent checkpoints `working-state.md` with current state.
  6. Agent exits cleanly.
- **Expected**: Agent `working-state.md` updated (non-empty, timestamped checkpoint). Agent process exits (PID no longer alive). Harness transitions agent `intent` to `stopped` (harness.py lines 246-249: `INTENT_STOPPED`). No orphaned Claude Code process. No sentinel file needed — event bus is the unified stop channel.
- **Verification**:
  ```bash
  # Check working state was updated (non-empty, recent modification)
  cat .squidsquad/pm/working-state.md
  stat .squidsquad/pm/working-state.md  # check mtime is recent
  
  # Check agent PID is dead
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
      print('WARNING: PermissionError — may be alive under different user')
  "
  # Check harness intent
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

- **Precondition**: Windows platform. `event-driven: yes`. PM agent was spawned via `boot_remote.py` `_spawn_windows` (line 395-440). `terminal_pid` was captured at spawn and stored in `.harness-state.json` (new field `terminal_pid` in `AgentState` and state file — currently only `claude_pid` exists at harness.py line 303). Harness has platform-specific terminal close logic (Windows: `taskkill /PID <terminal_pid>`, Unix: `kill <terminal_pid>`).
- **Steps**:
  1. Boot a pm agent and confirm `terminal_pid` is populated in `.harness-state.json` for the pm agent.
     ```bash
     python -c "import json; s=json.load(open('.squidsquad/.harness-state.json')); print(s['agents']['pm'].get('terminal_pid'))"
     ```
  2. Issue a graceful stop: `python references/scripts/start_team.py --stop pm` (or harness API equivalent).
  3. Wait for agent to exit cleanly (TC-2-07 passes — intent transitions to `stopped`).
  4. Observe the terminal window.
- **Expected**: Terminal window closes — not just the Claude process inside it, but the terminal window itself. `terminal_pid` process no longer alive. No zombie terminal windows remaining on the desktop.
- **Verification**:
  ```bash
  python -c "
  import json, os, sys
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
      # On Windows, PermissionError may mean process not owned by us — use tasklist as secondary check
      import subprocess
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
- **Note on Windows feasibility**: `_spawn_windows` (boot_remote.py lines 395-440) currently uses `wt.exe new-tab` or `cmd /c start` — neither returns a terminal window PID. The `subprocess.Popen` (line 412) could return a PID but it's the `wt.exe` PID, not the terminal tab PID. The spawned python process is a child of `wt.exe`. This TC may need to be revised once the dev agent designs the actual terminal PID capture mechanism. The TC verifies the end state (window closed), not the specific capture method.

---

## (3) Phase 3 — Template Migration

### TC-3-01: Agents Boot Without /loop Command

- **Precondition**: `event-driven: yes`. All templates migrated (Phase 3 complete). `compose.py deploy-all` run successfully. Fresh agent session started (no prior context in the session). Monitor tool validated (or stateless spawn chosen).
- **Steps**:
  1. Boot a pm agent via `python references/scripts/start_team.py --role pm`.
  2. Observe the agent's startup behavior in its terminal window.
  3. Wait 30 seconds for any `/loop` invocation that might occur.
- **Expected**: Agent boots and enters idle state without invoking `/loop`. No `/loop` command appears in the session. Agent is awake and waiting for events via Monitor tool (or exits after work if stateless spawn). Terminal shows event-driven orientation message (replacing "Boot. Begin your first Ralph Loop cycle now." from thin_launcher.py line 86).
- **Verification**:
  - Review agent terminal output: no `/loop 30m` or `/loop` invocation present.
  - Check agent's startup prompt — confirm it no longer contains "Boot. Begin your first Ralph Loop cycle now."
  - Agent is alive (PID in `.harness-state.json`) and health status is `running`.
  ```bash
  curl -s http://localhost:<PORT>/agents/pm | python -c "
  import sys, json
  a = json.load(sys.stdin)
  print('Health status:', a.get('health_status', a.get('status')))
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
- **Expected**: None of the following patterns appear in composed output for any role:
  - `/loop` invocation
  - `cycle_pre.py` references
  - `cycle_post.py` references
  - `cycle-input.json` read instructions
  - `cycle-output.json` write instructions
  - "Ralph Loop" phase descriptions ("Phase 1 — Pre-Cycle", "Phase 2 — Creative Work", "Phase 3 — Post-Cycle")
  - `iter-N.md` iteration log references
  - `current-state` file write instructions (cycle-based phase writes)
  - `cycle_number` field references
  - `quiet-cycle` concept
- **Verification**:
  ```bash
  # Check composed CLAUDE.md files for banned patterns
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

- **Precondition**: Phase 3 source changes complete. Cycle-related includes removed from all 24 `includes.yml` files (see pm/includes.yml lines 4-30 for current includes — `common/cycle-runner` at line 4, `common/context-pressure` at line 6, `common/self-restart` at line 29 must all be removed). New `event-driven-workflow.md` sub-skill created at `references/sub-skills/common/event-driven-workflow.md`.
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
  
  # Verify event-driven-workflow content present in all roles
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
  
  # Verify removed sub-skills absent from all composed files
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

## (4) Regression Tests

### TC-R01: event-driven: no Preserves Full Cycle Model Unchanged

- **Precondition**: `event-driven: no` in config.md (default). All #7630 code changes present but gated behind the flag. cycle_pre.py and cycle_post.py still present at `references/scripts/`. Old template includes still present in source (not removed — gated by config flag during compose).
- **Steps**:
  1. Verify config: `python references/scripts/config.py get event-driven` → should output `no` (or empty, which evaluates to false).
  2. Run `compose.py deploy-all` — should produce cycle-model CLAUDE.md files (with `/loop`, cycle-runner, etc.).
  3. Boot a pm agent normally: `python references/scripts/start_team.py --role pm`.
  4. Observe the agent invokes `/loop [INTERVAL]m`.
  5. Wait for one complete cycle (cycle_pre.py → creative work → cycle_post.py).
  6. Verify cycle_input.json written.
  7. Verify cycle_output.json consumed.
  8. Verify iteration log written (`iter-N.md` in `.squidsquad/pm/iterations/`).
  9. Verify git commit produced.
- **Expected**: Full existing cycle model functions without degradation. All cycle_pre/cycle_post operations complete. No event-driven behavior activates. No errors related to missing event-driven infrastructure. `/loop` works as before.
- **Verification**:
  ```bash
  # Verify config
  python references/scripts/config.py get event-driven
  # Expected: no (or empty)
  
  # Verify cycle artifacts after one cycle
  ls -la .squidsquad/pm/cycle-input.json
  ls -la .squidsquad/pm/cycle-output.json
  ls -la .squidsquad/pm/iterations/
  git log --oneline -1  # should show cycle commit
  
  # Verify agent health
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

- **Precondition**: `event-driven: yes` for pm role. `event-driven: no` (or not set) for skill role. (Config flag is per-instance/config.md — if it's a single global flag, this test evolves to: "config says event-driven: no but a role somehow has event-driven template" or vice versa. The warning should fire if harness detects mismatched intent/config across roles.)
- **Steps**:
  1. Set config so one role is event-driven and another is cycle-based (exact mechanism depends on implementation — per CONTEXT.md line 62: "Both models cannot run simultaneously for the same role" implying per-role gating is possible).
  2. Start harness: `python references/scripts/harness.py`.
  3. Check harness startup output (stdout) and logs.
- **Expected**: Harness prints a visible warning that roles are running in mixed mode (some event-driven, some cycle-based). Warning identifies which roles are in which mode. Harness still starts (does not abort — warning only). The warning must be prominent enough to be noticed (not buried in debug output).
- **Verification**:
  ```bash
  python references/scripts/harness.py 2>&1 | grep -i "mixed\|warning\|event-driven.*no\|cycle.*event"
  # At least one warning line expected
  # If the above grep returns empty: FAIL
  ```

---

### TC-R03: Existing Tracker Transitions Work Through Closure API

- **Precondition**: `event-driven: yes`. A real GitHub Issue exists at a known status (e.g., `#42` at `in-progress`). Closure API fully implemented. tracker.py `transition()` function unchanged in its interface.
- **Steps**:
  1. POST to `POST /events/{event_id}/complete` with a status transition payload:
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
  2. Harness processes closure, calls `tracker.py transition 42 in-progress pending-test --role pm-lead`.
  3. Verify the transition succeeded and comment was posted.
- **Expected**: Issue `#42` transitions from `in-progress` to `pending-test` exactly as if `tracker.py transition` was called directly. Comment posted with correct content. No difference in behavior from direct `tracker.py` calls — the closure API is a pass-through to the same tracker functions.
- **Verification**:
  ```bash
  python references/scripts/tracker.py get-labels 42
  # Expected: status:pending-test label present
  
  gh issue view 42 --json labels --jq '[.labels[].name] | sort'
  
  gh issue view 42 --json comments --jq '.comments[-1].body'
  # Expected: contains "Verified via event closure API"
  
  # Revert issue to in-progress for cleanup
  python references/scripts/tracker.py transition 42 pending-test in-progress --role pm-lead
  ```

---

## (5) Race Conditions from RESEARCH.md

### TC-RC01: Startup Race — Agents Don't POST Before Server Ready

- **Precondition**: `event-driven: yes`. Fresh harness start. Agents configured to auto-boot via `deferred_init` (harness.py lines 474-491). The fix from RESEARCH.md RACE-1 is in place: either server accepts connections before agents are spawned (reorder in lifespan, harness.py lines 406-495), or agent closure POST includes retry logic.
- **Steps**:
  1. Start harness with timing instrumentation.
  2. Monitor for any `POST /events/{id}/complete` or `POST /events` calls made before the harness FastAPI server is fully accepting connections (before `yield` at harness.py line 495).
  3. Observe agent behavior on startup.
- **Expected**: No agent POST attempts before server is ready. Either: (a) agent spawn is delayed until after `yield` (server ready), or (b) agent closure POST retries with backoff on connection-refused/503. No events lost due to startup timing.
- **Verification**:
  ```bash
  python -c "
  import subprocess, time, requests
  
  t0 = time.time()
  proc = subprocess.Popen(
      ['python', 'references/scripts/harness.py'],
      stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
      text=True
  )
  
  # Poll for server readiness
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
  
  # Read harness output for agent spawn timing
  import threading
  lines = []
  def reader():
      for line in proc.stdout:
          lines.append(line)
  t = threading.Thread(target=reader, daemon=True)
  t.start()
  time.sleep(5)
  
  # Check for errors
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

- **Precondition**: Harness running. Event emission working. The two ID generation schemes — `event_bus.py _generate_id` (line 58-61: SHA256 hash → 8-char hex) and `harness.py _emit_event` (line 1015-1021: `os.urandom(4).hex()` → 8 hex chars) — have been unified to one scheme with sufficient entropy (at least 12 hex chars, per RESEARCH.md RACE-4).
- **Steps**:
  1. Emit 1,000 events rapidly via concurrent `POST /events` calls.
  2. Retrieve all events via `GET /events`.
  3. Check for duplicate event IDs.
- **Expected**: All 1,000 events have unique IDs. No collisions. The unified ID generation scheme produces no duplicates at this volume. Even with 4 bytes of randomness, birthday collision at ~65K events means 1K is well within safe range, but the unified scheme should use more entropy for long-running safety.
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
          return r.status_code
      except Exception:
          return 0
  
  with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
      codes = list(ex.map(emit, range(1000)))
  
  ok_count = sum(1 for c in codes if c == 200)
  print(f'Successful emissions: {ok_count}/1000')
  
  # Now check uniqueness
  evts = requests.get(f'{BASE}/events?limit=2000', timeout=5).json()
  test_evts = [e for e in evts if e.get('event_type') == 'test-collision']
  ids = [e['id'] for e in test_evts]
  unique_ids = len(set(ids))
  print(f'Emitted: {len(ids)}, Unique IDs: {unique_ids}')
  
  if unique_ids == len(ids):
      print('PASS')
  else:
      print(f'FAIL: {len(ids) - unique_ids} collisions detected')
      from collections import Counter
      dupes = [id for id, cnt in Counter(ids).items() if cnt > 1]
      print(f'Duplicate IDs: {dupes[:5]}')
  "
  ```

---

### TC-RC03: Shutdown — In-Flight Events Marked Abandoned

- **Precondition**: `event-driven: yes`. At least one event is in-flight (dispatched, not closed) for the pm role. `in_flight_events["pm"]` is populated in harness state.
- **Steps**:
  1. Dispatch an event to pm. Confirm it is in-flight (agent does not close it — agent is alive but not responding, or agent was killed).
  2. Trigger harness shutdown via Ctrl+C (harness.py lines 1294-1355: Ctrl+C escalation) or `POST /shutdown` (line 926).
  3. Wait for harness to fully shut down. Observe shutdown log output.
  4. Restart harness.
  5. Inspect event status in the restored event bus.
- **Expected**: On shutdown, harness marks all in-flight events as `abandoned` before exiting (or during load_state on restart). On restart, harness does NOT automatically re-emit `abandoned` events — they are stale and require human or harness logic decision. The abandoned status is visible in event metadata. No silent event loss — the event is still in the persistent store with `abandoned` status.
- **Verification**:
  ```bash
  # After restart, check for abandoned events
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  abandoned = [e for e in evts if e.get('status') == 'abandoned']
  print('Abandoned events:', len(abandoned))
  for a in abandoned:
      print(f'  ID: {a[\"id\"]}, type: {a.get(\"event_type\")}, role: {a.get(\"role\")}')
  # Expect at least the in-flight event to be marked abandoned
  print('PASS' if abandoned else 'WARNING: no abandoned events — event may have been silently lost')
  "
  
  # Verify the abandoned event was NOT re-emitted (no new dispatched event with same payload)
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  dispatched = [e for e in evts if e.get('status') == 'dispatched' and e.get('role') == 'pm']
  print(f'Dispatched events for pm after restart: {len(dispatched)}')
  # If auto-replay of abandoned events is NOT the design, should be 0
  "
  ```

---

## (6) Windows-Specific Tests

### TC-WIN01: File Locking on Context-Pressure Reads — No PermissionError

- **Precondition**: Windows platform. Harness running. An agent (or statusline.sh) actively writing context-pressure files via atomic `.tmp` → `mv` pattern (statusline.sh line 72). Harness reading context-pressure via `Path.read_text()` (harness.py line 704-708: `SQUIDSQUAD_DIR / role / "context-pressure"`).
- **Steps**:
  1. Simulate high-frequency context-pressure writes: run a loop that rapidly writes to `.squidsquad/pm/context-pressure` (atomic `.tmp` → `mv`).
  2. Simultaneously, repeatedly query `GET /agents/pm/health` from harness.
  3. Run for 60 seconds.
  4. Check harness output for `PermissionError`, `OSError`, or file-read failures.
- **Expected**: No file locking exceptions. Harness reads either old data (before write) or new data (after write) but never crashes. If a `PermissionError` occurs, the harness `try/except OSError` block at harness.py line 707-708 handles it gracefully (returns `context_pressure: None`).
- **Verification**:
  ```bash
  # In one terminal: rapid context-pressure writes
  python -c "
  import time, tempfile, os
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
  
  # Check harness stdout for any tracebacks or OSError
  # Expected: no tracebacks, no PermissionError, no crashes
  ```

---

### TC-WIN02: PID Reuse — Harness Detects Agent Death Despite Fast PID Recycle

- **Precondition**: Windows platform. Harness running with health polling at 5-second intervals. Agent PID tracked in `.harness-state.json` (harness.py line 303: `claude_pid`). Process start time or process name also stored for disambiguation (per RESEARCH.md Windows-Specific Risks: "store process start time alongside PID for disambiguation").
- **Steps**:
  1. Boot an agent and record its PID and process start time.
  2. Kill the agent (`taskkill /F /PID <pid>`).
  3. Simulate a new process reusing the same PID (difficult to orchestrate naturally; use a test harness that checks harness behavior when PID is alive but process name is wrong).
  4. Wait one health poll cycle (5s).
  5. Check harness's detection.
- **Expected**: Harness detects the original agent is dead — even if PID is reused. Uses secondary factor (process name via `tasklist /FI "PID eq <pid>" /FO CSV`, or process start time comparison) to disambiguate. If PID is alive but process name does not match expected (e.g., not `claude` or `node`), harness marks agent as `stalled` and triggers reboot.
- **Verification**:
  ```bash
  python -c "
  import json, subprocess, os, time
  
  # Read agent PID
  state = json.load(open('.squidsquad/.harness-state.json'))
  pid = state.get('agents', {}).get('pm', {}).get('claude_pid')
  print(f'Agent PID: {pid}')
  
  # Kill agent
  os.kill(pid, 9)  # SIGKILL — will fail on Windows, use variant
  # On Windows:
  subprocess.run(['taskkill', '/F', '/PID', str(pid)], capture_output=True)
  
  # Wait for health poll
  time.sleep(7)
  
  # Check harness state
  state2 = json.load(open('.squidsquad/.harness-state.json'))
  pm2 = state2.get('agents', {}).get('pm', {})
  status = pm2.get('status')
  intent = pm2.get('intent')
  print(f'After death — status: {status}, intent: {intent}')
  assert status != 'running', f'FAIL: agent still marked running after kill'
  print('PASS' if status != 'running' else 'FAIL')
  "
  ```

---

### TC-WIN03: Terminal PID Tracking — PID Captured at Spawn

- **Precondition**: Windows platform. `boot_remote.py` `_spawn_windows` (lines 395-440) modified to capture and return the terminal PID alongside the agent PID. `thin_launcher.py` (line 86: `Boot. Begin your first Ralph Loop cycle now.`) modified to write terminal PID. `boot_remote.boot_agent()` returns `terminal_pid` in result dict.
- **Steps**:
  1. Boot a pm agent via `python references/scripts/start_team.py --role pm`.
  2. Immediately check `.harness-state.json` for `terminal_pid` in the pm agent's entry.
  3. Verify the `terminal_pid` is non-None and corresponds to a real process.
  4. On Windows, verify via `tasklist /FI "PID eq <terminal_pid>"` that the process is a terminal host (`conhost.exe`, `WindowsTerminal.exe`, or `wt.exe`).
- **Expected**: `terminal_pid` is captured and stored at spawn time. It is different from `claude_pid` (terminal window PID != Claude PID). The terminal PID corresponds to the actual window that the agent runs in.
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
  
  # Verify terminal PID exists
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

### TC-WIN04: Detached Process Stop Signal — stop-requested Event Works Without Signal

- **Precondition**: Windows platform. Agent spawned with `DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP` flags (boot_remote.py line 414). This means harvester cannot send SIGTERM or Ctrl+C to the agent process. The stop mechanism MUST be cooperative (event bus `stop-requested`) per Locked Decision #2.
- **Steps**:
  1. Boot a pm agent (detached process).
  2. Confirm agent is alive and processing events.
  3. Initiate graceful stop: `POST /agents/pm/stop` or `start_team.py --stop pm`.
  4. Harness emits `stop-requested` event on event bus.
  5. Monitor tool or agent internal logic detects the stop event.
  6. Wait for agent to exit (up to 30 seconds for checkpoint + exit).
- **Expected**: Agent detects `stop-requested` event (via Monitor tool watching event bus). Agent checkpoints and exits cleanly — no signal needed. Harness detects agent exit via PID check. No `taskkill /F` needed.
- **Verification**:
  ```bash
  # Trigger stop
  curl -s -X POST http://localhost:<PORT>/agents/pm/stop
  
  # Wait for agent to exit
  sleep 35
  
  # Check agent is dead
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
  # Confirm stop-requested event was consumed
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  stop_evts = [e for e in evts if e.get('event_type') == 'stop-requested' and e.get('role') == 'pm']
  print(f'stop-requested events: {len(stop_evts)}')
  "
  ```

---

## (7) Failure Mode Tests

### TC-FM01: Monitor Tool Disconnect/Reconnect — Events Not Lost

- **Precondition**: `event-driven: yes`. Persistent session + Monitor tool wake model. Agent running with Monitor tool watching event bus. Disk-persistent event bus (TC-P1 passes) so events survive reconnection gaps.
- **Steps**:
  1. Simulate Monitor tool disconnection — if Monitor tool has a timeout, wait for it to expire. Or temporarily block network access to harness port from agent.
  2. During the disconnection gap, emit 3 events to the agent's role via `POST /events`.
  3. Restore Monitor tool connection (or unblock network).
  4. Agent's Monitor tool reconnects.
  5. Agent queries `GET /events?since=<last_processed_event_id>`.
- **Expected**: All 3 events emitted during the disconnection gap are delivered to the agent when it reconnects. No events are silently lost. The disk-persistent event bus retains them. Agent processes them in order.
- **Verification**:
  ```bash
  # After reconnect, check agent processed all 3 events
  # Query event bus for closed events by this role
  curl -s http://localhost:<PORT>/events?event_type=test-disconnect | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  closed = [e for e in evts if e.get('status') == 'closed']
  print(f'Events closed after reconnection: {len(closed)}')
  assert len(closed) >= 3, f'FAIL: only {len(closed)}/3 events processed'
  print('PASS')
  "
  ```

---

### TC-FM02: Git Push Failure in Closure — Event Closure vs. Code Push Atomicity

- **Precondition**: `event-driven: yes`. A git remote that is temporarily unreachable (simulate by changing remote URL to a non-existent endpoint, or using a test repo where push fails). An event dispatched to an agent that would normally produce a commit+push.
- **Steps**:
  1. Configure remote to cause push failure (e.g., `git remote set-url origin http://127.0.0.1:1/fake`).
  2. Dispatch a `work-available` event to pm.
  3. Agent does work, posts closure with `commit_message`.
  4. Harness processes closure — attempts `git push`, push fails.
  5. Observe harness behavior.
- **Expected**: Harness logs the push failure. Event closure is either: (a) marked `closed-with-errors` (commit succeeded locally but push failed), or (b) event remains `dispatched` with error note and is retried. Harness does NOT silently mark event `closed` if push failed — the closure API contract requires commit AND push before event is truly closed per CONTEXT.md line 60: "Harness owns git commit/push." The error handling from cycle_post.py `_do_commit_push` (lines 297-412: branch workflow, "Nothing to commit" detection, push error handling) must be replicated.
- **Verification**:
  ```bash
  # Check event status
  curl -s http://localhost:<PORT>/events | python -c "
  import sys, json
  evts = json.load(sys.stdin)
  t = next((e for e in evts if e['id'] == '<EVENT_ID>'), None)
  print('Event status:', t.get('status'))
  if t.get('status') == 'closed':
      print('FAIL: event closed but push failed')
  elif t.get('status') in ('dispatched', 'error', 'closed-with-errors'):
      print('PASS: push failure captured in event status')
  "
  # Check harness logs for push failure
  # Restore remote after test
  git remote set-url origin <original_url>
  ```

---

### TC-FM03: Event Bus Overflow — Old Events Evicted Gracefully

- **Precondition**: Harness running. Event bus with a bounded size (1000 events if still using in-memory deque, or configurable limit if using disk persistence). Event volume high enough to approach the limit.
- **Steps**:
  1. Emit 1,200 events rapidly via `POST /events`.
  2. Query `GET /events` and check total event count.
  3. If using disk persistence, verify oldest events are archived/trimmed rather than silently lost. If still using in-memory deque (harness.py line 352: `maxlen=1000`), verify the oldest events are evicted.
  4. Query `GET /events?since=<old_event_id>` using an event ID that would have been evicted.
- **Expected**: Event bus handles overflow gracefully. Either: (a) with disk persistence, the limit is removed or raised significantly and all 1,200 events are stored, or (b) with bounded deque, oldest events are evicted but `get_since` handles evicted cursor gracefully (returns oldest available events with a warning, per harness.py lines 379-380: "ID not found (evicted) — return oldest available up to limit"). No crash, no corruption.
- **Verification**:
  ```bash
  # Emit 1200 events
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
  
  # Check total events
  python -c "
  import requests
  evts = requests.get('http://localhost:<PORT>/events?limit=2000', timeout=2).json()
  test_evts = [e for e in evts if e.get('event_type') == 'test-overflow']
  print(f'Test events stored: {len(test_evts)}')
  # With disk persistence: should be ~1200
  # With in-memory deque: should be 1000 (oldest 200 evicted)
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
  # Should return oldest available (not error, not empty)
  print('PASS' if len(evts) > 0 else 'FAIL: empty response on evicted cursor')
  "
  ```

---

## Regression Risks

Below are known risks that cannot be fully covered by test cases but must be monitored during QA:

- **cycle_pre/cycle_post scripts accidentally removed**: These scripts (`references/scripts/cycle_pre.py`, `references/scripts/cycle_post.py`) must remain present in the codebase even after template migration. If removed, agents running with `event-driven: no` will break with `FileNotFoundError`. TC-R01 partially covers this but a file-existence check should be added to smoke tests.
- **compose.py deploy-all race**: If `compose deploy-all` runs while an agent is mid-cycle reading its `CLAUDE.md`, the agent may read a partially-written file. The existing atomic write pattern (`.tmp` → `mv`) in compose output must be preserved. Not easily tested with an automated TC — requires manual race-condition-injection testing.
- **tracker.py comment dedup by event_id (GAP-7)**: Without the `event_id` parameter on `tracker.comment()` (line 1069), re-emitted events will post duplicate comments. TC-2-05 verifies at-most-once/idempotent behavior; if comments appear duplicated, GAP-7 is not fixed.
- **context-pressure path for clone agents (GAP-8)**: harness.py `GET /agents/{role}/health` (line 704) reads context-pressure from `SQUIDSQUAD_DIR / role / "context-pressure"` — this is the PRIMARY repo's path. For clone agents, statusline.sh writes to the clone's path. Harness reads the wrong file. If not fixed, harness may miss context pressure spikes for clone-based agents, leading to missed restarts. TC-WIN01 may inadvertently catch this if testing with a clone agent.
- **statusline.sh cycle-timer display**: statusline.sh lines 88-119 use `current-state` file mtime and `iter-N.md` files for cycle display. After Phase 3, these files won't be updated. Status bar may show stale/broken cycle timer. Noted as known degraded-display risk pending statusline.sh redesign (out of scope for this EPIC per CONTEXT.md line 97: "Vault protocol changes" out of scope, statusline not explicitly mentioned but is display infrastructure).
- **health_check.py legacy fallback**: harness.py `update_health()` lines 201-214 call `health_check.check_agent_health()` as fallback. With event-driven architecture, this should be fully removed. Under `event-driven: yes`, health_check.py must not produce false-positive health signals — TC-R01 should verify no `health_check.py` fallback runs in event-driven mode.
- **Per-event log format migration**: Historical `iter-N.md` files in `.squidsquad/<role>/iterations/` must coexist with new per-event log format. No migration path defined in TC — this is a documentation/discovery risk during QA.

---

## Comprehension Questions

These questions verify that a fresh agent, given only the migrated template files, can correctly derive the event-driven workflow. QA spawns a fresh subagent, provides only the listed files, and scores answers against expected derivations.

### CQ-1: How Does an Agent Wait for Work in Event-Driven Mode?

- **Files to provide**:
  - `.squidsquad/pm/CLAUDE.md` (composed output, post-migration — no `/loop`, no cycle prose)
  - `references/sub-skills/common/event-driven-workflow.md`
  - `references/sub-skills/common/agent-lifecycle.md` (rewritten for persistent session)
- **Question to ask fresh agent**: "You are a PM agent that has just booted. There is no `/loop` command and no `cycle_pre.py` to run. How do you wait for work to arrive? What tool or mechanism keeps you active between work items?"
- **Expected derivation**: Agent must answer that the Monitor tool (Claude Code v2.1.98+) watches the event bus for incoming events. The agent does not poll manually, does not sleep, and does not invoke `/loop`. The Monitor tool wakes the agent when an event with the agent's role arrives. The agent sits in an idle/persistent session state between events.
- **Pass criteria**: Answer mentions Monitor tool, event bus watching, and passive idle state. Answer must NOT mention `/loop`, `cycle_pre`, or manual polling.

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
- **Expected derivation**: Agent must answer: (1) checkpoint current working state to `working-state.md`, (2) if mid-event, attempt to post a partial closure or note the interruption, (3) exit the session cleanly. Agent must NOT attempt to ignore the event, defer it, or continue working. The `stop-requested` event is the unified stop channel — same Monitor tool that delivers work events also delivers the stop signal.
- **Pass criteria**: Answer includes checkpointing working state and clean exit. Answer must NOT say the agent polls a sentinel file or waits for `/loop` to end — the stop arrives via event bus, not via cycle end.

---

### CQ-4 (bonus): How Does the Agent Know Which Event to Process Next?

- **Files to provide**:
  - `.squidsquad/pm/CLAUDE.md` (composed output, post-migration)
  - `references/sub-skills/common/event-driven-workflow.md`
- **Question to ask fresh agent**: "Multiple events may arrive for your role over time. How do you know which event to process now? Can you work on two events at once? What ensures you don't miss events?"
- **Expected derivation**: Agent must answer that the harness dispatches exactly one event at a time per role (per-role in-flight queue). The Monitor tool detects the event, the agent reads its payload and processes it. Agent must NOT work on two events simultaneously — it processes one, closes it, then waits for the next dispatch. The harness queues subsequent events and delivers them one at a time.
- **Pass criteria**: Answer mentions single-event processing, harness queueing, and sequential dispatch. Must NOT say the agent picks from a list of events or processes events concurrently.

---

## Vault Candidates

- **Type**: learning — FEAT-PM-5613 already determined Monitor tool cannot replace /loop; #7630's locked decision ignored this finding — **Why**: Documents the risk of locking architecture decisions on unvalidated external dependencies. The Monitor tool research was done, concluded "no," but the lock happened anyway. Important for future decision-making discipline.
- **Type**: pattern — Atomic template migration at scale: 24 includes.yml + 4 instructions.md + 6 sub-skills + compose.py in one deploy — **Why**: Already established as [[learning-atomic-migration-strategy]] but worth reinforcing with this specific scale (30+ files, all roles, cross-cutting). The compose.py `deploy-all` command enables this but the coordination complexity is material.
- **Type**: learning — Event bus port discovery via parent-dir walk fails for sibling clones but harness port distribution mitigates this — **Why**: event_bus_reader.py `_discover_port` (line 42-53) has two paths: direct (works if harness distributed) and parent walk (fails for siblings). This is a latent architectural constraint. The harness distribution (harness.py lines 450-464) is a workaround, not a fix — any new event bus consumers must be aware of this limitation.
- **Type**: learning — cycle-output.json role-specific extras encode years of business logic that must survive architectural transitions — **Why**: code_commit, pr_actions, vault_writes, version_bump, human_input_processed, issues_filed (cycle-runner.md lines 73-92) are not incidental — they are the system's delivery contract. Any replacement must preserve them with fidelity. This learning applies to future architectural shifts.
```