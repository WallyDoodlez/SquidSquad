# Research — Harness Event-Driven Architecture (Phase 5)
## Scope: Tasks #8694 (dispatch-on-handoff) and #8695 (bootup-complete gate)

_Prepared for PM planning. Read-only investigation of existing codebase._
_Date: 2026-05-17_

---

## Files Surveyed

| File | Purpose |
|------|---------|
| `references/scripts/harness.py` | FastAPI supervisor — owns agent lifecycle (PID monitor, health poll, intent state machine, port discovery, event stream, REST API) |
| `references/scripts/event_bus.py` | Agent-side emit client — fire-and-forget HTTP POST to `/events`; discovers harness port via `.harness-port` file walk |
| `references/scripts/event_bus_reader.py` | Agent-side read client — cursor-based GET `/events`; used by `cycle_pre.py` to pull events since last cursor |
| `references/scripts/event_catalog.py` | Single source of truth for event type registry — two tiers: `EMITTED` (ground truth) and `RECOGNIZED` (planned) |
| `references/scripts/event_validator.py` | Static validation of `Event Reactions` config section — checks hallucinated events, missing consumers, cycles |
| `references/scripts/cycle_pre.py` | Pre-cycle mechanical layer — pulls, reads working-state, queries work queue, reads event bus, writes `cycle-input.json` |
| `references/scripts/cycle_post.py` | Post-cycle mechanical layer — executes status transitions, commits, pushes, advances event cursor, checks harness intent |
| `references/scripts/tracker.py` | Tracker abstraction — `work_queue()` encodes pickup priority; `transition()` enforces legal moves and role authority |
| `.squidsquad/skill/CLAUDE.md` | Composed skill agent instructions — contains `event-driven-workflow` sub-skill documenting Monitor+event_poll.py boot |
| `.squidsquad/pm/CLAUDE.md` | Composed PM agent instructions — same `event-driven-workflow` sub-skill |
| `.squidsquad/config.md` | Project configuration — `event-driven: no` (not set yet), event reactions per role |

**Note**: `event_poll.py` is referenced in composed CLAUDE.md files (`references/scripts/event_poll.py <role> --wait 5 --target`) but **does not exist yet** in `references/scripts/`. It is a planned script for Phase 5.

---

## Harness Architecture Summary

The harness is a FastAPI process (`harness.py`) on port 7373 (configurable). It acts as:

1. **Agent supervisor** — spawns agents via `boot_remote.boot_agent()` in visible terminal windows. Tracks liveness via stored `AgentState.claude_pid` plus `.claude-pid` file fallback. Background health poll thread runs every 5 seconds (`HEALTH_POLL_INTERVAL = 5`).

2. **Intent state machine** — per-agent intent: `running / stopping / restarting / stopped`. Persisted to `.squidsquad/.harness-state.json`. Agents query harness intent at cycle end via `GET /agents/{role}` (in `cycle_post._query_harness_intent()`); exit code 42 triggers respawn.

3. **Event stream** — in-memory bounded `EventStream` (deque, maxlen=1000). Events stored in-memory only — no disk persistence. Agents POST events to `/events`; harness updates `AgentState` fields (cycle, phase) from them.

4. **REST API** — HTTP only, `127.0.0.1` binding:
   - `GET /status` — harness + all agents health
   - `GET /agents` — list agents
   - `GET /agents/{role}` — single agent state (includes `intent`)
   - `GET /agents/{role}/health` — liveness, phase, context pressure
   - `POST /agents/{role}/start` — spawn agent
   - `POST /agents/{role}/stop` — set intent=stopping
   - `POST /agents/{role}/restart` — set intent=restarting
   - `POST /agents/all/start` — spawn all
   - `POST /agents/all/stop` — stop all
   - `POST /events` — receive event from agent
   - `GET /events` — retrieve events with filter/cursor
   - `POST /merge` — async PR merge + compose trigger
   - `POST /shutdown` — graceful harness shutdown

5. **Port discovery** — harness writes port to `.squidsquad/.harness-port` and distributes to each agent clone's `.squidsquad/.harness-port`. All clients walk parent directories up to 5 levels to find it.

---

## Tracker Observation Today (What It Does, What It Doesn't)

### What the harness does NOT do today:

- **No tracker polling.** The harness has zero code that watches GitHub Issues, calls `gh` CLI, polls label changes, or reads `tracker.py` output.
- **No dispatch logic.** There is no code in `harness.py` that decides which event to send to which role, or even emits outbound `assigned-to` / `status-transition` events to agents.
- **No webhook listener.** No GitHub webhook integration anywhere in the codebase.

