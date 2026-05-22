# CONTEXT-9873-A — Cursor Migration to Harness + Ack Event Type + Harness Ack-Consumer Task

**Issue**: #9873-A (foundation slice of #9873 umbrella)
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-21
**Status**: planning → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: `.squidsquad/pm/planning/CONTEXT-9873-A.md`. Read this artifact in full before pickup. The bullets in the issue body are a summary; this planning artifact is the contract.

> **FOUNDATION SLICE**: #9873-A is the pre-flip blocker that -B (event_poll nudge-only), -C (agent contract), -D (subloop), -E (timeout re-nudge), and -F (TUI) all build on. Nothing in those slices can be correctly wired until cursor state lives in the harness and the ack-consumer is running.

---

## Authoritative Scope Statement

#9873-A delivers three tightly coupled changes that must ship together:

1. **Harness-owned cursor state** — add `_cursors: dict[str, str]` to `EventLifecycleManager`; persist alongside in-flight tracking in `.event-state.json`.
2. **`GET /events/cursor/{role}` endpoint** — returns `{"cursor": null | str, "role": str}` at 200 always.
3. **Ack event type split + harness ack-consumer** — replace the single `event_type=ack` with two types (`ack-cursor` and `ack-stop`); extend the inline handler at `harness.py:1533-1558` to advance the cursor on `ack-cursor` receipt; add `event_bus.ack_cursor()` and `event_bus.ack_stop()` helpers in `event_bus.py`.

Scope boundary: this slice wires the harness side only. The agent-side contract for emitting `ack-cursor` (when and how `event_poll.py` calls it) is deferred to -C. event_poll.py changes beyond what is strictly required to emit the new event types are deferred to -B.

---

## §1 Locked Decisions

### D1 — Foundation slice identity (LOCKED)

This is #9873-A. It ships before -B/-C/-D/-E/-F. It is a pre-flip blocker. No later slice can be correctly implemented without this foundation. Do not bundle -B or later concerns into this PR.

### D2 — Ack handler approach: extend existing inline handler (LOCKED)

Extend the already-partially-wired inline handler at `harness.py:1533-1558`. Do NOT add a new endpoint for ack processing. Do NOT use `POST /events/{id}/complete` (rejected pattern — vault note `decision-event-bus-architecture-redesign` §core-principles). The inline path on `POST /events` is already present and is the correct extension point.

### D3 — Cursor state location: `_cursors` dict on `EventLifecycleManager` (LOCKED)

Add `_cursors: dict[str, str]` to `EventLifecycleManager.__init__`. Persist in `.event-state.json` alongside in-flight tracking (single state file, same persistence path). The key `"cursors"` is added to the JSON shape: `{"cursors": {"pm": "abc123", "skill": "def456"}}`. Load from the file on harness boot. Do NOT store cursors in `.harness-state.json` (that file owns agent lifecycle state, not event-bus consumer-position state).

### D4 — Cursor persist wrapped in `asyncio.to_thread` (LOCKED — H6 mitigation)

Cursor advance + persist must be wrapped in `await asyncio.to_thread(...)` at the call site in the inline ack-handler. This mitigates the H6 sync-file-I/O-on-event-loop hazard identified in RESEARCH-9874. Match the existing pattern at `harness.py:1530` (`await asyncio.to_thread(state.save_state)`). The HTTP response may return before cursor persist completes — fire-and-forget semantics are acceptable for ack.

### D5 — New endpoint: `GET /events/cursor/{role}` (LOCKED)

Shape: returns `{"cursor": null, "role": "<role>"}` when no cursor exists for the role (first boot), or `{"cursor": "<event_id>", "role": "<role>"}` when a cursor exists. HTTP status is 200 always — no 404. Call `_validate_role(role)` at entry (consistent with other role-scoped endpoints). Read `_cursors[role]` under `event_lifecycle._lock`.

### D6 — Event type split: `ack-cursor` + `ack-stop` (LOCKED — human Option 2)

The current shared `event_type=ack` at `harness.py:1534` is REPLACED by two distinct event types:

- **`event_type=ack-cursor`** (NEW): payload schema `{event_id: str, role: str}`. Emitted by agent infrastructure to advance the harness cursor past `event_id` for the given role.
- **`event_type=ack-stop`** (REPURPOSED from current `event_type=ack`): payload schema `{event_id: str, result: str}`. Preserves the existing stop-confirmed branch behavior at `harness.py:1547-1557` without change.

