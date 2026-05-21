# RESEARCH-9873-A — Cursor Migration to Harness + Ack Event Type + Harness Ack-Consumer Task

**Issue**: #9873-A (foundation slice; ticket number will be assigned when umbrella splits)
**Phase**: 1 (Research)
**Author**: pm-research-agent
**Date**: 2026-05-21

---

## §1 Problem Statement

The event bus has three missing pieces that must ship together before the -B/-C/-D/-E/-F slices
can build on top:

1. **Cursor is agent-local** today. `event_poll.py` writes `Last Processed Event ID` into
   `.squidsquad/<role>/working-state.md`. The harness has no authoritative view of where each
   agent sits in the stream. This blocks server-side retry, timeout detection, and the ack-consumer
   model.

2. **Ack event type has no harness consumer that advances cursors**. The RECOGNIZED catalog
   entry (`event_catalog.py:138`) uses the old payload schema `{event_id, result}`. The vault
   decision (locked 2026-05-21) locks `{ack_for, role}` as the payload. The task prompt specifies
   `{advance_to, role}`. These three schemas conflict — the correct shape must be locked in this
   RESEARCH before dev pickup.

3. **The inline ack-handler at `receive_event` (harness.py:1534–1558) is already wired but uses
   the wrong schema and wrong cursor semantics**. It calls `event_lifecycle.ack(ack_event_id,
   role)` — clearing in-flight for a single event — but does NOT advance a per-role cursor. This
   is Phase 4 plumbing left half-wired from a previous cycle.

