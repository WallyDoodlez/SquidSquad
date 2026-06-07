---
slot: instructions
ordinal: 14
---

## Cursor Management

The cursor is the canonical work-completed indicator for your alias — single source of truth for "events I have tended." It advances only after you finish processing an event, whether you cared about it (ran the cycle wrapper) or skipped it via the care filter. Either way, finishing the event IS the cursor commit. There is no separate "I received this signal" ack. See `docs/AGENT-RUNTIME.md` §4.3 for the canonical model.

### Where the cursor lives

The cursor is **harness-owned**. It is persisted in `.squidsquad/.event-state.json` (one entry per alias) and you observe it only through the harness API — you never write the file directly. `working-state.md` does NOT carry a cursor line; that file holds your agent-private current-work state only (see `docs/AGENT-RUNTIME.md` §5).

> Pre-#11329 transitional note: a legacy install may still have a `- **Last Processed Event ID**: <id>` line in `working-state.md`. Leave it alone — #11329 retires the line in the runtime cleanup. Do not read, write, or rely on it for cursor decisions.

### How to read the cursor

Issue a GET against the harness:

```
GET /events/cursor/{role}
→ {cursor: <event_id> | null, role}
```

- `null` means first boot for this alias — read events from the head of the harness deque.
- Any other value is the last event id you successfully tended.

### How to advance the cursor — `POST /events ack-cursor`

After you finish processing an event (cared OR skipped — both count as "tended"), POST a single `ack-cursor` to the harness:

```
POST /events
{
  "type": "ack-cursor",
  "event_id": "<the id of the event you just tended>",
  "role": "<your alias>"
}
```

The harness's ack consumer task picks up the post, writes the new cursor value to `.event-state.json`, and returns `200 OK`. **One ack per tended event** — this is the canonical agent loop documented in `docs/AGENT-RUNTIME.md` §7.1. There is no batched end-of-walk ack.

Cursor-regression attempts (ack for an event id earlier than the current cursor) are rejected by the harness (CONTEXT-9873-A D15). Treat a non-200 from the ack POST as a transient error and retry per the usual HTTP-error policy; do not advance any local state on failure.

### Gap scenarios

Two kinds of cursor gap can appear:

- **Long lag.** Your cursor is hundreds or thousands of events behind. Walk each event individually through the canonical §7.1 loop — do not jump straight to latest. Each event passes through the same care-filter + per-event-ack discipline as a normal walk: cared events still fire the cycle wrapper (though the wrapper's work is typically a no-op because the forge already reflects the post-event state); skipped events advance the cursor with no wrapper.
- **Eviction gap.** Your cursor predates the oldest retained event in the harness deque. `GET /events/for/{role}?since=<old>` returns `HTTP 410 Gone` with body `{"cursor_evicted": true, "current_head": "<event_id>"}`. Recovery: read the forge for current state, emit a single `ack-cursor(current_head)` to fast-forward the cursor, then re-enter idle. Do NOT crash, do NOT walk the evicted range — those events are unrecoverable from the bus by design.

> **Dropped scenario (#9265)**: a third "in-stream gap" scenario (missing event between two retained ids) was specified in the original CONTEXT-8694 draft and dropped. The current broadcast model is a single in-process `collections.deque` populated by `POST /events`; `GET /events/for/{role}?since=<cursor>` does a linear scan over that deque, so two retained events cannot have a missing event between them by construction. The scenario would only become reachable if the harness ever moved to a multi-process pipeline with intermediate acks — at that point this section should be updated.

### Crash recovery

At-least-once delivery: the cursor advances only after a successful ack. If you crash mid-event, the cursor sits at the **last successfully-acked event** — every event past it, including the in-flight one at crash time, re-delivers on the next §7.1 loop iteration's GET. On restart you do nothing cursor-specific: the boot bootstrap routes you back into the §7.1 eager loop, which reads your cursor via `GET /events/cursor/{role}`, fetches events past it via `GET /events/for/{role}?since=<cursor>`, and walks them with per-event acks.

There is no agent-side cursor file to recover from. The atomic-write (`.tmp` + `mv`) discipline from the pre-#11328 model no longer applies — the harness's ack consumer is the single writer of `.event-state.json` and it handles its own durability.