The old `event_type=ack` entry in `event_catalog.py` is REPLACED (not extended). Both new types are registered in the EMITTED tier of `event_catalog.py` with clear descriptions.

### D7 — Initial cursor: NULL on first boot (LOCKED — human direction)

When `_cursors` has no entry for a role (first boot, or role never seen), `GET /events/cursor/{role}` returns `{"cursor": null, "role": "<role>"}`. The absence of a cursor entry means "start from the beginning of the deque" (`since=null` → all available events). The entry is absent until the first `ack-cursor` arrives. Do NOT initialize cursors to the deque head on first boot.

### D8 — Evicted ack handling: REJECT silently (LOCKED — human direction)

If an `ack-cursor` arrives with an `event_id` that is no longer in the deque (FIFO-evicted), the ack-consumer REJECTS the cursor advance. Log the rejection at debug level. The cursor stays at its current value. Do NOT advance the cursor to a value that no longer references a valid in-deque event. Rationale: advancing past evicted events creates undefined replay semantics — the cursor must point to a verifiable position.

### D9 — `dispatch()` from #9741: do NOT restore (LOCKED)

The `dispatch()` strip from #9741 stays. Cursor state obsoletes per-event in-flight tracking. The ack-consumer advances `_cursors[role]` — it does not populate `_in_flight`. The `test_does_not_dispatch` and `test_endpoint_does_not_touch_lifecycle_state` tests remain correct and are not inverted.

### D10 — `event_bus.ack_cursor` + `event_bus.ack_stop` helpers (LOCKED)

Add two thin helpers to `references/scripts/event_bus.py`, both wrappers around `emit()`:

- `ack_cursor(event_id: str, role: str)` — emits `event_type="ack-cursor"`, payload `{"event_id": event_id, "role": role}`. Fire-and-forget. No-op if either arg is empty.
- `ack_stop(event_id: str, result: str)` — emits `event_type="ack-stop"`, payload `{"event_id": event_id, "result": result}`. Fire-and-forget. No-op if either arg is empty.

The deleted `event_bus.ack()` from #9813 is NOT directly restored — the two-helper split replaces it.

### D11 — Concurrency: hold lock during advance + persist (LOCKED)

The ack-consumer must hold `EventLifecycleManager._lock` during cursor advance and persist. Match the existing lock discipline in `EventLifecycleManager.ack()` at `harness.py:646-658`. Multiple concurrent `ack-cursor` events for the same role are serialized by the lock. Last-write-wins is acceptable (acks are monotonically increasing in practice; event IDs are not lexicographically ordered so no monotonic comparison is possible — see RESEARCH-9873-A §9 Q3).

### D12 — Compose pipeline + fixture regen in same PR (LOCKED)

Skill MUST run `compose.py deploy <all four roles>` and regenerate `tests/comprehension/8697_fixtures/*_events_CLAUDE.md` for all 4 roles in the same PR. Per `feedback_l1_l4_only` — all agent instructions composed from L1–L4; no ad-hoc instruction files outside the compose pipeline.

### D13 — CQ spec scope: catalog entries + endpoint shape only (LOCKED)

Per `feedback_comprehension_tests_required` — a CQ spec is required for any task adding/changing agent instructions. The agent contract for emitting `ack-cursor` is deferred to -C, so -A's CQ covers only: (a) the `ack-cursor` and `ack-stop` catalog entries and their payload schemas, and (b) the shape of `GET /events/cursor/{role}` responses (null vs present, always-200). The CQ spec is written by skill alongside the implementation; QA derives the formal test plan from it.

### D14 — event_poll.py cursor changes: deferred to -B (LOCKED)

event_poll.py changes (reading cursor from harness instead of working-state.md, removing `_write_cursor_atomic`, emitting `ack-cursor` after each batch) are deferred to -B. -A adds the helpers and catalog entries that -B will call, but does not modify event_poll.py call sites.

---

## §2 Grounded File References

