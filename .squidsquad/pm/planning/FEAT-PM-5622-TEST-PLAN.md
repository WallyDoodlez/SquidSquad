# FEAT-PM-5622 Test Plan — Phase 4: Agent Communication Bus

## Test Cases

---

### TC-1: GET /events returns all events when no filters applied
- **Precondition**: Harness running with Phase 2 (#4709) shipped. At least 5 events in the deque (emitted via POST /events from multiple agents).
- **Steps**: `curl -s "http://localhost:7373/events"` — no query params.
- **Expected**: JSON array of up to `limit` events (default 50), each with fields: `id`, `event_type`, `role`, `timestamp`, `cycle_number`, `payload`, `received_at`.
- **Verification**: `python -c "import json,urllib.request; r=urllib.request.urlopen('http://localhost:7373/events'); data=json.load(r); assert len(data)>=1; assert all('received_at' in e for e in data)"` exits 0.

---

### TC-2: GET /events filters by role
- **Precondition**: Deque contains events from at least two different roles (e.g., `pm` and `skill`).
- **Steps**: `curl -s "http://localhost:7373/events?role=pm"`
- **Expected**: Response contains only events where `role == "pm"`. No skill or qa events appear.
- **Verification**: `python -c "import json,urllib.request; r=urllib.request.urlopen('http://localhost:7373/events?role=pm'); data=json.load(r); assert all(e['role']=='pm' for e in data), data"`

---

### TC-3: GET /events filters by event_type
- **Precondition**: Deque contains events of types `cycle-start`, `pr-merge`, and `cycle-end`.
- **Steps**: `curl -s "http://localhost:7373/events?event_type=pr-merge"`
- **Expected**: Response contains only events where `event_type == "pr-merge"`.
- **Verification**: `python -c "import json,urllib.request; r=urllib.request.urlopen('http://localhost:7373/events?event_type=pr-merge'); data=json.load(r); assert all(e['event_type']=='pr-merge' for e in data)"`

---

### TC-4: GET /events filters by since (cursor)
- **Precondition**: Deque has events with IDs `aaa00001`, `aaa00002`, `aaa00003`, `aaa00004`.
- **Steps**: `curl -s "http://localhost:7373/events?since=aaa00002"`
- **Expected**: Response contains only events with IDs strictly after `aaa00002` — i.e., `aaa00003` and `aaa00004`. The `since` event itself is excluded.
- **Verification**: `python -c "import json,urllib.request; r=urllib.request.urlopen('http://localhost:7373/events?since=aaa00002'); data=json.load(r); ids=[e['id'] for e in data]; assert 'aaa00002' not in ids; assert 'aaa00003' in ids"`

---

### TC-5: GET /events respects limit parameter
- **Precondition**: Deque has 200 events.
- **Steps**: `curl -s "http://localhost:7373/events?limit=10"`
- **Expected**: Response contains exactly 10 events (the most recent 10).
- **Verification**: `python -c "import json,urllib.request; r=urllib.request.urlopen('http://localhost:7373/events?limit=10'); data=json.load(r); assert len(data)==10, len(data)"`

---

### TC-6: GET /events combines filters (role + event_type + since + limit)
- **Precondition**: Deque has mixed events. Several `pm/cycle-start` events before and after a known cursor ID.
- **Steps**: `curl -s "http://localhost:7373/events?role=pm&event_type=cycle-start&since=<cursor_id>&limit=5"`
- **Expected**: Only `pm` events of type `cycle-start` that arrived after `<cursor_id>`, max 5 returned.
- **Verification**: Read response JSON; assert all `role=='pm'`, all `event_type=='cycle-start'`, all have position after `<cursor_id>` in deque, count <= 5.

---

### TC-7: Harness stamps received_at epoch on every event
- **Precondition**: Harness running. One event emitted via `POST /events`.
- **Steps**: Read the event back via `GET /events?limit=1`.
- **Expected**: Event object has `received_at` field containing a Unix epoch float (not the agent-supplied `timestamp`). Value is within 2 seconds of the wall clock at test time.
- **Verification**: `python -c "import json,urllib.request,time; r=urllib.request.urlopen('http://localhost:7373/events?limit=1'); e=json.load(r)[0]; assert abs(e['received_at']-time.time())<60"`

---

### TC-8: event_bus_reader.py queries harness and returns event list
- **Precondition**: `references/scripts/event_bus_reader.py` deployed. Harness running with several events in deque.
- **Steps**: `python -c "from event_bus_reader import query; events=query(role='pm'); print(len(events), events[0].keys())"`
- **Expected**: Returns a list of dicts. Each dict has `id`, `event_type`, `role`, `received_at` keys. No exception raised.
- **Verification**: Script exits 0 and prints a non-zero count with expected keys.

---

### TC-9: event_bus_reader.query() uses since parameter as cursor
- **Precondition**: Deque has 10 events. Last known event ID is `<cursor>`.
- **Steps**: `python -c "from event_bus_reader import query; events=query(role='pm', since='<cursor>'); print([e['id'] for e in events])"`
- **Expected**: Only events strictly after `<cursor>` are returned. The cursor event itself does not appear.
- **Verification**: Assert `<cursor>` not in returned IDs.

---

### TC-10: cycle_pre.py injects recent_events into cycle-input.json
- **Precondition**: Harness running with events in deque. Agent has `Last Processed Event ID: none` in `working-state.md`.
- **Steps**: `python references/scripts/cycle_pre.py pm` (full cycle_pre run for pm role).
- **Expected**: `.squidsquad/pm/cycle-input.json` contains a `recent_events` key whose value is a list (may be empty or populated). The key is present even if the list is empty.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert 'recent_events' in d, d.keys()"`

---

### TC-11: cycle_pre.py injects only role-relevant events
- **Precondition**: Deque has pm events and skill events. PM agent uses `PM_EVENT_TYPES` filter (e.g., `["pr-merge", "verification-failed"]`).
- **Steps**: Run `python references/scripts/cycle_pre.py pm`.
- **Expected**: `cycle-input.json` `recent_events` list contains only events matching PM's subscribed event types. skill-only events (e.g., `task-start`) do not appear.
- **Verification**: Read `cycle-input.json`; assert all `recent_events[*].event_type` are in PM's configured list.

---

### TC-12: Agent-side cursor advances after processing
- **Precondition**: Agent has `Last Processed Event ID: <old_id>` in `working-state.md`. New events exist beyond `<old_id>`.
- **Steps**: Run `python references/scripts/cycle_pre.py pm` followed by `python references/scripts/cycle_post.py pm`.
- **Expected**: After `cycle_post.py` completes, `.squidsquad/pm/working-state.md` has `Last Processed Event ID` updated to the ID of the most recent event processed this cycle (or unchanged if no new events).
- **Verification**: `grep "Last Processed Event ID" .squidsquad/pm/working-state.md` — value differs from `<old_id>`.

---

### TC-13: Mechanical reaction fires for high-confidence pr-merge pattern
- **Precondition**: Event in deque: `{event_type: "pr-merge", payload: {issue_number: 999, pr_number: 100}}`. Issue #999 is at status `pending-ship`. Git log includes merge commit for PR #100 referencing #999.
- **Steps**: Run `python references/scripts/cycle_pre.py pm` with mechanical reactions enabled.
- **Expected**: Issue #999 is transitioned to `shipped` (or `in-progress` per tracker rules) without requiring the agent's creative phase. Reaction is logged in cycle-pre output.
- **Verification**: `python references/scripts/tracker.py get-state 999` returns the expected post-reaction status.

---

### TC-14: Mechanical reaction verifies local state before acting
- **Precondition**: Event in deque: `{event_type: "pr-merge", payload: {issue_number: 999, pr_number: 101}}`. But git log does NOT contain a merge commit for PR #101 (agent clone is behind).
- **Steps**: Run `python references/scripts/cycle_pre.py pm`.
- **Expected**: Mechanical reaction does NOT fire. Issue #999 status is unchanged. Event is retained for retry next cycle (cursor does not advance past it).
- **Verification**: `python references/scripts/tracker.py get-state 999` returns pre-cycle status.

---

### TC-15: Mechanical reaction is idempotent (same event consumed twice)
- **Precondition**: Agent cursor is reset to before event `<ev_id>` (simulating crash recovery). The event contains `{event_type: "pr-merge", payload: {issue_number: 999}}`. Issue #999 is already in the expected post-reaction status (reaction ran last cycle).
- **Steps**: Run `python references/scripts/cycle_pre.py pm` (re-processes `<ev_id>`).
- **Expected**: Reaction executes again but produces no state change (transition rejected silently as already in target status). No error or crash.
- **Verification**: `python references/scripts/tracker.py get-state 999` — status unchanged. cycle_pre exits 0.

---

### TC-16: First cycle after upgrade — no cursor gets recent N events
- **Precondition**: `working-state.md` has `Last Processed Event ID: none` (or the field is absent entirely — freshly upgraded agent).
- **Steps**: Run `python references/scripts/cycle_pre.py pm`.
- **Expected**: `cycle-input.json` `recent_events` contains up to `limit` (default 100) recent events from the deque. Not empty if any events exist. Cursor is then set to the newest returned event ID after the cycle.
- **Verification**: `recent_events` list length is > 0 when harness has events; no exception.

---

### TC-17: Cursor points to evicted event — gets oldest available
- **Precondition**: Deque holds 1000 events with IDs in range `[bbb00001..bbb01000]`. Agent cursor is `aaa99999` (an old ID not in the deque — evicted).
- **Steps**: `GET /events?since=aaa99999`
- **Expected**: Harness does not error. Returns events from oldest available (`bbb00001` onward), up to limit. Agent receives a catch-up burst.
- **Verification**: Response is a non-empty list; first event ID is the oldest in the deque. HTTP status 200.

---

### TC-18: Harness unreachable — returns empty list, agent continues
- **Precondition**: Harness is NOT running. `event_bus_reader.py` deployed. `cycle_pre.py` extended with reader call.
- **Steps**: Run `python references/scripts/cycle_pre.py pm`.
- **Expected**: `cycle_pre.py` does not crash. `cycle-input.json` has `recent_events: []`. Cycle completes normally — agent operates on poll-based behavior (current Phase 2 mode).
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); assert d['recent_events']==[]"` exits 0.

