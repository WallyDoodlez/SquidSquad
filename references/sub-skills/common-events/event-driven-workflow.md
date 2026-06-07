---
slot: instructions
ordinal: 12
---

## Event-Driven Workflow

You are a persistent agent session driven by events from the harness. You react to one event at a time, consult the forge as the source of truth, and POST `ack-cursor` to the harness after each tended event so it advances your cursor in `.event-state.json`.

This fragment is a brief orientation. The full agent contract lives in the companion event-mode fragments — read them in this order:

1. **[[event-mode-contract]]** — boot sequence (Case A), event reactions (Cases B–E), case-precedence rule, working-state ownership discipline. Harness-loss recovery is handled by `common/boot-bootstrap.md` (polling-mode fallback at boot, #9588), not inline degraded mode.
2. **[[cursor-management]]** — harness-owned cursor in `.event-state.json`; agent reads via `GET /events/cursor/{role}` and advances via `POST /events ack-cursor` per tended event; gap handling (long lag, eviction).
3. **[[forge-read-pattern]]** — why the forge is the source of truth and how to read it before acting.
4. **[[idle-cooldown-loop]]** — what an event-mode agent does when `work_queue()` is empty.
5. **[[comment-handling]]** — comments are NOT event triggers; DM end-of-task exception; transition-on-handoff rule.

### Quick reference

- **Wake mechanism** — Monitor tool streaming `python references/scripts/event_poll.py <role> --wait 5 --target`. Each line of stdout is one JSON event.
- **Atomic unit of work** — one event at a time. Process to completion before reading the next.
- **Source of truth** — the forge (`tracker.py` queries). Event payloads are hints; always forge-read before acting.
- **Cursor** — harness-owned in `.squidsquad/.event-state.json`; you advance it by POSTing `ack-cursor {event_id, role}` after each tended event (see [[cursor-management]]).
- **Idle** — improvement-scan cool-down loop (see [[idle-cooldown-loop]]).
- **Handoff** — status transitions and label changes wake the stream; bare comments do not (see [[comment-handling]]).

### Error handling

If the harness becomes unreachable mid-session, the agent does NOT pivot to forge-direct work — this is a **manual-recovery scenario**: keep retrying `bootup-complete` at the 5-minute-capped backoff; the operator restarts the agent; on restart the boot bootstrap (`common/boot-bootstrap.md`) detects the unreachable harness and routes to polling mode (#9588). Mid-session degraded operation was removed in #9588.

`event_poll.py` handles transient HTTP errors (5xx, `ConnectionError`, `Timeout`, `IncompleteRead`) automatically with exponential backoff. 4xx responses are treated as caller faults and exit non-zero.

### Context pressure

The harness monitors agent context pressure files and emits `stop-requested` when a restart is needed. Honor `stop-requested` at the next task boundary (see Case E in [[event-mode-contract]]); the harness handles the respawn.
