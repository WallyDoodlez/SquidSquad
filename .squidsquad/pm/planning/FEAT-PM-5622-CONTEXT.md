# FEAT-PM-5622 Context — Phase 4: Agent Communication Bus (Read Side)

## Scope

Agents READ from the harness event bus for real-time coordination. Adds:
- `GET /events` endpoint on harness with query param filtering
- `event_bus_reader.py` — new module for cursor-based event consumption
- `cycle_pre.py` integration — inject `recent_events` into `cycle-input.json`
- Mechanical reactions for high-confidence patterns (in `cycle_pre.py`)
- Per-role relevance filtering in `cycle_pre.py`
- Harness-stamped `received_at` epoch on every event

Does NOT include: frontend UI (Phase 5), WebSocket/SSE push (Phase 3 addition), external chat adapters (#3415), event persistence to disk.

## Locked Decisions (human decided)

- **Q1 — Mechanical reaction location**: High-confidence idempotent patterns (pr-merge → auto-transition, verification-failed → rework context) execute in `cycle_pre.py` before agent creative phase. Lower-confidence patterns surface to agent via `recent_events` for creative-phase judgment.
- **Q2 — Cursor authority (revised after DeepSeek review)**: Agent-side cursor in `working-state.md` (`Last Processed Event ID` field). Agent passes cursor as `?since=<id>` query param on `GET /events`. Harness is stateless for cursors — does not track or persist them. `X-Consumer-Cursor` header on emissions becomes read-only TUI telemetry (harness displays consumption lag but doesn't use it for state).
- **Q3 — File separation**: `event_bus.py` (emit, Phase 2) and `event_bus_reader.py` (consume, Phase 4) stay separate. Different concerns, different error handling, different import sites.
- **Q4 — Shared endpoint**: Same `GET /events` endpoint serves both agent consumption and future browser UI (Phase 3). Differentiated by query params. Agent: `?since=<id>&role=pm&limit=50`. Browser: `?roles=pm,skill&event_types=pr-merge&since=<ts>&limit=200`.
- **Q5 — Full payload**: `recent_events` in `cycle-input.json` includes complete event objects. 10-30 events × ~200 bytes = 2-6KB — negligible for context.
- **Q6 — Agent-side relevance filtering**: Each agent's `cycle_pre.py` has a per-role config block (e.g., `PM_EVENT_TYPES = ["pr-merge", "verification-failed"]`) that filters events locally. Harness returns all events for the role; agent keeps what it cares about.
- **Event ordering**: Harness stamps `received_at` epoch timestamp on every event at append time. Ordering is by arrival time, not causal. Documented as a known limitation — consumers must not assume causal ordering.
- **TUI consumption visibility** (from prior session): Bus lag column in health bar + fan-out markers (`[P✓ Q✓ S✓ D-]`) showing which consumers have read each event. Cursor reporting via `X-Consumer-Cursor` header — harness uses for display only, not state.
- **--suppress-event flag**: Deferred (YAGNI). Tracker state machine prevents cascade loops — transitions are one-way, terminal states can't cycle. Add the flag later if riskier reactions are defined.

## Dev Discretion (dev agent can choose)

- Internal structure of `event_bus_reader.py` — class vs functions, error handling strategy
- How `cycle_pre.py` organizes the per-role event type config (dict, constant, etc.)
- Whether to extract shared port discovery into a utility or duplicate the 15 lines
- Mechanical reaction handler architecture (registry pattern, if/else, etc.)
- Default `limit` value for `GET /events` query param
- How `_read_working_state()` parser is extended for `Last Processed Event ID`

## Side Effect Mitigations (required)

- `GET /events` must timeout at 500ms (same pattern as Phase 2 emit). Timeout → return `[]`, agent continues normally.
- `event_bus_reader.py` import wrapped in `try/except ImportError` — missing module returns `[]`, not crash.
- Mechanical reactions MUST be idempotent — calling the same reaction twice produces the same result. `tracker.py transition` already rejects invalid transitions.
- Mechanical reactions MUST verify local state before acting — e.g., check issue is actually at expected status before transitioning.
- `recent_events` defaults to `[]` if harness unreachable, reader missing, or no new events.
- First cycle after upgrade (no cursor): reader returns most recent N events (default limit). Agent catches up once.

## Upgrade Path (required)

- Same 5-step deployment as Phase 2: deploy reader → deploy updated cycle_pre → wait one cycle → deploy harness GET endpoint → agents read events next cycle.
- `event_bus_reader.py` deploys BEFORE harness update (import wrapped in try/except).
- `working-state.md` template gains `Last Processed Event ID` field — existing agents without it default to "none" (no cursor → get recent N events).
- Rollback: revert import lines + restart old harness → agents fall back to empty `recent_events`.
- Mixed-version squad: Phase 4 agents read bus eagerly, Phase 2 agents don't read at all. No breakage.

## Out of Scope

- Frontend/browser UI for events (Phase 5)
- WebSocket/SSE push (Phase 3 addition)
- External chat adapters (Telegram, Discord, Slack — #3415)
- Event persistence to disk
- `--suppress-event` flag on tracker.py (deferred — YAGNI)
- `event_bus.py` port discovery cleanup (separate bug)
- Causal ordering / Lamport clocks (future phase if needed)
