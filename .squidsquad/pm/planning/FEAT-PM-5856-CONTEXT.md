# FEAT-PM-5856 Context — Status-Transition Events on Event Bus

## Scope

Make tracker.py transition() emit a `task-transition` event on every successful status transition. Replace the dead `task-start`/`task-end` emissions with a unified event type that agents actually filter for. Add harness TUI log branch for `task-transition`.

## Locked Decisions (human decided)

- **Q1 — Cleanup**: Remove dead `task-start`/`task-end` branches from harness.py `_log_event()` dispatch. Clean up dead code.
- **Q2 — Force flag**: No force flag in payload. YAGNI — add later if needed.
- **Q3 — Call chain**: cycle_post.py already calls tracker.py transition(). One event per transition, no double emission.

## Dev Discretion (dev agent can choose)

- Payload structure for `task-transition` event (which fields, naming)
- Whether to refactor the inline try/except emission into a helper function
- How to handle the `task-start`/`task-end` retirement (remove vs comment)

## Side Effect Mitigations (required)

- event_bus import failure must remain silent (existing try/except guard)
- Harness not running must remain silent (event_bus.emit returns silently)
- Illegal/blocked transitions must NOT emit events (guards fire sys.exit before emission block)
- One event per transition — no double emission

## Upgrade Path (required)

- N/A — purely additive. Old agents without event reading continue working. New agents start seeing status transitions in recent_events.

## Out of Scope

- Mechanical reactions triggered by task-transition events (Phase B follow-up)
- New event types beyond task-transition (#5613)
- Agent template changes for interpreting task-transition events
