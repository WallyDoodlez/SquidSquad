# Working State

- **Task**: #5622 Phase 4 agent comm bus
- **Status**: planning
- **Phase**: discussing FEAT-PM-5622

## Completed Steps
- Phase 1 Research complete
- Architecture confirmed: single bus, log model not queue
- Cursor + lag visibility design locked
- Phase 2 scope updated with task-start/task-end events

## Remaining Steps
- Resolve open Q: relevance rule location
- Phase 2 approval gate
- Phase 3 test plan

## Key Decisions
- Single shared bus, log model (events stay on consume)
- Each consumer tracks own cursor
- Cursor reported via X-Consumer-Cursor header on emission
- Health bar 'Bus Lag' column + event log fan-out markers
- 11 event types in Phase 2 (added task-start, task-end)

## Quiet cycle counter: 0
