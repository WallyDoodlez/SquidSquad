# Working State

- **Task**: #5622
- **Status**: in-progress
- **Started**: 2026-05-05 23:02
- **Last Processed Event ID**: none

## Completed Steps
- Extended GET /events in harness.py with since, role, event_type query params + received_at stamp
- Created event_bus_reader.py — cursor-based event consumption module (stdlib urllib, 500ms timeout)
- Extended cycle_pre.py — injects recent_events into cycle-input.json from event bus reader
- Extended _read_working_state() to parse Last Processed Event ID field
- Added per-role event relevance filtering (_ROLE_EVENT_TYPES config in cycle_pre.py)
- Written 15 tests for event_bus_reader.py (port discovery, query, get_since)
- Written 3 tests for cycle_pre cursor parsing (value, none, missing)
- Added event_bus_reader.py to installer-files.txt
- All tests passing (84/84 cycle_pre + event_bus_reader)

## Remaining Steps
- Add mechanical reactions to cycle_pre.py (pr-merge → auto-transition, verification-failed → rework context)
- Update sub-skill docs (cycle-runner.md with recent_events field, working-state.md with cursor field)
- Final full test run and PR creation

## Key Decisions
- event_bus_reader.py uses same port discovery pattern as event_bus.py
- Harness stamps received_at (time.time()) at POST time before appending to stream
- GET /events over-fetches (limit*3) before filtering
- get_since returns oldest available if cursor ID evicted from deque
- Per-role filtering: PM sees most event types, skill/dm see fewer