The refined model (cycles 1541-1560, superseding RESEARCH-9873's framing) assigns cursor
ownership to the harness. Ack = "event_poll.py delivered this batch to stdout and wrote the
Monitor nudge" — not "agent finished processing." The cursor is the sole tracking primitive; ack
is the event-bus message that advances it.

---

## §2 Current State (file:line refs)

### 2.1 EventLifecycleManager — harness.py:610–809

- **`:623-626`** — `append(event)`: stores event in stream, calls `_persist()`.
- **`:628-644`** — `dispatch(event_id, role, event)`: marks in-flight. **Intact but no callers in
  live endpoint code** (stripped in #9741). Only called from tests directly.
- **`:646-658`** — `ack(event_id, role)`: clears in-flight for a single event_id. **Intact**.
  Called by `complete_event` endpoint AND by the inline ack-handler at line 1537 (see §2.5).
- **`:665-686`** — `_persist()`: atomic `.event-state.json` write. Holds `self._lock` while also
  calling `self._stream.get_recent(200)` (acquires `EventStream._lock`) and performing the sync
  file write. **H6 wedge hazard from RESEARCH-9874**: called on the hot `POST /events` path
  without `to_thread` wrapping.
- **`:742-788`** — `timeout_scan()`: scans `_in_flight`; logs + resets timers. **No re-delivery**.
  Finds nothing today because dispatch() is never called from live endpoints.
- **`:790-809`** — `start_timeout_scanner()` / `_scan_loop()`: background thread, every 30s.

**Per-role cursor state**: does NOT exist in EventLifecycleManager today. The class has
`_in_flight`, `_dispatched`, `_dispatch_times`, `_retry_counts` — no `_cursors` dict.

### 2.2 GET /events/for/{role} — harness.py:1621–1688

Pure filtered-read. dispatch() call stripped at commit 017b65a3 (#9741). Comment at line 1675
documents the strip and references #9813. No lifecycle side effects.

### 2.3 POST /events/{event_id}/complete — harness.py:1691–1746

Intact. Calls `event_lifecycle.ack(event_id, role)`. Since dispatch() is never called from
endpoints, `_in_flight` is always empty, so `ack()` always returns False → endpoint always
returns 410. The `_execute_transition`/`_execute_comment` helpers (subprocess.run, H4 wedge
hazard) are unreachable today.

### 2.4 GET /events/lifecycle — harness.py:1888–1904

Returns `{stream_size, in_flight, persisted}`. No cursor data. Will need a cursor field or a
companion endpoint.

### 2.5 Inline ack-handler at receive_event — harness.py:1533–1558

**Critical finding**: there is already partial ack-handling wired in `POST /events`:

```python
# harness.py:1534-1539 (approximate)
if event_type == "ack":
    ack_event_id = body.get("payload", {}).get("event_id")
    if ack_event_id and role:
        acked = event_lifecycle.ack(ack_event_id, role)
```

This is **Option A (inline on POST /events)**. It:
- Fires synchronously on the asyncio event loop (H6 risk if `ack()` → `_persist()` is slow).
- Uses payload key `event_id` — conflicts with vault's `ack_for` and prompt's `advance_to`.
- Calls `event_lifecycle.ack(single_event_id, role)` — clears in-flight for one event but does
  NOT advance a per-role cursor (cursor doesn't exist yet).
- Also has a `stop-confirmed` branch (lines 1544–1557) that is a separate concern.

**Implication**: Option A (inline) is already partially present. -A's job is to extend this
handler to: (a) use the correct payload schema, (b) advance the harness-owned cursor instead of
(or in addition to) clearing in-flight.

### 2.6 event_bus.py — ack() fully deleted (#9813)

`event_bus.py` currently contains only `emit()` and `bootup_complete()`. No `ack()` function.
The deleted form emitted `event_type="ack"` via `emit()` — which is exactly the pattern the vault
decision locks. Re-implementation is a thin wrapper around `emit()`.

### 2.7 event_poll.py — cursor handling today

- **`:66`** — `_working_state_path(role)`: cursor lives in `.squidsquad/<role>/working-state.md`.
- **`:81-93`** — `_resolve_cursor(role, since_arg)`: reads from working-state.md or defaults to "".
  No harness query. Default "" → harness treats as since=0 → returns all retained events. This is
  the bootstrap behavior today: first boot with no cursor = process all events in deque.
- **`:96-131`** — `_write_cursor_atomic(role, cursor)`: writes `Last Processed Event ID` line.
- **`:264,271`** — per-event loop: write cursor THEN emit to stdout (advance-then-emit, per spec §3.5).
- **`:279-283`** — post-loop eviction re-anchor (#9740 fix).

In the new model, `_resolve_cursor` must query `GET /events/cursor/{role}` first; `_write_cursor_atomic`
is **removed** (harness owns cursor, advanced via ack event). event_poll.py becomes ultra-thin:
detect new events past cursor → write one nudge line to stdout → emit ack event.

### 2.8 event_catalog.py — current ack entry

RECOGNIZED tier, `event_catalog.py:138–142`:
```python
"ack": {
    "description": "Agent acknowledges event completion — closes the event lifecycle",
    "planned_source": "event_bus.py ack()",
    "payload_fields": ["event_id", "result"],
}
```

Must be updated: payload schema should change to `{ack_for, role}` (vault schema) or
`{advance_to, role}` (prompt schema) — see §9 Q1.

### 2.9 .event-state.json — current persistence shape

```json
{
  "events": [...],
  "in_flight": {},
  "dispatched": {},
  "dispatch_times": {},
  "retry_counts": {}
}
```

No cursor field. Cursor migration adds `"cursors": {"pm": "abc123", "skill": "def456"}`.

### 2.10 .harness-state.json — agent intent state

Contains per-role `{intent, intent_set_at, status, boot_time, clone_path, claude_pid, ...}`.
No cursor data. Cursor does NOT belong here — harness-state.json is agent lifecycle state;
event cursors are event-bus state (belongs in .event-state.json).

---

## §3 Cursor Persistence Options

### 3.1 Location options

**Option L1 — Extend .event-state.json** (recommended):
Add `"cursors": {role: event_id}` key alongside `in_flight`, `dispatched`, etc. The
`EventLifecycleManager._persist()` already writes this file atomically. Cursor and in-flight
data share the same lock discipline (`self._lock`). Single persist call covers both.

**Option L2 — Separate .event-cursors.json**:
New file, parallel to .event-state.json. Cleaner schema separation. Requires a second atomic
write and separate lock (or reuse the same lock). Adds file count. No strong benefit over L1
given both are owned by `EventLifecycleManager`.

**Option L3 — In .harness-state.json**:
Wrong home. Harness-state is agent lifecycle; cursors are stream-consumer positions. Mixing them
couples lifecycle restart logic with event bus logic. Rejected.

**Recommendation**: L1 — extend .event-state.json.

### 3.2 Schema (in .event-state.json)

```json
{
  "events": [...],
  "in_flight": {},
  "dispatched": {},
  "dispatch_times": {},
  "retry_counts": {},
  "cursors": {
    "pm": "abc123def456",
    "skill": "7890abcd1234"
  }
}
```

`cursors[role]` = event_id of the most recently tended event (harness deque ID). The next
`GET /events/for/{role}?since=<cursor>` returns events AFTER this ID (exclusive, matching
existing "since" semantics on the endpoint).

### 3.3 Bootstrap / first-boot cursor

Two options:

**Option B1 — End-of-queue (no replay)**:
On first boot (no cursor in .event-state.json for this role), cursor = latest event_id in the
deque. The agent starts fresh; no backlog is replayed. This matches Kafka's
`auto.offset.reset=latest` behavior.

**Option B2 — Beginning-of-queue (process all retained)**:
On first boot, cursor = "" (empty), so `GET /events/for/{role}?since=` returns all retained
events. The agent processes the entire deque on first wake. This matches `auto.offset.reset=earliest`.

**Current behavior**: `event_poll.py` today defaults cursor to "" if no working-state.md line
exists. So the current system is B2 (process all retained events on first boot). However with a
1000-event deque and long-running harness, B2 on first agent boot could deliver 1000 events at
once — most likely stale noise.

**Recommendation**: B1 (end-of-queue). New agents start at the tip. Replay of missed events
is a -B concern (timeout_scan re-delivery). If the human wants B2 as opt-in (e.g., disaster
recovery replay), that is a config flag for a later slice.

**Edge case**: harness restart clears the in-memory deque. Cursors persist in .event-state.json
but the events they point to may no longer exist in the deque. On restart, the harness loads
cursors from .event-state.json and reloads the last 200 events from the same file. If a cursor
points to an event ID that exists in the reloaded 200, GET /events/for/{role}?since={cursor}
returns events after it normally. If the cursor points to an event evicted before the last 200,
the eviction path (EVICTION warning + oldest_id re-anchor) fires — same logic as today. No
special restart handling needed.

---

## §4 Ack-Consumer Architecture Options

**Context**: the inline ack-handler at harness.py:1534 already implements Option A partially.

### Option A — Inline at POST /events (already partially present)

**Current state**: wired for the `stop-confirmed` sub-case. Can be extended to advance cursor.

**Pro**: no new infrastructure. Simplest extension of what's already there.

**Con**: runs on the asyncio event loop. `ack()` calls `_persist()`, which holds `self._lock`
while doing sync file I/O (`tmp.write_text` + `tmp.replace`). This is the H6 wedge hazard from
RESEARCH-9874. Every ack event received triggers a file write on the hot path.

**Mitigation**: wrap `event_lifecycle.ack_cursor(...)` (the new combined operation) in
`await asyncio.to_thread(...)` at the call site, same pattern as `await asyncio.to_thread(state.save_state)` at line 1530. This keeps Option A but pushes the I/O off-loop.

**Revised Option A (with to_thread)**: inline at POST /events, but ack processing deferred to
thread pool. HTTP response returns before ack processing completes. Acceptable for fire-and-forget
ack semantics.

### Option B — Background asyncio.Task scanning deque every N seconds

Parallel to `timeout_scan()`. A new coroutine (not a thread — stays on the event loop) reads
from the deque for events with `event_type=="ack"` and processes them. Runs every 2-5 seconds.

**Pro**: clean separation from the HTTP request path. Ack processing is decoupled from event
ingestion.

**Con**: ack events sit in the deque between their arrival and the next scan tick (up to N
seconds). Cursor is stale during that window. For -A this is fine — cursor staleness of 5s is
acceptable given the Monitor nudge cadence. However the scan loop itself runs on the event loop;
`_persist()` must still be wrapped in `to_thread` to avoid blocking the loop.

**Implementation**: `asyncio.create_task(_ack_scan_loop())` in the FastAPI lifespan, alongside
`event_lifecycle.start_timeout_scanner()`.

### Option C — Queue + worker thread (proper 4-layer split)

Not recommended for -A. This is the full Option C from RESEARCH-9874. Weeks of work, out of scope.

### Recommendation

**Option A (revised, with `to_thread` wrap)** for -A. Rationale:

1. Infrastructure already exists at harness.py:1534 — extending it is lower risk than adding a
   new scan loop.
2. The to_thread wrap mitigates the H6 wedge hazard. The persist call moves off the event loop.
3. Cursor advance latency = the time for the POST /events response cycle + thread-pool scheduling.
   This is sub-millisecond in practice — adequate for the nudge-driven polling model.
4. Option B adds complexity (new task, scan interval tuning) for marginal benefit. Option B is
   the right path if ack volume becomes high enough that Option A creates thread-pool saturation —
   not a realistic concern at current agent counts.

**Flag**: Option B is the safer long-term design. If -B (timeout re-delivery) requires a scan
loop anyway, pivoting Option A → Option B in the same PR is low-cost. PM should check whether
-B's scan loop can double as the ack-consumer — merging them avoids two separate scan tasks.

---

## §5 Endpoint Design: GET /events/cursor/{role}

### Shape

```http
GET /events/cursor/{role}
```

Response when cursor exists:
```json
{"cursor": "abc123def456", "role": "pm"}
```

Response when no cursor yet (first boot):
```json
{"cursor": null, "role": "pm"}
```

**Never 404**: a 404 forces callers to handle a non-2xx path before they've done anything wrong.
Returning `{"cursor": null}` with 200 is cleaner — the caller interprets null as "start at tip"
per the bootstrap logic.

### event_poll.py usage

`_resolve_cursor` changes to:
1. If `--since` flag: use that (unchanged).
2. Else: `GET /events/cursor/{role}` → use returned cursor (or null = tip).
3. Fallback (harness unreachable): fall through to working-state.md (backward compat shim during
   transition period only; remove in a follow-on slice).

**Note**: if the harness is unreachable, event_poll.py already returns None and exits. The
working-state.md fallback may not be needed — harness reachability is a hard dependency in
event-driven mode.

### Atomicity

`GET /events/cursor/{role}` reads `_cursors[role]` under `event_lifecycle._lock`. Atomic read
with no persist. Safe.

---

## §6 #9741 Dispatch Revert Question

### Does cursor obsolete dispatch() / in-flight tracking?

In the cursor-based model:
- `cursor[role]` = "agent has consumed all events up to and including this ID."
- In-flight = "delivered but not yet acked." This was the old mechanism for tracking the gap
  between dispatch and ack.

With cursor-as-ack-signal:
- The gap between cursor and deque head IS the in-flight window.
- Harness doesn't need to track individual in-flight event IDs — the cursor position defines
  the unacked range.

**Conclusion**: for the cursor model, `dispatch()` + `_in_flight` dict are NOT needed for cursor
advancement. The ack-consumer only needs to advance `_cursors[role]` — it does not need to clear
entries from `_in_flight`.

**However**: `timeout_scan()` depends on `_in_flight` to detect overdue events. Without dispatch()
populating `_in_flight`, timeout_scan() cannot fire (same as today — it finds nothing and does
nothing). In the new model, timeout detection must compare `cursor[role]` age against now, not
`_dispatch_times[event_id]`.

**Recommendation for -A**: do NOT restore dispatch() from GET /events/for/{role}. Keep the #9741
strip. The -B (timeout re-delivery) slice will redesign timeout_scan() to use cursor staleness
rather than per-event dispatch times. This is a cleaner design than restoring the old mechanism.

**In-flight endpoint**: `GET /events/in-flight/{role}` (harness.py:1749) will return empty lists
as today. Consider adding a `GET /events/lag/{role}` endpoint in -B that computes `deque_head -
cursor[role]` to show unprocessed event count. Out of scope for -A.

**POST /events/{id}/complete**: remains as-is (always returns 410 since dispatch() is never
called). This endpoint is architecturally deprecated in the cursor model — there is no
`POST /events/{id}/complete` call path. It can be removed in a cleanup slice (-F or later).

---

## §7 event_bus.ack() Helper Re-Implementation

### Form

```python
def ack(ack_for: str, role: str):
    """Emit an ack event acknowledging receipt of ack_for event.

    event_poll.py calls this after writing each batch's last event to stdout.
    The harness ack-consumer advances cursor[role] to ack_for on receipt.
    Fire-and-forget like emit(). Safe to call multiple times (idempotent cursor).
    """
    if not ack_for or not role:
        return
    emit("ack", role, payload={"ack_for": ack_for, "role": role})
```

### Caller

`event_poll.py` — called after the per-event loop completes (or after the nudge line is written
in the ultra-thin model). Not called by agent code — agents have no visibility into ack mechanics.

### Schema alignment question (§9 Q1)

The vault decision locks `payload = {ack_for, role}`. The task prompt specifies
`payload = {advance_to, role}`. These are semantically equivalent but textually different. The
event_catalog.py RECOGNIZED entry uses `{event_id, result}` — a third incompatible schema.

The choice between `ack_for` and `advance_to` has behavioral implications:
- `ack_for`: points AT the last tended event (cursor = this value). "I acked event X."
- `advance_to`: points AT the last tended event (cursor = this value). "Advance cursor to X."

Both encode the same information differently. `advance_to` is more explicit about the
harness-side operation; `ack_for` is more explicit about the event-bus receipt semantics.

**Recommendation**: use `ack_for` (vault-locked), update the catalog entry to match. The
harness ack-consumer sets `cursor[role] = ack_for`. The task prompt's `advance_to` naming should
be treated as the umbrella's informal description; the vault is authoritative.

---

## §8 Recommended Approach + Reasoning

### Recommended implementation sequence for -A:

**Step 1 — EventLifecycleManager cursor support**:
- Add `_cursors: dict[str, str]` to `EventLifecycleManager.__init__`.
- Add `advance_cursor(role, event_id)` method: sets `_cursors[role] = event_id`, calls
  `_persist()` wrapped in `to_thread` (or accepts an asyncio context flag).
- Add `get_cursor(role) -> str | None` method: returns `_cursors.get(role)`.
- Extend `_persist()` to include `"cursors"` key in the JSON output.
- Extend `load()` to restore `_cursors` from .event-state.json.

**Step 2 — GET /events/cursor/{role} endpoint**:
- New thin endpoint. Reads `event_lifecycle.get_cursor(role)`. Returns `{cursor, role}`. Null
  cursor = first boot (caller should start at tip).
- `_validate_role(role)` call at start (consistent with other role-scoped endpoints).

**Step 3 — event_catalog.py update**:
- Move `"ack"` from RECOGNIZED to EMITTED tier (event_poll.py will actively emit it).
- Update payload_fields to `["ack_for", "role"]`.
- Update description: "event_poll.py acks event delivery — advances harness cursor for role."
- Update source: "event_poll.py".

**Step 4 — Harness ack-consumer (extend existing inline handler)**:
- At harness.py:1534 (the existing `if event_type == "ack":` block), extend to:
  1. Read `ack_for` from `body["payload"]["ack_for"]` (replacing `event_id` key).
  2. Call `await asyncio.to_thread(event_lifecycle.advance_cursor, role, ack_for)`.
  3. Keep the existing `event_lifecycle.ack(ack_for, role)` call to maintain in-flight clearing
     for any events that were dispatched via the old path (defensive no-op if in-flight is empty).
  4. Keep the `stop-confirmed` branch unchanged.
- Remove the old `event_id` key lookup; use `ack_for` exclusively.

**Step 5 — event_bus.ack() helper**:
- Add `ack(ack_for: str, role: str)` to `references/scripts/event_bus.py`.
- Thin wrapper around `emit("ack", role, payload={"ack_for": ack_for, "role": role})`.

**Step 6 — event_poll.py cursor migration**:
- Add `_resolve_cursor_from_harness(role, port)` that calls `GET /events/cursor/{role}`.
- Modify `_resolve_cursor` to query harness first (null cursor → tip bootstrap).
- After each event's stdout write, call `event_bus.ack(event_id, role)` (fire-and-forget).
- Remove `_write_cursor_atomic` calls (cursor ownership moves to harness).
- **Backward compat**: keep working-state.md fallback for harness-unreachable case during
  transition, or remove and let the poll fail cleanly (harness is required in event-driven mode).

### Atomicity and concurrency

- `advance_cursor(role, event_id)` is called from thread pool (via to_thread). It acquires
  `self._lock` before mutating `_cursors`. Same lock discipline as `ack()`.
- Multiple agents emitting acks simultaneously: each call acquires `self._lock` independently.
  The last writer for a given role wins — this is correct because acks are monotonically
  increasing (each ack_for is a later event than the previous). If two acks arrive out of order
  (race between two event_poll.py invocations for the same role), the cursor may advance to an
  older event. Mitigation: compare event IDs before advancing (only advance if ack_for >
  cursor[role]). See §9 Q3 for ID ordering semantics.
- Atomicity of cursor advance + persist: both happen inside `advance_cursor()` under the lock.
  If persist fails (OSError), `_persist()` swallows the error (line 685: `except OSError: pass`).
  Cursor advances in-memory but not on disk. On harness restart, cursor reverts to last
  persisted value — agent re-delivers events from that point. This is acceptable at-least-once
  semantics.

### Evicted ack

If ack arrives with `ack_for` pointing to an event no longer in the deque (evicted):
- `advance_cursor(role, ack_for)` still sets `cursor[role] = ack_for`. The cursor is a string
  ID — it does not need to reference a live deque entry.
- Next `GET /events/for/{role}?since=ack_for` will get the eviction response if ack_for predates
  the retained window. event_poll.py handles this via the existing eviction path.
- **Cursor still advances** — the ack is valid even for evicted events. The agent tended that
  event; the cursor moves forward. This is the correct behavior.

---

## §9 Open Questions for PM/Human

**Q1 — CRITICAL: payload schema conflict between vault, prompt, and catalog**:
- Vault decision locks: `{ack_for, role}` — "I acked event with ID ack_for."
- Task prompt (9873-A scope) specifies: `{advance_to, role}` — "advance cursor to this ID."
- Current catalog RECOGNIZED entry: `{event_id, result}` — old schema, clearly wrong.

These are semantically equivalent but the field name matters for the harness ack-consumer
(it reads the field by name). **PM must lock one name before dev pickup.** Recommendation: use
`ack_for` (vault-authoritative). The task prompt's `advance_to` appears to be an informal
restatement. If human wants `advance_to` as the canonical name, the vault note must be updated.

**Q2 — Does event_poll.py ack ONCE per nudge or ONCE per event?**:
Vault consumption chain diagram shows event_poll.py emitting ack after each event in the loop.
The task prompt says "batched ack ONCE per nudge with payload `{advance_to: last_tended_event_id, role}`."
These are different designs:
- Per-event ack: N ack events per nudge. Cursor advances N times.
- Per-nudge ack: 1 ack event per nudge. Cursor jumps to last event in batch.

Per-nudge is more efficient (1 emit instead of N) and matches the Kafka consumer-group commit
model (commit offset = last consumed message). Recommend per-nudge. Dev should implement the
per-event loop but emit a single ack at the end with the last event's ID.

**Q3 — Event ID ordering: can harness compare IDs to enforce monotonic cursor advance?**:
Event IDs are 16-char hex hashes (content + nonce, per `event_bus.py:_generate_id`). They are
NOT monotonically ordered by value — they are random within the deque. The deque is ordered by
insertion time. Harness cannot compare `ack_for > cursor[role]` lexicographically.

Two options:
- Accept non-monotonic acks (last write wins, even if it's an older event). Very unlikely in
  practice — event_poll.py processes events sequentially.
- Add a sequence number to events and compare on sequence number. This is a larger schema change.

Recommendation for -A: accept last-write-wins. Document as known limitation. -B can add
sequence numbers if out-of-order ack becomes a real problem.

**Q4 — Remove working-state.md cursor or keep as fallback?**:
After -A ships, `event_poll.py` reads cursor from harness. If working-state.md cursor remains,
there are two cursor sources. Options:
- Remove working-state.md cursor writes entirely in -A (clean cutover).
- Keep working-state.md cursor as a deprecated fallback during -A and remove in -B.

If harness is unreachable, event_poll.py already fails with exit 2 (Monitor exits, session
exits). There is no degraded mode where working-state.md fallback helps. Recommendation: clean
cutover in -A — remove `_write_cursor_atomic` from event_poll.py. The `--(harness-unreachable)→
exit 2` path already handles this.

**Q5 — Does the existing `stop-confirmed` ack branch at harness.py:1544 stay as-is?**:
This branch fires when `payload.result == "stop-confirmed"`. It is orthogonal to cursor
advancement. In the new schema (`{ack_for, role}`), the payload has no `result` field. The
stop-confirmed logic needs to be preserved through a different mechanism. Options:
- Keep both payload schemas valid (ack can have optional `result` field).
- Move stop-confirmed to a separate event type (`stop-acked`).

Recommendation: keep `result` as an optional field in the ack payload. The vault schema
`{ack_for, role}` is the minimum; `result` is additive. This preserves the stop-confirmed path
without a new event type. Dev must check this during implementation.

**Q6 — Test coverage: harness.py:1951–1971 `test_does_not_dispatch` and related**:
RESEARCH-9873 §2.6 noted that `test_does_not_dispatch` and `test_endpoint_does_not_touch_lifecycle_state`
are inverted forms from the #9741 strip. In the new model (dispatch() still stripped, cursor
advanced via ack), these tests remain correct — they assert dispatch() is NOT called at GET
/events/for/{role}. No inversion needed for -A. Confirm this analysis before dev pickup.

---

## §10 Out of Scope for -A (Deferred to -B/-C/-D/-E/-F)

- **-B: timeout_scan re-delivery** — detect cursor staleness and re-emit the original event.
  Requires redesigning timeout_scan() to use cursor age, not per-event dispatch times. The
  timeout_scan() thread keeps running but still finds nothing (no `_in_flight` entries) until -B.
- **-C: TUI hook** — surfacing per-agent cursor position and ack progress in the terminal UI.
- **-D: event_poll.py ultra-thin nudge model** — full refactor of event_poll.py to the
  "detect anything past cursor? → write one stdout nudge line" model. -A only needs the cursor
  read + ack emit; the rest of event_poll.py logic is unchanged.
- **-E: agent-side reads via GET /events/for/{role}?since=cursor** — the agent reading its own
  event range and deciding per-event whether to care. This is an agent contract change; -A only
  wires the harness side.
- **-F: remove POST /events/{id}/complete** — endpoint is architecturally deprecated in the
  cursor model. Remove in cleanup slice after -E is live.
- **Event persistence across harness restart** — today only the last 200 events are persisted.
  At-least-once across full harness outages requires full event persistence. Phase 5, not pre-flip.
- **Sequence numbers on events** — needed for monotonic cursor comparison. Deferred to -B or later.
- **`GET /events/lag/{role}`** — shows unprocessed event count (deque_head - cursor[role]).
  Useful for TUI and alerting. Deferred to -C.
- **Re-implementing dispatch() at GET /events/for/{role}** — explicitly NOT restored in -A.
  The #9741 strip stays. Cursor obsoletes per-event in-flight tracking. dispatch() restoration
  would re-introduce H6 wedge pressure and event-state.json bloat for no gain.
- **Sub-skill doc updates** — `event-driven-workflow.md` and `cursor-management.md` need updating
  to reflect harness-owned cursor. Deferred to -D or -E when the agent contract changes.
- **`_execute_transition`/`_execute_comment` H4 wedge fix** — the subprocess.run calls inside
  `complete_event` remain unwrapped. Since the endpoint always returns 410 (no in-flight events),
  these are unreachable. RESEARCH-9874 Option A tracks this.

---

## Changelog

- 2026-05-21 — Created by pm-research-agent. Foundation slice of #9873 umbrella.