---

### TC-19: event_bus_reader.py missing (ImportError) — returns empty list
- **Precondition**: `event_bus_reader.py` is NOT present in `references/scripts/`. `cycle_pre.py` wraps the import in `try/except ImportError`.
- **Steps**: Run `python references/scripts/cycle_pre.py pm`.
- **Expected**: `cycle_pre.py` does not crash. `cycle-input.json` has `recent_events: []`. No exception surfaced to agent.
- **Verification**: `cycle_pre.py` exits 0; `recent_events` is `[]` in output JSON.

---

### TC-20: Mixed-version squad — Phase 4 + Phase 2 agents coexist
- **Precondition**: pm agent has Phase 4 `cycle_pre.py` + `event_bus_reader.py` deployed. skill agent is still on Phase 2 (no `event_bus_reader.py`, no `recent_events` injection).
- **Steps**: Both agents run concurrent cycles. skill emits events via POST /events. pm reads via GET /events.
- **Expected**: pm agent sees skill's events in `recent_events`. skill agent runs normally with no `recent_events` field in its `cycle-input.json` (or field absent). Neither agent crashes or corrupts the other's state.
- **Verification**: pm cycle-input.json has `recent_events` with skill events. skill cycle-input.json either lacks `recent_events` or has `[]`. Both agents complete cycles without error.

