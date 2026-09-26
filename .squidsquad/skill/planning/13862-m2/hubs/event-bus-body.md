
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

## Distilled leaves (vault v2)

- [[learning-broadcast-deque-cannot-have-in-stream-gaps]]
- [[learning-ead-status-routing-and-back-transition-dedup]]
- [[learning-monitor-persistent-do-not-rearm-per-nudge]]
- [[learning-post-outage-boot-drain-repeated-assigned-to]]
- [[learning-single-emit-wake-nudge-needs-bounded-reemit-and-must-bypass-time-filter]]
- [[learning-strip-vs-wire-audit-findings]]
- [[learning-wire-format-specs-triplicated-across-trds]]
- [[pattern-verify-egress-guard-on-the-wire]]

## Changelog

- **2026-09-26** — migrated to vault v2 (#13862).
