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
  "id": "a3f7b2c1",
  "event_type": "cycle-start|cycle-end|phase-change|git-*",
  "role": "pm|skill|qa|dm",
  "timestamp": "2026-05-01T18:00:00",
  "cycle_number": 862,
  "payload": {}
}
```

- `id`: short SHA (8 chars, generated from hash of timestamp+role+event_type+payload). Unique per event. Useful for referencing specific events in logs, debugging, and future API queries.

### Events:

**Cycle events** (emitted by cycle_pre/cycle_post):
- **cycle-start**: after writing cycle-input.json
- **cycle-end**: after commit/push (includes cycle_type + summary)
- **phase-change**: when status bar updates

**Git events** (emitted by git_ops.py):
- **git-pull**: after pull (includes result: ok/conflict/stash)
- **git-commit**: after commit (includes message, branch, files changed count)
- **git-push**: after push (includes branch)
- **pr-create**: after PR creation (includes PR number, title, branch)
- **pr-merge**: after PR merge (includes PR number)
- **branch-checkout**: on task-begin/task-end (includes branch name, task number)

## Implementation

- **event_bus.py** (~50 lines): stdlib urllib, `emit(event_type, role, payload)`. Reads `.harness-port`, POST with 500ms timeout, catches all exceptions silently.
- **cycle_pre.py**: emit `cycle-start` after writing cycle-input.json
- **cycle_post.py**: emit `cycle-end` after commit/push
- **git_ops.py**: emit `git-pull`, `git-commit`, `git-push`, `pr-create`, `pr-merge`, `branch-checkout` at each respective operation
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

Split display:
- **Top: persistent health bar** — always visible, updates in-place. Shows each agent's status (alive/dead, current cycle, current phase). Redraws on each event.
- **Below: scrolling event log** — events stream below the health bar.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ pm:    🦑 #869 idle       ctx: 22%  │  Session: $5.67                      │
│ skill: 🦑 #868 implementing ctx: 45%  │  Week:    $81.60                     │
│ qa:    🦑 #166 verifying  ctx: 31%  │                                      │
│ dm:    🦑 #48  delivering ctx: 12%  │                                      │
└─────────────────────────────────────────────────────────────────────────────┘
[21:03:11] skill git-pull     ok
[21:03:12] skill cycle-start  #867
[21:03:30] skill git-commit   "fix: async shutdown" (2 files)
[21:03:33] skill cycle-end    #867 (active)
```

Health bar shows:
- **Per agent**: status icon + current cycle + phase + context pressure %
- **Bottom: two usage bars** (account-wide, Claude provides % only):

Layout: **health pinned top (aligned table), logs scroll below.**

```
┌─────────┬────┬───────┬──────────────┬──────┐
│ Agent   │    │ Cycle │ Phase        │ Ctx  │
├─────────┼────┼───────┼──────────────┼──────┤
│ pm      │ 🦑 │ #869  │ idle         │ 22%  │
│ skill   │ 🦑 │ #868  │ implementing │ 45%  │
│ qa      │ 🦑 │ #166  │ verifying    │ 31%  │
│ dm      │ 🦑 │ #48   │ delivering   │ 12%  │
├─────────┴────┴───────┴──────────────┴──────┤
│ Session: ████████░░░░░░░░░░░░ 42%          │
│ Weekly:  ██████████████░░░░░░ 68%          │
└────────────────────────────────────────────┘
[21:33:42] pm    cycle-start  #869
[21:34:15] skill git-pull     ok
[21:35:02] skill git-commit   "feat: event bus" (3 files)
[21:35:08] skill cycle-end    #868 (active)
[21:37:10] dm    pr-merge     PR #4715
[21:37:20] dm    cycle-end    #48 (active) — shipped #4439
```

- Health table pinned top, redraws in-place on each event
- Usage bars below health table, also pinned
- Event log scrolls freely below
- Table columns aligned: Agent | Status | Cycle | Phase | Context %

Use `rich` library (already installed). Specifically:
- `rich.table.Table` for the aligned agent health table
- `rich.progress.Progress` for the session/weekly usage bars
- `rich.live.Live` for the pinned top section (redraws in-place)
- `rich.console.Console` for the scrolling event log below

`rich` handles cross-platform terminal rendering (Windows + Mac + Linux).

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