### What exists today:

- **Agents self-poll the tracker** via `tracker.py work-queue <role>` inside `cycle_pre.py` each cycle (approximately every 30 minutes). The work queue is freshly re-read every pre-cycle.
- **Status transitions flow from agents to tracker** (via `cycle_post._do_status_transitions()` → `tracker.py transition`), and the transition emits a `status-transition` event back to the harness event stream for observability only.
- **Event stream receives status-transition events** (POST `/events` from `tracker.py`), but the harness only stores them — it does not re-dispatch or react to them.
- **The `_update_agent_from_event()` function** (`harness.py:750`) updates `AgentState.current_cycle/phase` from events but has no dispatch logic.

### Key gap for #8694:

The harness currently has no mechanism to observe tracker state changes. It receives `status-transition` events via POST `/events` — meaning if agents emit these, the harness _already sees them_. The missing piece is: **when a status-transition event arrives, re-evaluate the affected role's work queue and emit an `assigned-to` event**.

---

## Event Bus Mechanics

### Storage

- **In-memory only.** `EventStream` is a `collections.deque(maxlen=1000)` (`harness.py:364`). No SQLite, no file persistence, no database. Events evicted on overflow (oldest first).
- **No replay on harness restart.** If the harness crashes, all events are lost. Agents that had not advanced their cursor lose the events.

### Emission (agent → harness)

- `event_bus.emit()` — fire-and-forget HTTP POST to `http://127.0.0.1:{port}/events` with 500ms timeout.
- Called from: `cycle_pre.py` (cycle-start), `cycle_post.py` (cycle-end), `tracker.py` (status-transition, tracker-comment), `git_ops.py` (git-commit, git-push, etc.), `harness.py` itself (pr-merged, compose-completed, request-merge via `_emit_event()`).

### Reading (harness → agent, today's /loop mode)

- `event_bus_reader.query()` — cursor-based GET `/events?since=<id>&role=<r>&event_type=<types>` with 500ms timeout.
- Called from `cycle_pre.py:1019` during pre-cycle. Last cursor stored in `working-state.md` (`Last Processed Event ID`). Cursor advanced by `cycle_post._advance_event_cursor()` after creative phase completes.
- Events are filtered per-role by `_filter_events_for_role()` using either config-driven or hardcoded `_ROLE_EVENT_TYPES` (`cycle_pre.py:349`).

### Direction: agent → harness (existing POST /events)

The `POST /events` endpoint (`harness.py:827`) already accepts any event from agents. Validation: requires `event_type` and `role` fields. The endpoint does **no** type validation against the event catalog — any event_type string is accepted. This means a `bootup-complete` event type can be POSTed today without harness changes to the `/events` endpoint itself.

### Direction: harness → agent (today)

Today this happens **only** through `cycle-input.json` (pre-cycle pull model). The harness does NOT push events to agents. The `event-driven-workflow` sub-skill in CLAUDE.md describes the future architecture where `event_poll.py` streams events to the Monitor tool, but this script does not exist yet.

---

## Pickup Ordering (with Exact Citations)

### tracker.py work_queue() — canonical priority definition

File: `references/scripts/tracker.py`, function `work_queue()`, lines 437-510.

Priority sort key (lines 483-501):

```python
# Determine sort key: (status_rank, type_rank, priority_rank)
if status == "in-progress":
    status_rank = 0
elif status == "approved":
    status_rank = 1
else:  # open
    status_rank = 2

type_rank = 0 if item_type == "issue" else 1
prio = severity if item_type == "issue" else priority
prio_rank = PRIORITY_ORDER.get(prio, 1)  # default medium
```

Docstring at line 440-444:

```
Priority order (strict):
1. In-progress items (resume first)
2. Approved issues — severity:high → medium → low
3. Approved tasks — priority:high → medium → low
4. Open issues — severity:high → medium → low
```

### Skill CLAUDE.md — agent's pickup rule

File: `.squidsquad/skill/CLAUDE.md`, line ~501-507 (sub-skill: triage-issues):

```
This returns a unified, priority-sorted list of ALL actionable items (issues AND tasks). Priority order is enforced by the script:
1. In-progress items (resume first)
2. Approved issues — severity:high → medium → low
3. Approved tasks — priority:high → medium → low
4. Open issues — severity:high → medium → low

**You MUST pick the first item in the queue.** No discretion to skip, reorder, or cherry-pick.
```

