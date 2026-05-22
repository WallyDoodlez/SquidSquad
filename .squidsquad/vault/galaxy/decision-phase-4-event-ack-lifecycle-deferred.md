---
name: decision-phase-4-event-ack-lifecycle-deferred
description: Event ack/retry/in-flight lifecycle was intentionally deferred to "Phase 4". Today cursor-advance is the implicit delivery signal; retry on processing failure does not exist.
metadata:
  type: decision
type: decision
tags: [event-bus, harness, lifecycle, ack, phase-4, deferred-work]
created: 2026-05-21
updated: 2026-05-21
owner: pm
status: active
confidence: high
source: review
links: [learning-strip-vs-wire-audit-findings, learning-broadcast-deque-cannot-have-in-stream-gaps]
---

# Event-mode ack/retry lifecycle is intentionally deferred (Phase 4)

## Original design intent

The event-bus + harness were built with these moving parts working together:

- `EventLifecycleManager.dispatch(event_id, role)` — marks an event as in-flight in `.event-state.json` when it's delivered to an agent
- `EventLifecycleManager.ack(event_id, role)` — clears the in-flight entry after the agent finishes processing
- `EventLifecycleManager.timeout_scan()` — every 30s scans for in-flight entries past 10min; logs timeouts; eligible for retry
- `POST /events/{event_id}/complete` — endpoint for the agent to invoke ack after processing

Wired together: **at-least-once delivery with retry on no-ack**. Harness knows whether each agent actually received and processed each event; events lost to a crash or hang get redelivered.

## Current state (cycle 1539+)

The full lifecycle was never wired end-to-end. Two cleanups stripped the working infrastructure rather than completing it:

- **#9741 (cycle 1538)** stripped the `dispatch()` call from `GET /events/for/{role}` because nothing was emitting acks → in-flight entries accumulated forever
- **#9813 (cycle 1539)** deleted `event_bus.ack()` as a "dead stub" with no caller

Today's de-facto signal: cursor advance in `event_poll.py` after each event is read from stdout. This means:
- "Delivered" = "agent's `event_poll.py` wrote the event to stdout"
- "Received and processed" = **unknowable** — no signal travels back to the harness
- "Retry on failure" = **does not exist** — a crashed agent mid-processing silently loses events

## Why deferred

Each strip was locally rational (the code was dead) but architecturally regressive. The reasoning chain in CONTEXT-9741 D1 was "simplest; dead Phase 4 plumbing with no consumer." See [[learning-strip-vs-wire-audit-findings]] for the broader lesson.

The deferred work was renamed "Phase 4 lifecycle wiring" in CONTEXT-9741 D4 and #9813 body. No tracker item exists for it as of cycle 1539. Whenever the project decides to restore the original guarantees, the work involves either:

- **Path A (smaller)**: re-add `dispatch()` to the polling endpoint + add cursor-advance-as-ack POST to `event_poll.py` + restore `event_bus.ack()` (which now needs to be re-implemented since the stub was deleted)
- **Path B (cleaner)**: design an explicit ack contract — agents POST `/events/{id}/complete` after successful processing, with a richer state machine separating delivered/received/processed/acked

Path A is closer to the original code shape. Path B is the longer-term direction implied by the "Phase 4" language.

## Implication for related work

- **#9845 (noop stress-test event)** was scoped as a closed noop/noop-ack emit pair because the general ack mechanism doesn't exist. Once Phase 4 lands, #9845's CLI should be retrofitted to use the real ack path so latency measurements reflect actual delivery semantics, not an artificial echo.
- **Any new feature relying on "agent finished" signal** must invent its own mechanism today or wait for Phase 4.
- **Polling mode is unaffected** — there's no ack contract in polling mode by design; agents read tracker on each cycle.

## Triggering signals to revisit

- Operator observes an event loss (only detectable as a missed status transition or skipped reaction)
- New feature requires end-to-end delivery confirmation
- Event-mode flip surfaces latency or loss patterns that need observability
- Human directs Phase 4 to begin

## Changelog

- 2026-05-21 — Created by pm-lead. Captures the current state of event-ack/retry deferral so future agents on this topic understand the temporary nature of #9741+#9813 strips.