---

### TC-21: Harness restart resets deque — agents catch up
- **Precondition**: Agents have cursors pointing to event IDs from the pre-restart deque (e.g., `ccc00500`). Harness is stopped and restarted. New events are emitted post-restart (e.g., `ddd00001`).
- **Steps**: Agents run their next cycle post-restart (`GET /events?since=ccc00500`).
- **Expected**: Harness returns `[]` (deque empty, old ID not found) or returns newest events from the now-populated deque. Agents reset cursors to newest available ID. No crash, no manual intervention needed.
- **Verification**: Agent cycle completes normally. After 1–2 cycles, cursor in `working-state.md` reflects a valid ID from the new deque.

---

### TC-22: Concurrent agent emissions — received_at ordering correct
- **Precondition**: Two agents emit events simultaneously to harness POST /events endpoint.
- **Steps**: From two processes, emit events within the same millisecond. Read back via GET /events.
- **Expected**: Each event has a unique `received_at` epoch value. Events appear in the deque in the order the harness received them (HTTP arrival order). No duplicate `received_at` values (or documented as acceptable if identical).
- **Verification**: `GET /events?limit=10` — assert all `received_at` values are numeric; assert event IDs are unique.

---

### TC-23: Mechanical reaction does not cause infinite cascade
- **Precondition**: Mechanical reaction is configured to call `tracker.py transition` on `pr-merge`. `tracker.py transition` emits a `status-transition` event back to the bus.
- **Steps**: Trigger a mechanical reaction (feed `pr-merge` event, run `cycle_pre.py`). Monitor the bus for resulting events.
- **Expected**: The `status-transition` event emitted by `tracker.py` does NOT trigger another mechanical reaction because: (a) tracker state machine enforces one-way transitions (shipped is terminal — can't cycle back), and (b) the reacting agent's self-event filter ignores its own emissions. The bus does not grow unboundedly. No infinite reaction loop occurs.
- **Verification**: After reaction fires, `GET /events` deque count increases by at most 1 additional event (the `status-transition`). No further reactions are triggered. cycle_pre exits 0.

---

### TC-24: Phase 2 event emission still works unchanged
- **Precondition**: Phase 4 changes deployed (new `cycle_pre.py`, new `harness.py` with `GET /events` filtering). Phase 2 agents use `event_bus.py` to emit via POST /events.
- **Steps**: Run `python references/scripts/event_bus.py emit cycle-start pm '{"cycle":1}'`.
- **Expected**: Event appears in deque via `GET /events`. Phase 2 emission behavior identical to pre-Phase-4 state. POST /events returns 200. event_bus.py does not crash.
- **Verification**: `GET /events?event_type=cycle-start&role=pm` returns the emitted event.

---

### TC-25: cycle_pre.py existing functionality unaffected
- **Precondition**: Phase 4 cycle_pre.py deployed. Working-state.md has a valid task entry. Config is valid.
- **Steps**: Run `python references/scripts/cycle_pre.py pm`.
- **Expected**: All pre-existing cycle_pre.py steps complete normally: git pull, config validation, context pressure check, working state read, triage/queue queries. The new event reader step does not break or reorder these. `cycle-input.json` contains ALL existing fields plus the new `recent_events` field.
- **Verification**: Diff `cycle-input.json` keys against a Phase 2 baseline; all original keys present; `recent_events` is the only addition. cycle_pre exits 0.

---

### TC-26: cycle-input.json backward compatible — new field is additive
- **Precondition**: Phase 4 `cycle_pre.py` running. Agent CLAUDE.md does not reference `recent_events` (agent is on an older template).
- **Steps**: Run cycle_pre, then have the agent read cycle-input.json in its creative phase.
- **Expected**: Agent ignores unknown `recent_events` field gracefully. No parse error. Existing fields (`role`, `cycle_number`, `working_state`, `timestamp`, etc.) are unchanged.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); required=['role','cycle_number','timestamp','working_state']; assert all(k in d for k in required)"` exits 0.