### QA-rejected items override the queue

File: `.squidsquad/skill/CLAUDE.md`, lines ~477-495 (sub-skill: triage-issues):

```
**First, check for QA-rejected items** (highest priority — fix existing before starting new):
python references/scripts/triage.py qa-rejected skill --json
```

### Design-gate skip

File: `.squidsquad/skill/CLAUDE.md`, line ~513:

```
**Design label check**: If the item has a `design:needed` or `design:in-progress` label, skip it and pick the next item in the queue.
```

### Actionable statuses

File: `references/scripts/tracker.py`, lines 479-481:

```python
# Skip items not actionable by dev agents
if status not in ("in-progress", "approved", "open"):
    continue
```

**Implication for #8694**: The harness dispatch logic for `assigned-to` events needs to replicate the same priority ordering as `work_queue()`. The simplest approach is to call `tracker.py work-queue <role>` and take the first item from stdout JSON, then emit `assigned-to` with that item's payload.

---

## Path to Add bootup-complete (#8695)

### What needs to change

**Agent side** (instructions / CLAUDE.md template):
- Add to `event-driven-workflow` sub-skill: after boot init (working-state read, Monitor subscription active), agent must emit `bootup-complete` via `event_bus.emit("bootup-complete", role, {"monitor_active": true})`.
- This uses the existing `event_bus.emit()` function — no new agent-side code needed.

**Harness side — three changes needed**:

1. **Add `bootup-complete` to event catalog** (`references/scripts/event_catalog.py`):
   - Move from `RECOGNIZED` tier to `EMITTED` tier or add as new `EMITTED` entry.
   - Add to `EMITTED` dict at line 26: `"bootup-complete"` with source `"agent boot"`, payload_fields `["monitor_active"]`.

2. **Add per-role boot gate to `AgentState`** (`harness.py:68`):
   - Add field `bootup_complete: bool = False` to `AgentState.__slots__` and `__init__`.
   - Reset to `False` on spawn (`start_agent`, `_deferred_init`, `update_health` when PID changes).
   - Set to `True` in `_update_agent_from_event()` when `event_type == "bootup-complete"`.

3. **Add per-role dispatch queue** (`harness.py` — new data structure):
   - Add `_pending_dispatch: dict[str, list[dict]]` to `HarnessState` (or inline per `AgentState`).
   - In the future `_dispatch_to_agent()` function: if `bootup_complete is False`, append event to `_pending_dispatch[role]`; log `"queued-but-not-dispatched for {role} — waiting for bootup-complete"`.
   - When `bootup-complete` arrives in `_update_agent_from_event()`: set `bootup_complete = True`, then flush `_pending_dispatch[role]` by calling `_dispatch_to_agent()` for each queued event.

**Expose via existing `/agents/{role}` endpoint**:
- `AgentState.to_dict()` already returns all fields. Add `"bootup_complete": self.bootup_complete` to the dict (`harness.py:101-115`). No new endpoint needed — issue #8695 acceptance criterion says "harness exposes bootup-complete status per role via existing `/agents/{role}` endpoint."

### Concrete file changes summary

| File | Change |
|------|--------|
| `references/scripts/event_catalog.py` | Add `bootup-complete` to `EMITTED` dict (line ~87) |
| `references/scripts/harness.py` | `AgentState`: add `bootup_complete` field (line ~71); `_update_agent_from_event()`: set on event (line ~768); `HarnessState`: add `_pending_dispatch` dict; new `_flush_dispatch_queue(role)` helper; reset `bootup_complete=False` on each agent spawn in `update_health()` and `start_agent()` |
| `references/sub-skills/event-driven-workflow.md` (or wherever the sub-skill source lives) | Add boot sequence step: emit `bootup-complete` after Monitor subscription active |

---

## Path to Dispatch-on-Handoff (#8694)

### Core logic needed

The harness needs to observe status-transition events and re-evaluate role work queues. Here is the minimal path:

**Step 1 — React to status-transition events in `_update_agent_from_event()`** (`harness.py:750`):

```python
elif event_type == "status-transition":
    # Re-evaluate work queue for the transitioning role + potential recipient role
    payload = event.get("payload", {})
    transitioned_role = _extract_role_from_issue(payload.get("issue_number"))
    _schedule_dispatch_check(transitioned_role)
```

