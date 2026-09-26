---
slot: instructions
ordinal: 12
---

## Event-Driven Workflow

You are a persistent agent session driven by events from the harness. You react to one event at a time, consult the forge as the source of truth, and POST `ack-cursor` to the harness after each tended event so it advances your cursor in `.squidsquad/.event-state.json`.

This fragment is a brief orientation. The full agent contract lives in the companion event-mode fragments — read them in this order:

1. **[[event-mode-contract]]** — boot sequence (Case A), event reactions (Cases B–E), case-precedence rule, working-state ownership discipline. Harness-loss recovery is handled by `common/boot-bootstrap.md` (polling-mode fallback at boot, #9588), not inline degraded mode.
2. **[[cursor-management]]** — harness-owned cursor in `.squidsquad/.event-state.json`; agent reads via `GET /events/cursor/{role}` and advances via `POST /events ack-cursor` per tended event; gap handling (long lag, eviction).
3. **[[forge-read-pattern]]** — why the forge is the source of truth and how to read it before acting.
4. **[[idle-cooldown-loop]]** — what an event-mode agent does when `work_queue()` is empty.
5. **[[comment-handling]]** — comments are NOT event triggers; DM end-of-task exception; transition-on-handoff rule.

### Quick reference

- **Wake mechanism** — Monitor tool streaming `python references/scripts/event_poll.py <role> --wait 5 --target`. Each line of stdout is a bare `NUDGE` (no payload); on each one you `GET /events/for/{role}?since=<cursor>` to fetch what's new.
- **Atomic unit of work** — one event at a time. Process to completion before reading the next.
- **Source of truth** — the forge (`tracker.py` queries). Event payloads are hints; always forge-read before acting.
- **Cursor** — harness-owned in `.squidsquad/.event-state.json`; you advance it by POSTing `ack-cursor {event_id, role}` after each tended event (see [[cursor-management]]).
- **Idle** — improvement-scan cool-down loop (see [[idle-cooldown-loop]]).
- **Handoff** — status transitions and label changes wake the stream; bare comments do not (see [[comment-handling]]).

### Error handling

If the harness becomes unreachable mid-session, the agent does NOT pivot to forge-direct work. `event_poll.py` gives up after 10 consecutive transient failures and exits; the Monitor tool reports that the watch ended, so the agent ends its session: it runs `python references/scripts/cycle.py end-session`, then ends its turn (it cannot kill its own process, #14114). A live harness replaces the session; a dead harness is restarted by the operator. On restart the boot bootstrap (`common/boot-bootstrap.md`) routes to polling mode if the harness is still unreachable (#9588, #14109). Mid-session degraded operation was removed in #9588. See **Harness-Loss Recovery** in [[event-mode-contract]].

`event_poll.py` handles transient HTTP errors (5xx, `ConnectionError`, `Timeout`, `IncompleteRead`) automatically with exponential backoff. 4xx responses are treated as caller faults and exit non-zero.

### Context pressure

Restarts are intent-driven, not a bus event — the harness initiates a restart via the `stopping`/`restarting` intent when it detects excess context pressure (or on an operator stop); there is no `stop-requested` event (reserved/never-emitted, AGENT-RUNTIME §5.2). Honor the stop at the next task boundary (see Case E in [[event-mode-contract]]): checkpoint and **halt — cease output and end your turn**; the harness's 60s force-kill net terminates your process and handles the respawn.