---

### TC-27: working-state.md parser handles new field without breaking existing fields
- **Precondition**: `working-state.md` contains all existing fields (Task, Status, Started, Phase, Quiet Cycles) plus the new `Last Processed Event ID` field.
- **Steps**: Run `python references/scripts/cycle_pre.py pm` (triggers `_read_working_state()` call).
- **Expected**: All fields parsed correctly. `Last Processed Event ID` is read into the `working_state` dict. No KeyError or silent None for existing fields. `cycle-input.json` working_state object contains the new field.
- **Verification**: `python -c "import json; d=json.load(open('.squidsquad/pm/cycle-input.json')); ws=d['working_state']; assert 'task' in ws; assert 'last_processed_event_id' in ws"`

---

### TC-28: Harness existing endpoints unaffected by Phase 4 additions
- **Precondition**: Phase 4 harness deployed (new `GET /events` filtering added). Existing endpoints in use.
- **Steps**: Test each pre-Phase-4 endpoint: `GET /agents`, `POST /events`, `GET /agents/{role}`, `GET /health`.
- **Expected**: All existing endpoints return the same responses as before Phase 4. No regression in response shape, status codes, or headers.
- **Verification**: Run `python tests/test_harness.py` — all pre-existing harness tests pass. HTTP status 200 for all endpoints that were 200 before.

---

### TC-29: Deploy event_bus_reader.py before harness update — no crash
- **Precondition**: `event_bus_reader.py` deployed to repo. Harness is still on Phase 2 (GET /events exists but has no filtering, or returns unfiltered results). `cycle_pre.py` imports reader with try/except.
- **Steps**: Run `python references/scripts/cycle_pre.py pm`.
- **Expected**: cycle_pre imports `event_bus_reader` successfully. Reader calls GET /events against the unfiltered Phase 2 harness endpoint. Receives unfiltered events (or empty if endpoint missing). Injects `recent_events` (possibly all events, possibly `[]`). No crash.
- **Verification**: cycle_pre exits 0. `recent_events` is a list (possibly unfiltered, possibly empty — both acceptable).

---