| File | Lines | Change |
|------|-------|--------|
| `references/scripts/harness.py` | 610–658 | `EventLifecycleManager`: add `_cursors` dict, `advance_cursor()`, `get_cursor()` methods; extend `_persist()` + `load()` for cursor key |
| `references/scripts/harness.py` | 665–686 | `_persist()`: add `"cursors"` key to JSON output; keep same atomic-write pattern |
| `references/scripts/harness.py` | 1533–1558 | Inline ack-handler: split `event_type=ack` branch into `ack-cursor` branch (advance cursor via `to_thread`) and `ack-stop` branch (existing stop-confirmed logic, payload key renamed from `event_id` to match new schema) |
| `references/scripts/harness.py` | new endpoint after line ~1688 | `GET /events/cursor/{role}`: thin read under lock, returns `{cursor, role}`, 200 always |
| `references/scripts/event_catalog.py` | 138–142 | Replace `"ack"` RECOGNIZED entry with two EMITTED entries: `"ack-cursor"` and `"ack-stop"` |
| `references/scripts/event_bus.py` | end of file (after line 141) | Add `ack_cursor(event_id, role)` and `ack_stop(event_id, result)` helpers |
| `references/scripts/event_poll.py` | no changes | Deferred to -B |
| `tests/comprehension/8697_fixtures/*_events_CLAUDE.md` | all 4 roles | Regenerated by `compose.py deploy` in same PR |

---

## §3 Acceptance Criteria

**AC-1 (`_cursors` dict — presence)**: `EventLifecycleManager` has a `_cursors` attribute of type `dict[str, str]` initialized at `__init__`. The attribute is populated from `.event-state.json` on harness boot if the `"cursors"` key is present, and defaults to an empty dict if absent.

**AC-2 (`_cursors` — persistence)**: After an `ack-cursor` event is successfully processed, `.event-state.json` contains a `"cursors"` key whose value includes the updated `role → event_id` entry. The persist operation runs off the asyncio event loop (via `asyncio.to_thread` or equivalent). On harness restart, `_cursors` is restored from the persisted file.

**AC-3 (`GET /events/cursor/{role}` — null case)**: When no cursor exists for a role (first boot, or role has never sent `ack-cursor`), `GET /events/cursor/<role>` returns HTTP 200 with body `{"cursor": null, "role": "<role>"}`.

**AC-4 (`GET /events/cursor/{role}` — present case)**: After the harness processes an `ack-cursor` event for a role, `GET /events/cursor/<role>` returns HTTP 200 with body `{"cursor": "<event_id>", "role": "<role>"}` where `event_id` matches the value from the ack payload.

**AC-5 (`ack-cursor` catalog entry)**: `references/scripts/event_catalog.py` contains an EMITTED-tier entry for `"ack-cursor"` with payload fields `["event_id", "role"]` and a description identifying it as the cursor-advance signal emitted after event delivery.

**AC-6 (`ack-stop` catalog entry)**: `references/scripts/event_catalog.py` contains an EMITTED-tier entry for `"ack-stop"` with payload fields `["event_id", "result"]` and a description identifying it as the stop-confirmation signal. The old `"ack"` RECOGNIZED entry is removed.

**AC-7 (ack-consumer — cursor advance on valid receipt)**: When the harness receives a `POST /events` with `event_type="ack-cursor"` and a payload `{event_id, role}` where `event_id` is present in the in-memory deque, the harness advances `_cursors[role]` to `event_id` and persists the updated state. Subsequent `GET /events/cursor/<role>` reflects the new cursor.

**AC-8 (ack-consumer — evicted event_id rejected)**: When the harness receives `event_type="ack-cursor"` with an `event_id` that is no longer in the deque (FIFO-evicted), the cursor is NOT advanced. The cursor value returned by `GET /events/cursor/<role>` is unchanged from before the ack arrived. A debug-level log entry is emitted.

**AC-9 (cursor advance wrapped in to_thread)**: The cursor advance + persist operation in the ack-cursor handler path does not execute synchronous file I/O on the asyncio event loop. The `asyncio.to_thread` wrapper (or equivalent off-loop mechanism) is used, matching the pattern at `harness.py:1530`.

**AC-10 (`event_bus.ack_cursor` helper)**: `references/scripts/event_bus.py` exports `ack_cursor(event_id: str, role: str)` which emits `event_type="ack-cursor"` with payload `{"event_id": event_id, "role": role}` via `emit()`. Calling with empty `event_id` or `role` is a no-op (no exception raised). Fire-and-forget semantics — silent on failure.

