# Working State

- **Task**: #5622
- **Status**: in-progress
- **Started**: 2026-05-05 23:02

## Completed Steps
- Extended GET /events in harness.py with since, role, event_type query params + received_at stamp
- Created event_bus_reader.py — cursor-based event consumption module (stdlib urllib, 500ms timeout)
- Extended cycle_pre.py — injects recent_events into cycle-input.json from event bus reader
- Extended _read_working_state() to parse Last Processed Event ID field
- All existing tests pass (66/66 cycle_pre, full suite green)

## Remaining Steps
- Add mechanical reactions to cycle_pre.py (conservative, idempotent)
- Add per-role relevance filtering config to cycle_pre.py
- Write unit tests for event_bus_reader.py
- Write unit tests for harness GET /events endpoint changes
- Write unit tests for cycle_pre event integration
- Update sub-skill docs (cycle-runner.md, working-state.md template)
- Add event_bus_reader.py to installer-files.txt

## Key Decisions
- event_bus_reader.py uses same port discovery pattern as event_bus.py
- Harness stamps received_at (time.time()) at POST time before appending to stream
- GET /events over-fetches (limit*3) before filtering to ensure enough results after role/type filter
- get_since returns all events from oldest if cursor ID not found (evicted from deque)
- Per-role filtering will be constants in cycle_pre.py (dev discretion from CONTEXT.md)