### TC-30: Deploy updated cycle_pre.py — graceful when reader missing
- **Precondition**: Updated `cycle_pre.py` is deployed but `event_bus_reader.py` has NOT been deployed yet (deploy order reversed from recommended).
- **Steps**: Run `python references/scripts/cycle_pre.py pm`.
- **Expected**: `cycle_pre.py` catches `ImportError` from `from event_bus_reader import query`. Falls back to `recent_events: []`. Cycle completes normally. No crash, no unhandled exception.
- **Verification**: cycle_pre exits 0. `cycle-input.json` has `recent_events: []`.

---

### TC-31: Mixed deploy order does not break anything
- **Precondition**: Reader deployed but harness not yet updated (Phase 2 harness). Then harness updated mid-squad (Phase 4 harness running while some agents still on Phase 2 cycle_pre).
- **Steps**: Run agents with mixed deploy states across 2 cycles.
- **Expected**: No agent crashes. Phase 4 agents get events. Phase 2 agents get `recent_events: []` or no field. Harness serves both correctly.
- **Verification**: All agents complete cycles without error; harness process remains alive throughout.

---

## Smoke Tests

- [ ] `python references/scripts/cycle_pre.py pm` exits 0 and `.squidsquad/pm/cycle-input.json` contains `recent_events` key
- [ ] `GET /events` returns HTTP 200 with a JSON array
- [ ] `GET /events?role=pm&limit=5` returns at most 5 events, all with `role=="pm"`
- [ ] `GET /events?since=<valid_id>` returns only events strictly after that ID
- [ ] `event_bus_reader.query(role='pm')` returns a list without raising an exception when harness is running
- [ ] `event_bus_reader.query(role='pm')` returns `[]` without raising an exception when harness is down
- [ ] `cycle_pre.py` exits 0 when `event_bus_reader.py` is absent (ImportError path)
- [ ] Every event returned by `GET /events` has a `received_at` numeric field
- [ ] `python tests/run_tests.py` passes with no failures after Phase 4 deployment
- [ ] `working-state.md` `Last Processed Event ID` field updates after a cycle that processes new events

---

## Regression Risks

- **Phase 2 POST /events broken**: Adding GET filtering to harness.py could accidentally break the existing event append path. Watch for: POST /events returning non-200, events not appearing in deque after emission.
- **cycle-input.json field clobbering**: If `recent_events` injection overwrites an existing field (e.g., a key name collision with a future field), agents receive wrong data. Watch for: unexpected None or empty values in existing fields after Phase 4 deployment.
- **working-state.md parser regression**: Adding `Last Processed Event ID` to `_read_working_state()` could break existing field parsing if the regex/match patterns interfere. Watch for: `task`, `status`, `phase`, or `quiet_cycles` returning None when they previously had values.
- **cycle_pre.py latency increase**: The new HTTP GET adds ~5–50ms per cycle. If the harness is slow or the timeout is too low, cycle_pre could hit the timeout and log spurious "harness unreachable" warnings every cycle. Watch for: `recent_events: []` on every cycle even when harness is healthy.
- **Context pressure spike**: Large `recent_events` payloads (burst after long stall) could push `cycle-input.json` token count up significantly. Watch for: agents hitting 70% context threshold earlier than usual after Phase 4 deploy.
- **Mechanical reaction false positives**: `pr-merge` → auto-transition firing on the wrong issue (mismatched PR/issue number parsing). Watch for: tracker issues transitioning unexpectedly without agent creative-phase involvement.
- **Event loop / cascade**: Mechanical reaction emits a `status-transition` event which triggers another mechanical reaction. Watch for: deque growing unboundedly after a single trigger event; repeated tracker transitions for the same issue within a single cycle.
- **state_bus.py misclassifying working-state.md**: If the new `Last Processed Event ID` field causes `state_bus.is_state_file()` to behave differently, the cursor may not persist across cycles. Watch for: cursor always resetting to `none` after each cycle.
- **Port discovery regression**: If `event_bus_reader.py` uses a different port discovery strategy than `event_bus.py` (e.g., clone-local vs parent-dir walk), agents on some clone topologies may fail to reach the harness. Watch for: reader returning `[]` consistently on specific agents while others work.

---

## Comprehension Questions

### CQ-1: What does `recent_events` contain and where does it come from?
- **Files**: `references/sub-skills/common/cycle-runner.md`, `references/scripts/event_bus_reader.py`, `references/scripts/cycle_pre.py`
- **Expected**: `recent_events` is a list of event objects injected into `cycle-input.json` by `cycle_pre.py`. It is populated by calling `event_bus_reader.query()` which issues a `GET /events` request to the harness, filtered by the agent's role and subscribed event types, using the agent's cursor (`Last Processed Event ID`) as the `since` parameter. The list is `[]` if the harness is unreachable or no new events exist since the last cursor.