This is a new code path after the existing `phase-change` handler at line 769.

**Step 2 — Add `_schedule_dispatch_check(role)`** — a lightweight function (or thread-safe flag set) that triggers a work-queue re-evaluation. Can be a simple `threading.Event` or queue.

**Step 3 — Add `_evaluate_and_dispatch(role)`**:

```python
def _evaluate_and_dispatch(role):
    """Re-evaluate a role's work queue and emit assigned-to if head changed."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "tracker.py"), "work-queue", role],
        capture_output=True, text=True, check=False, cwd=str(REPO_ROOT)
    )
    if result.returncode != 0:
        return
    try:
        queue = json.loads(result.stdout)
    except json.JSONDecodeError:
        return
    if not queue:
        # No work — optionally emit no-work-available
        return
    top_item = queue[0]
    # Check if already dispatched this item (avoid duplicate dispatch)
    agent = state.get_agent(role)
    if agent and agent.current_dispatched_item == str(top_item["number"]):
        return
    # Dispatch
    _emit_outbound_event("assigned-to", role, payload={
        "issue_number": top_item["number"],
        "title": top_item["title"],
        "type": top_item["type"],
        "priority": top_item["priority"],
        "status": top_item["status"],
    })
    if agent:
        agent.current_dispatched_item = str(top_item["number"])
```

**Step 4 — Add `_emit_outbound_event(event_type, target_role, payload)`**:

This is the first harness→agent push. The delivery mechanism depends on `event_poll.py` existing. Options:

- **File-based**: write JSON to `.squidsquad/<role>/.pending-event` — agent's event_poll.py reads this file.
- **API-polled**: store in `EventStream` but with a `target_role` field; event_poll.py filters on `target_role`.

The CLAUDE.md sub-skill says agents use the Monitor tool watching `event_poll.py <role> --wait 5 --target`. The `--target` flag likely means "filter events targeted at this role." **The simplest approach**: store outbound events in the existing `EventStream` with a `target_role` field, and `event_poll.py` polls `GET /events?role=<role>&event_type=assigned-to` until a new event appears.

### Race handling considerations

**Multiple simultaneous transitions**: If agents A and B both transition items near-simultaneously, two `status-transition` events arrive. Each triggers `_evaluate_and_dispatch()`. These can run concurrently if dispatched to separate background threads. Since they target different roles, no conflict. If same role, last-write-wins on `current_dispatched_item` — acceptable if `_evaluate_and_dispatch` is serialized per role (use `threading.Lock` per role or a single dispatch thread with a role-keyed work queue).

**Queue drain vs. in-flight**: If role X is processing event E1 and a new transition arrives making E2 available, the harness should queue E2 for delivery after E1 is completed. The `bootup-complete` gate pattern already handles this: don't dispatch when `in_flight_event` is set (another field needed on `AgentState`). When agent completes work (emits a status-transition for their own item), `in_flight_event` clears and the next dispatch triggers.

**No /complete API for #8694**: The issue explicitly says "completion is inferred from tracker state." The signal is: agent's assigned item transitions away from their actionable statuses (`in-progress`, `approved`, `open`). The harness detects this via the incoming `status-transition` event. This avoids needing a separate `/complete` endpoint.

**Harness busy during dispatch B**: Since harness is async (FastAPI + uvicorn), event receipt and dispatch-trigger are handled in async context. Background `_evaluate_and_dispatch()` runs in a thread. If harness receives event B while processing A's dispatch, it queues via `_schedule_dispatch_check()` — a thread-safe queue (e.g., `queue.Queue`) drains sequentially.

### Concrete file changes summary

| File | Change |
|------|--------|
| `references/scripts/harness.py` | `AgentState`: add `current_dispatched_item: str = None`, `in_flight_event: str = None`; `_update_agent_from_event()`: add `status-transition` handler that calls `_schedule_dispatch_check()`; new functions: `_schedule_dispatch_check()`, `_evaluate_and_dispatch()`, `_emit_outbound_event()`; new background dispatch thread or per-role work queue |
| `references/scripts/event_catalog.py` | Add `assigned-to` and `no-work-available` to `EMITTED` dict (currently only in `RECOGNIZED` tier per config.md — see below) |
| New file: `references/scripts/event_poll.py` | Script that polls `GET /events` for target-role events and streams JSON lines to stdout. Needed for Monitor tool integration. Takes `<role> --wait <seconds> --target` args. |

---