**AC-11 (`event_bus.ack_stop` helper)**: `references/scripts/event_bus.py` exports `ack_stop(event_id: str, result: str)` which emits `event_type="ack-stop"` with payload `{"event_id": event_id, "result": result}` via `emit()`. Calling with empty args is a no-op. Fire-and-forget semantics.

**AC-12 (stop-confirmed branch compatibility)**: The existing stop-confirmed behavior — when payload contains `result == "stop-confirmed"` and agent intent is `INTENT_STOPPING`, the harness writes agent state — continues to work after the ack split. The `ack-stop` handler preserves this branch. No regression in stop-confirmation flow.

**AC-13 (CQ spec — catalog + endpoint)**: A comprehension-question spec is present in the PR (in `tests/comprehension/` or equivalent) covering: (a) the `ack-cursor` payload schema, (b) the `ack-stop` payload schema, (c) the `GET /events/cursor/{role}` response shape for null and non-null cursor cases. A fresh agent given only the modified catalog file and endpoint handler can correctly answer these questions from the source alone.

**AC-14 (compose pipeline)**: `python references/scripts/compose.py deploy <role>` runs successfully for all four roles (pm, skill, qa, dm) and the regenerated `tests/comprehension/8697_fixtures/*_events_CLAUDE.md` files are committed in the same PR. CI comprehension-fixture tests pass.

---

## §4 Out of Scope

The following are explicitly deferred and must NOT be bundled into this PR:

- **-B (event_poll nudge-only)**: Changes to `event_poll.py` polling logic, removing `_write_cursor_atomic`, reading cursor from harness instead of `working-state.md`, emitting `ack-cursor` from poll loop. Deferred to slice -B.
- **-C (agent contract)**: Agent-side reads-events-decides-acks contract; documenting when and how agents emit `ack-cursor`; changes to `event-driven-workflow.md` or `cursor-management.md` sub-skills. Deferred to slice -C.
- **-D (improvement subloop trigger)**: Any improvement subloop triggering on ack events. Deferred to slice -D.
- **-E (timeout re-nudge)**: `timeout_scan()` redesign to detect cursor staleness and re-emit the original event. The timeout scanner keeps running but continues to find nothing (no `_in_flight` entries) until -E. Deferred to slice -E.
- **-F (TUI)**: Surfacing per-agent cursor position and ack progress in the terminal UI. Post-v1. Deferred to slice -F.
- **Restoring `dispatch()`**: The #9741 strip stays. Per D9.
- **`GET /events/lag/{role}`**: Shows unprocessed event count (deque_head minus cursor). Useful for TUI and alerting — deferred to -C or later.
- **`POST /events/{id}/complete` removal**: Endpoint is architecturally deprecated but removal is a cleanup step deferred to a later slice after -C is live.
- **Event persistence across harness restart**: At-least-once across full harness outages requires full event persistence. Out of scope — Phase 5.
- **Sequence numbers on events**: Needed for monotonic cursor comparison. Deferred to -B or later.
- **working-state.md cursor removal from event_poll.py**: The `_write_cursor_atomic` removal and harness-cursor read in event_poll.py are -B work.

---

## §5 Sequencing

-A is the pre-flip blocker. The implementation sequence within -A:

1. Extend `EventLifecycleManager`: add `_cursors` dict, `advance_cursor(role, event_id)`, `get_cursor(role) -> str | None`; extend `_persist()` and `load()` for cursor key.
2. Add `GET /events/cursor/{role}` endpoint (thin read under lock, 200 always).
3. Update `event_catalog.py`: remove `"ack"` RECOGNIZED entry; add `"ack-cursor"` and `"ack-stop"` to EMITTED tier.
4. Extend inline ack-handler at `harness.py:1533-1558`: add `ack-cursor` branch (advance cursor via `to_thread`); rename existing `ack` check to `ack-stop`; preserve stop-confirmed branch.
5. Add `ack_cursor()` and `ack_stop()` helpers to `event_bus.py`.
6. Write CQ spec for catalog entries and endpoint.
7. Run `compose.py deploy` for all four roles; commit regenerated `*_events_CLAUDE.md` fixtures.
8. Verify CI passes. Ship as single PR.

**Foundation for subsequent slices**: -B reads cursor from `GET /events/cursor/{role}` (step 2 above). -C documents when agents call `ack_cursor()` (step 5). -D and -E build on the harness cursor state established in step 1. None of these can be correctly wired without -A.

