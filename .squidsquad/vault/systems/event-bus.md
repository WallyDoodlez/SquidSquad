---
type: system
tags: [event-bus, events, architecture]
created: 2026-07-20
updated: 2026-07-20
status: active
owner: shared
---

# Event Bus

_Hub note (VAULT-ARCH 3.2): connective anchor for this subsystem. Keep it a
map, not an essay -- galaxy leaves carry the knowledge; this note carries
the links._

## What It Is

The harness's broadcast deque + cursor model: agents GET events past their cursor, ack per event; nudges wake, the forge is truth. At-least-once, eviction-tolerant.

## Key Files

`references/scripts/event_bus.py`, `references/scripts/event_poll.py`, `.squidsquad/.event-state.json`, `docs/AGENT-RUNTIME.md` (SS8)

## Knowledge Map

- Architecture: [[decision-event-bus-architecture-redesign]], [[decision-phase-4-event-ack-lifecycle-deferred]]
- Mode-agnostic fragments: [[learning-common-events-fragments-are-mode-agnostic]]