## Open Questions for PM Discussion Phase

1. **How does the harness learn which role owns a transitioning issue?** The `status-transition` payload has `issue_number` but not necessarily the `role:*` label of the issue. The harness would need to either: (a) call `tracker.py get-labels <number>` to read role labels, or (b) receive `role` in the status-transition payload. Option B requires a small `tracker.py` change to include `role` in the event payload. Is this acceptable?

2. **How does the dispatch loop avoid re-dispatching the same item?** The `current_dispatched_item` field on `AgentState` tracks last dispatch, but if the harness restarts, this is lost. Should it be persisted to `.harness-state.json`? Or is it acceptable to re-emit `assigned-to` for an item the agent already picked up (idempotent if agent checks working-state)?

3. **What does the harness do when `work-queue <role>` returns empty?** Option A: emit nothing (agent's improvement-scan sub-skill handles idle). Option B: emit `no-work-available`. The #8694 issue says "emit no-work-available (or stay silent)". This needs a decision — `event-driven-workflow` CLAUDE.md doesn't document what happens on idle.

4. **Does `event_poll.py` long-poll or loop-poll?** The `--wait 5` flag in the CLAUDE.md boot sequence suggests 5-second poll interval. Should it be a true HTTP long-poll (blocking GET until event arrives) or a short-poll loop? Long-poll would need a new endpoint or SSE; short-poll can use existing `GET /events?since=<id>`.

5. **Singleton enforcement (#8692 interaction)**: #8692 (no singleton enforcement — high severity, open) is a prerequisite risk. If two agents of the same role boot simultaneously, both emit `bootup-complete` and both receive `assigned-to`. The harness has no way to distinguish which session is authoritative. Should #8692 be fixed before Phase 5 starts?

6. **Bootstrap order during harness restart**: When harness restarts and all agents are re-spawned (deferred init), the dispatch gate means no events go out until all agents emit `bootup-complete`. What's the timeout if an agent never boots? Is there a watchdog that clears the gate after N seconds?

7. **What is the `--target` flag in `event_poll.py`?** Not yet defined (script doesn't exist). Does it mean "only return events targeted at this role" or "include all events but filter to this role's event types"? This determines whether `assigned-to` needs a `target_role` field or whether it uses the existing `role` field.

8. **Does #8694 require the `event-driven: yes` config gate to be flipped first?** The `event-driven-workflow` sub-skill is gated on config. If the harness starts emitting `assigned-to` events but agents are still in `/loop` mode, those events are undelivered. The config gate flip and the harness dispatch implementation need to be coordinated.

---

## Related Bugs Filed

- **#8689** (`role:skill`, `severity:medium`, `status:open`): `POST /agents/{role}/restart` does not immediately reboot idle agents — restart is queued until the agent's next `/loop` tick. Relevant to #8694: in event-driven mode, the idle agent issue changes character (Monitor replaces /loop), but the harness restart path still involves PID lifecycle. Fix may be a prerequisite for responsive dispatch.

- **#8691** (`role:skill`, `severity:medium`, `status:open`): `cycle_post.py` commits uncommitted files outside the agent's domain (broad `git add`). Not directly blocking Phase 5, but worsens audit trail if multiple agents share a clone — relevant risk noted alongside #8692.

- **#8692** (`role:skill`, `severity:high`, `status:open`): No singleton enforcement — two agents of the same role can run in the same clone concurrently. High-severity blocker risk for Phase 5: if the harness dispatches `assigned-to` to a role with two active sessions, both will attempt to process the same item. Recommend treating this as a prerequisite for Phase 5 tasks.

---

## Summary Table — Key Gaps Between Today and Phase 5 Target

| Gap | Location | Tasks |
|-----|----------|-------|
| Harness has no tracker observation | `harness.py` | #8694 |
| No `assigned-to` event emitter in harness | `harness.py` | #8694 |
| No `bootup-complete` event type defined | `event_catalog.py` | #8695 |
| No `bootup_complete` field on AgentState | `harness.py` | #8695 |
| No dispatch gate on `bootup_complete` | `harness.py` | #8695 |
| `event_poll.py` does not exist | New file | #8694 + #8695 |
| `assigned-to` in catalog only as config reaction, not EMITTED | `event_catalog.py` | #8694 |
| No singleton enforcement | `thin_launcher.py` / harness | #8692 (blocker) |
| `event-driven: yes` not set in config.md | `.squidsquad/config.md` | Coordination task |