---

## §6 Risk Notes for Skill at Pickup

1. **Ack-consumer is yet another async task on the loop**: the inline ack-handler at `harness.py:1533` runs on the hot `POST /events` path. Keep the persist call in `asyncio.to_thread` — do NOT let the disk write block the event loop. Match the existing pattern at line 1530 exactly.

2. **Cursor schema must match what -B will read**: -B's `event_poll.py` will call `GET /events/cursor/{role}` and interpret the `"cursor"` field. The field name and null semantics are locked in D5 and D7 — do not deviate. A mismatch here will silently break -B's cursor resolution.

3. **Existing stop-confirmed branch must survive the split**: The `ack-stop` branch is a repurpose, not a rewrite. The logic at `harness.py:1547-1557` (check `result == "stop-confirmed"`, check agent intent is `INTENT_STOPPING`, call `state.save_state` off-loop) must be preserved verbatim in the `ack-stop` handler. The only change is the event_type check: `ack` → `ack-stop`.

4. **Evicted-event rejection requires a deque membership check**: D8 locks rejection of ack-cursor for evicted event_ids. Skill must implement a deque membership lookup before advancing the cursor. The deque is `EventStream._stream` (a `collections.deque`) — the check must hold `EventStream._lock` (or use the existing `get_recent` API) to be safe. Do not advance and then check; check first.

5. **Payload field name**: -A locks `event_id` as the payload field for both `ack-cursor` and `ack-stop` (see D6 and D10). The vault note uses `ack_for`; the task prompt originally used `advance_to`. The locked schema in this CONTEXT uses `event_id` (consistent with the PM-locked decisions above and the existing inline handler's `ack_event_id` variable naming). Skill must NOT use `ack_for` or `advance_to` — those names appear in pre-lock research artifacts only.

6. **Lock ordering**: `advance_cursor` acquires `EventLifecycleManager._lock`. If it calls into `EventStream` (for the eviction check), that path acquires `EventStream._lock`. The existing `_persist()` already does this (line 665–686 comment in RESEARCH). Ensure the lock acquisition order is consistent with existing usage to avoid deadlock.

---

## §7 Open Questions Resolved

| Question | Resolution |
|----------|------------|
| Q1 (RESEARCH §9) — 3-way payload schema conflict: vault uses `ack_for`, prompt uses `advance_to`, catalog uses `event_id` | **Option 2 (human direction)**: split into two event types (`ack-cursor` and `ack-stop`), each with payload field `event_id`. The `ack_for` and `advance_to` names appear only in pre-lock research and vault; the locked schema uses `event_id`. |
| Q2 (RESEARCH §9) — Per-event ack or per-nudge ack | Deferred to -C (agent contract slice). -A wires the harness side only; the emission cadence is -C's concern. |
| Q3 (RESEARCH §9) — Event ID ordering for monotonic cursor comparison | Last-write-wins accepted for -A. Event IDs are 16-char random hex — not lexicographically ordered. Sequence numbers deferred. |
| Q4 (RESEARCH §9) — Remove working-state.md cursor or keep fallback | Deferred to -B. -A does not touch event_poll.py. |
| Q5 (RESEARCH §9) — stop-confirmed branch preservation | Preserved via `ack-stop` repurpose (D6). The `result` field remains in the `ack-stop` payload; the stop-confirmed check is unchanged. |
| Initial cursor value | **NULL on first boot (human direction)** — no cursor entry until first `ack-cursor` arrives. Endpoint returns `{"cursor": null, "role": "<role>"}`. Deque start-from-beginning semantics apply. |
| Evicted ack handling | **REJECT silently (human direction)** — cursor does not advance for evicted event_ids. Debug log emitted. Cursor stays at prior value. |

---

## §8 Next Step

PM transitions #9873-A `planning` → `planned`. Human reviews this CONTEXT-9873-A.md. On human approval, PM transitions `planned` → `approved`. Skill picks up.

Before PM transitions `planned` → `approved`, the pre-approval body-vs-CONTEXT sync check must pass: the GitHub issue body AUTHORITATIVE SCOPE banner must point at this file, and the body scope bullets must be consistent with §§ Scope, Locked Decisions, and Out of Scope above.
