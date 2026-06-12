---
slot: instructions
ordinal: 13
---

## Forge-Read Pattern

**The forge is the source of truth. The event stream is a wake-up signal, not state.**

Every decision consults the forge before acting. This is the rule that lets the harness remain a pure broadcast pipe and lets agents recover correctly from any sequence of crashes, evictions, or out-of-order delivery.

### When You Receive An Event

1. **Wake.** `event_poll.py` delivered a `NUDGE` (no payload) to stdout; `GET /events/for/{role}?since=<cursor>` and take the next event.
2. **Read the event payload.** Treat it as a hint about what may have changed on the forge.
3. **Forge-read.** Query the forge via `tracker.py` for the referenced item (and/or `work_queue(<role>)` for your role's queue). The forge tells you the actual current state.
4. **Act on what the forge says**, not on what the event payload said. The event may be stale (delayed delivery, repeated delivery during gap recovery, etc.).

After you tend each event (steps 1-4 above), you MUST POST `ack-cursor {event_id, role}` to the harness — the cursor does NOT advance automatically. `event_poll.py` only emits a wake `NUDGE`; it never touches the cursor. The harness cursor (in `.event-state.json`) advances only when the agent POSTs `ack-cursor` for the event it just finished (see [[cursor-management]] for the wire shape; see [[event-mode-contract]] for the per-event loop). Skipping the POST leaves the cursor stuck at the boot position; every event re-delivers on the next restart.

### Why

- Events can be **stale, duplicated, or out-of-order**. The forge is consistent.
- The harness has **no dispatch logic** and no per-role queue — it can broadcast the same event twice during reconnects or eviction recovery without harm, because every agent forge-reads anyway.
- **Crash recovery** is trivial: on restart, the agent reads working-state, forge-reads any in-progress task, and resumes — no special replay protocol needed.
- **Mid-task events** (Case D in [[event-mode-contract]]) are absorbed by the next forge-read at task completion. The agent never needs an in-memory event queue.

### `work_queue()` Semantics

`tracker.py list-tasks <role> --status approved` (and equivalent issue queries) is the forge query that backs `work_queue()`. It returns the current queue from the forge, ordered by priority/severity, every time. The agent does NOT cache the queue across events — re-reading is cheap and the forge is authoritative.

### `tracker.py get-state <number>`

Use this whenever you need to confirm an item's current status, role assignment, or labels before acting. Example: on boot, after reading an in-progress task from working-state, you call `get-state` to confirm the forge still has it in-progress and assigned to you. If the forge says otherwise, drop the task and fall through to `work_queue()`.