---

### CQ-2: What happens if the harness is unreachable during cycle_pre?
- **Files**: `references/scripts/cycle_pre.py`, `references/scripts/event_bus_reader.py`
- **Expected**: The import of `event_bus_reader` is wrapped in `try/except ImportError`, and the HTTP call inside `query()` is wrapped with a 500ms timeout. If the harness is unreachable (timeout, connection refused, or HTTP error), `query()` catches the exception and returns `[]`. `cycle_pre.py` injects `recent_events: []` into `cycle-input.json`. The agent proceeds normally with zero events this cycle — same behavior as Phase 2 (no bus read). The agent is not blocked and does not error.

---

### CQ-3: How does an agent's cursor work and where is it stored?
- **Files**: `references/sub-skills/common/working-state.md`, `references/scripts/cycle_pre.py`, `references/scripts/cycle_post.py`
- **Expected**: The cursor is stored as `Last Processed Event ID` in `working-state.md` (the agent-side state file, git-persisted via the state branch commit in `cycle_post.py`). At the start of each cycle, `cycle_pre.py` reads this field and passes it as `?since=<id>` to `GET /events`, so the harness returns only events the agent has not yet seen. After the agent processes the events, `cycle_post.py` updates `working-state.md` with the ID of the most recent event processed, advancing the cursor. If the field is absent or `"none"` (first cycle after upgrade), the reader fetches the most recent N events (default limit) as a one-time catch-up.

---

### CQ-4: Which events does PM care about vs Skill vs QA?
- **Files**: `references/scripts/cycle_pre.py`, `references/sub-skills/common/event-bus-consumer.md` (if created), `references/sub-skills/pm/` or equivalent role config
- **Expected**: Each agent's `cycle_pre.py` has a per-role event type config block (e.g., `PM_EVENT_TYPES`, `SKILL_EVENT_TYPES`, `QA_EVENT_TYPES`). PM subscribes to cross-role coordination events: `pr-merge`, `verification-failed`, `task-start`, `cycle-end`. Skill subscribes to events relevant to dev work: `qa-rejection`, `pr-conflict`, `task-assigned`. QA subscribes to: `pr-merge` (triggers verification), `cycle-end` (check for pending-test items), `verification-failed`. The harness returns all events for the requesting role; the agent's own `cycle_pre.py` filters to its subscribed subset before injecting into `cycle-input.json`. The per-role lists are defined as constants in `cycle_pre.py` (dev discretion on exact structure — dict, constant, or config file).

---

### CQ-5: What is the event ordering guarantee in the bus?
- **Files**: `references/scripts/harness.py`, `references/sub-skills/common/event-bus-consumer.md` (if created), `FEAT-PM-5622-RESEARCH-DEEPSEEK.md`
- **Expected**: Event ordering is "as received by harness" (HTTP arrival time), not causal. The harness appends events to a bounded deque under a single lock, so ordering is consistent within the deque but does not guarantee causal accuracy across concurrent emitters. A `cycle-start` from agent A may appear after a `cycle-end` from agent B even if A started first. The `received_at` timestamp (harness-stamped) and the event `id` both reflect arrival order. Consumers must not assume causal ordering — they treat all events as "happened since last cycle" without imposing causal interpretation. This is a documented limitation to be addressed with Lamport clocks in a future phase if needed.

---

### CQ-6: What is the upgrade sequence for Phase 4 and why does order matter?
- **Files**: `FEAT-PM-5622-CONTEXT.md`, `FEAT-PM-5622-RESEARCH.md`, `references/scripts/cycle_pre.py`
- **Expected**: The 5-step sequence is: (1) deploy `event_bus_reader.py` to main repo — silent, not yet imported anywhere; (2) deploy updated `cycle_pre.py` with import + reader call — import is wrapped in `try/except ImportError` so missing reader returns `[]` gracefully; (3) wait one cycle for agents to git pull; (4) deploy updated `harness.py` with `GET /events` filtering endpoint; (5) next cycle — agents read events. Order matters because `cycle_pre.py` imports `event_bus_reader.py` — if `cycle_pre.py` is deployed without the reader, the ImportError catch ensures no crash. If the harness is updated before `cycle_pre.py`, the GET endpoint exists but nothing calls it yet — also fine. Rollback: revert import lines from `cycle_pre.py` and restart the old harness — agents fall back to `recent_events: []`.
