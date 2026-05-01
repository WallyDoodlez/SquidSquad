# FEAT-PM-4709 Context — Harness Phase 2: Event Bus

## Scope

Add event bus to the harness. Mechanical scripts (cycle_pre/cycle_post) emit events via HTTP POST. Harness maintains live state model and displays events in console.

## Locked Decisions (human decided)

- **Event emission via HTTP POST**: Agents emit to `localhost:<port>/events`. Same FastAPI server from Phase 1.
- **Mechanical scripts emit**: cycle_pre.py and cycle_post.py emit events. Agents don't know about events — zero template changes. Silent fire-and-forget.
- **Port discovery via file**: `.harness-port` written to each agent clone directory by harness at startup (reads .local-config for paths).
- **Backward compat**: If harness down or event_bus.py missing, silent no-op. Zero behavior change for agents.

## Event Schema (Phase 2 MVP)

```json
{
  "event_type": "cycle-start|cycle-end|phase-change",
  "role": "pm|skill|qa|dm",
  "timestamp": "2026-05-01T18:00:00",
  "cycle_number": 862,
  "payload": {}
}
```

### Events:
- **cycle-start**: emitted by cycle_pre.py after writing cycle-input.json
- **cycle-end**: emitted by cycle_post.py after commit/push
- **phase-change**: emitted when status bar updates (piggyback on existing write)

## Implementation

- **event_bus.py** (~50 lines): stdlib urllib, `emit(event_type, role, payload)`. Reads `.harness-port`, POST with 500ms timeout, catches all exceptions silently.
- **cycle_pre.py**: add `event_bus.emit("cycle-start", role, {"cycle_number": N})` after writing cycle-input.json
- **cycle_post.py**: add `event_bus.emit("cycle-end", role, {"cycle_number": N, "cycle_type": type, "summary": summary})` after commit/push
- **Harness /events endpoint**: receives events, appends to bounded stream (1000 max), updates AgentState

## Harness State Model (extended from Phase 1)

```python
AgentState:
  role: str
  pid: int
  alive: bool
  current_cycle: int
  current_phase: str
  last_cycle_start: datetime
  last_cycle_end: datetime
  last_cycle_type: str  # active/quiet/suppressed

EventStream:
  events: deque(maxlen=1000)  # bounded, ~200KB max
```

## Console Display

Harness console shows events as they arrive:
```
[18:32:55] skill cycle-start #862
[18:33:12] qa   phase-change verifying
[18:33:38] skill cycle-end   #862 (active) — #4439 fixing QA bugs
[18:34:01] dm   cycle-start #45
```

Simple scrolling log. No curses/rich. Upgradeable later.

## Port Distribution (clone isolation)

On harness startup:
1. Read `.squidsquad/.local-config` for all agent clone paths
2. Write `.squidsquad/.harness-port` to each clone's `.squidsquad/` directory
3. event_bus.py reads from its own clone's `.squidsquad/.harness-port`

## Dev Discretion

- Thread safety implementation (single lock vs asyncio queue)
- Whether to add a GET /events endpoint for polling (in addition to console display)
- Exact console format and colors
- Whether cycle_post also emits status_transitions from cycle-output.json

## Side Effect Mitigations (required)

- event_bus.py import wrapped in try/except everywhere — missing file = no-op
- .harness-port missing = no emit, no error
- HTTP timeout 500ms — never blocks agent cycle
- Bounded event stream — never grows unbounded

## Depends On

- #4439 Phase 1 (harness must be running and serving HTTP)

## Out of Scope (Phase 2)

- Frontend WebSocket streaming (Phase 3/4)
- Custom agent-initiated events from creative phase
- Telegram/Discord adapters (Phase 6)
- Event persistence to disk
