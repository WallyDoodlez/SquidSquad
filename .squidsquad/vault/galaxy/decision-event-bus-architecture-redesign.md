---
name: decision-event-bus-architecture-redesign
description: Locked architectural principles for the event-bus redesign — harness as transport-only bus, forge as work-state source of truth, ack as event-type on the bus, cursor managed server-side
metadata:
  type: decision
type: decision
tags: [event-bus, harness, architecture, ack, cursor, monitor]
created: 2026-05-21
updated: 2026-05-21
owner: pm
status: active
confidence: high
source: conversation
links: [decision-phase-4-event-ack-lifecycle-deferred, learning-strip-vs-wire-audit-findings, learning-broadcast-deque-cannot-have-in-stream-gaps]
---

# Event-bus architecture — locked principles (cycle 1541-1542)

## Core principles (locked by human directive)

1. **Harness is a transport bus, not an orchestrator.** It moves events between producers and consumers. It does NOT track work completion, ticket state, or workflow status.
2. **Forge (GitHub Issues) is the source of truth for work state.** Status labels, comments, PR merges = the project's institutional state. Harness has no opinion on whether work is done.
3. **Agent owns work completion.** The agent acts on events; what it does with them is between the agent and the forge.
4. **Ack = receipt confirmation, NOT completion confirmation.** "Ack" means "the event was delivered to the agent's session." It does not mean "the agent finished processing."
5. **No `POST /events/{id}/complete` endpoint.** Reject any design that adds endpoints for completion state. The bus pattern uses events, not RPC, for state transitions.

## Implementation contract

### Ack as event-type
- Ack is a new event type emitted on the bus: `event_type="ack"`, payload `{ack_for: <original_event_id>, role: <self>}`.
- The harness watches its own deque for `ack` events (new consumer task) and updates per-role state on receipt.
- The deleted `event_bus.ack()` (in #9813) was reaching for this pattern correctly — its restoration is the right move.

### Ack is emitted by `event_poll.py`, NOT by the agent
- "Agent received the event" = "event was written to stdout, Monitor turned it into a task-notification, agent's session was woken."
- That boundary lives inside `event_poll.py` — the gateway process running as Monitor's stdin source.
- After `event_poll.py` writes the JSON line to stdout, it POSTs the ack event. The agent itself never emits acks. It doesn't even know they exist.

### Cursor management moves to harness
- Today cursor lives in `.squidsquad/<role>/working-state.md` (agent-local).
- New: cursor is harness state (persisted with `.event-state.json` or sibling).
- New endpoint: `GET /events/cursor/{role}` — agent queries "where am I?"
- Cursor advances via ack-consumer in harness: ack arrives → cursor advances past `ack_for`.
- Clean cutover. No local-file fallback. Harness owns cursor as bus consumer-position state (Kafka/Redis-streams pattern).

### Monitor contract is unchanged
- `event_poll.py --wait 5 --target` invocation stays the same.
- Each stdout line = one task-notification = one agent wake.
- Monitor exit = session exit (per #9742).
- The redesign happens INSIDE `event_poll.py` and the harness; the agent's boot contract and Monitor wiring are untouched.

## Consumption chain (after redesign)

```
[ harness in-memory deque ]
        │
        │ HTTP GET /events/for/{role}?since=<harness-cursor>
        ▼
[ event_poll.py --wait ]
   │  for each event:
   │    1. write JSON line to stdout
   │    2. POST event_type="ack" with payload={ack_for, role}
   │  cursor query: GET /events/cursor/{role}  (harness owns)
   ▼
[ Monitor tool ] (persistent across cycles)
   ▼
[ agent session ]  reacts per role's reacts-to config

[ harness ack-consumer task ]  watches own deque for event_type=ack
   ▼
   - clear in-flight for ack_for
   - advance per-role cursor
   - update "agent notified" record (TUI hook later)
```

## Persistence facts that constrain the redesign

- **Events live in `collections.deque(maxlen=1000)`** — in-memory only. Harness restart drops the event history. At-least-once across restarts requires event persistence — separate, larger work.
- **`.event-state.json`** persists in-flight + dispatch_times + retry_counts metadata. Cursor migration adds per-role cursor here (or sibling file).
- **`timeout_scan()`** (sync, async-task-wrapped) runs every 30s. Today logs only. Real re-delivery (re-emit the original event from deque) is in scope for the redesign — but bounded by deque retention (~1000 events).

## Pre-flip blocker structure

#9873 (umbrella for the ack/cursor restore) splits into:
- **#9873-A**: cursor migration to harness + `GET /events/cursor/{role}` endpoint + ack event type + harness ack-consumer task → cursor-advance on ack receipt. **Pre-flip blocker.**
- **#9873-B**: `timeout_scan()` re-delivery — re-emit the original event when cursor stalls past N seconds. **Pre-flip blocker.**
- **#9873-C**: TUI hook surfacing per-agent ack progress. **Post-v1.**

#9874 (harness arch wedge hazards) and #9875 (vault L2) explicitly deprioritized by human cycle 1542 — alignment-first.

## Open architectural questions (not blocking the locks above)

- **Event persistence across harness restart**: today none. Adding it makes at-least-once real across full outages. Out of scope for #9873 but flagged as Phase 5.
- **TUI ack visualization scope**: timing + which states surface (sent / acked / overdue / re-delivered).
- **Re-delivery bounded by deque eviction**: if the original event was evicted before re-delivery fires, what does timeout_scan do? Log + drop, or escalate? (#9873-B locks this.)

## Why this matters (the lesson chain)

This decision corrects the local-optimization trap captured in `learning-strip-vs-wire-audit-findings` (cycle 1541). The #9741 and #9813 strips removed working bus-pattern infrastructure (`dispatch()`, `event_bus.ack()`) because no consumer existed yet. The right move was to ADD the consumer — exactly what this decision locks. The strips have to be reverted as part of #9873-A.

The `event_bus.ack()` emit-to-stream pattern that was deleted in #9813 — research at the time framed it as "architecturally wrong." This decision corrects that framing: emit-to-stream was the right pattern; what was missing was a server-side consumer of those ack events. That gap is what #9873-A fills.

## Changelog

- 2026-05-21 — Created by pm-lead. Captures the architectural alignment built across cycles 1541-1542 via human directive and PM reflection. Supersedes the Path A vs Path B framing in `decision-phase-4-event-ack-lifecycle-deferred` (which contemplated `POST /events/{id}/complete` as Path B; this decision rejects that path entirely).
