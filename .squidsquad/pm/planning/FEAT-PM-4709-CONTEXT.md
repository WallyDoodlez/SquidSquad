# FEAT-PM-4709 Context — Harness Phase 2: Event Bus

## Scope

Add event bus to the harness. Mechanical scripts (cycle_pre/cycle_post) emit events via HTTP POST. Harness maintains live state model and displays events in console.

## Locked Decisions (human decided)

- **Event emission via HTTP POST**: Agents emit to `localhost:<port>/events`. Same FastAPI server from Phase 1.
- **Mechanical scripts emit**: cycle_pre.py and cycle_post.py emit events. Agents don't know about events — zero template changes. Silent fire-and-forget.
- **Port discovery via parent-dir walking**: `event_bus.py` reads `.harness-port` from its own clone's `.squidsquad/` with parent-directory fallback walking (matches existing pattern in `cycle_post.py:_discover_harness_port()`). Harness only writes `.harness-port` to the main repo's `.squidsquad/` directory; agent clones discover via parent-dir walk. Default fallback to port 7373 if not found. Simpler and already battle-tested.
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

### Events (11 total — 4 categories):

**Cycle events** (emitted by cycle_pre/cycle_post):
- **cycle-start**: after writing cycle-input.json
- **cycle-end**: after commit/push (includes cycle_type + summary)
- **phase-change**: when status bar updates

**Git events** (emitted by git_ops.py — single funnel per operation):
- **git-pull**: after pull (includes result: ok/conflict/stash)
- **git-commit**: after commit (includes message, branch, files changed count, **commit_type: "code"|"state"** — distinguishes feature-branch code commits from main-branch state commits)
- **git-push**: after push (includes branch). **Emitted from `git_ops.push()` only** — single funnel, never from cycle_post.py callers, prevents duplicate events from multi-path push logic (#5444 fallback).
- **pr-create**: after PR creation (includes PR number, title, branch)
- **pr-merge**: after PR merge (includes PR number)
- **branch-checkout**: on task-begin/task-end (includes branch name, task number)

**Task events** (emitted by tracker.py — single funnel at status transition):
- **task-start**: after agent transitions task to `in-progress` (from `approved` for tasks, from `open` for issues). Payload: `task_number`, `from_status`, `assigned_role`, `task_title` (truncated to 80 chars).
- **task-end**: after agent transitions task to `pending-test` (from `in-progress`). Payload: `task_number`, `assigned_role`, `cycles_to_complete` (computed by counting cycle boundaries between task-start and task-end events for the same task_number, or null if task-start not in current bus history).

Emitted from inside `tracker.py transition` after the GitHub API call succeeds — single funnel guarantees consistency.

**Harness-internal events** (emitted by harness, NOT agents — added per impact review):
- The harness MAY inject its own events into the stream when internal state changes (intent transitions, health-check results). These bypass the agent emission contract. Specific event types deferred to Phase 3+ (see #5613); Phase 2 just establishes the precedent that harness-internal events are valid stream entries.

## Implementation

- **event_bus.py** (~50 lines): stdlib urllib, `emit(event_type, role, payload)`. Reads `.harness-port` via parent-dir walking (fallback 7373), POST with 500ms timeout, catches all exceptions silently.
- **cycle_pre.py**: emit `cycle-start` after writing cycle-input.json
- **cycle_post.py**: emit `cycle-end` after commit/push (does NOT emit `git-push` — that comes from git_ops.push only)
- **git_ops.py**: emit `git-pull` (in `pull()`), `git-commit` (in `commit_code()` with `commit_type:"code"`, in `commit_state()` with `commit_type:"state"`), `git-push` (in `push()` — single funnel), `pr-create` (in `pr_create()`), `pr-merge` (in `pr_merge()`), `branch-checkout` (in `task_begin()`/`task_end()`)
- **tracker.py**: emit `task-start` after successful transition to `in-progress`, emit `task-end` after successful transition to `pending-test`. Single funnel inside the `transition()` function — emit only on successful GitHub API response.
- **Harness /events endpoint**: receives events from agents, appends to bounded stream (1000 max), updates AgentState. Harness can also inject internal events directly into the stream without HTTP roundtrip.

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

Per locked decision above — using parent-dir walking, not per-clone writes:

1. Harness writes `.harness-port` to main repo's `.squidsquad/.harness-port` only (existing behavior)
2. `event_bus.py` reads `.harness-port` starting from its own clone's `.squidsquad/`, walking up parent directories until found
3. Falls back to port 7373 if not found at any level
4. Reuses the pattern already in `cycle_post.py:_discover_harness_port()` (lines 453-482) — extract to shared utility OR replicate the same logic in `event_bus.py`

This works because agent clones are siblings of the main repo (per clone-isolation architecture). Parent-dir walking finds the main `.squidsquad/.harness-port` automatically.

## Dev Discretion

- Thread safety implementation (single lock vs asyncio queue)
- Whether to add a GET /events endpoint for polling (in addition to console display)
- Exact console format and colors
- Whether cycle_post also emits status_transitions from cycle-output.json

## Locked Decisions — Transition Refinements (from agent-transition review)

- **Console mode flag**: harness supports `--console simple|rich` (default `rich`). `simple` preserves current `print()`-based output as fallback. All `_log()` calls route through a `ConsoleWriter` abstraction. This provides a rollback path if rich rendering has terminal issues.
- **Event bus import warning**: `event_bus.py` import wrapped in `try/except ImportError` with a single-shot stderr warning (`"WARNING: event_bus.py import failed, events disabled"`). Silent runtime exceptions (HTTPError, ConnectionRefused) remain silent — only the import failure logs once. Aids debugging without breaking fire-and-forget contract.
- **AgentState backfill on harness startup**: when harness boots and discovers running agents via PID checks, it reads existing files to populate health table immediately:
  - `.squidsquad/<role>/current-state` → `current_phase`
  - `.squidsquad/<role>/context-pressure` → context %
  - latest `.squidsquad/<role>/iterations/iter-N.md` → `current_cycle` (parse N from filename)
  - `last_cycle_start`, `last_cycle_end`, `last_cycle_type` remain "—" until first event (one cycle max)

  Health table shows meaningful data within ~5 seconds of harness restart, not 30 minutes. Phase 1 already reads `current-state` and `context-pressure` for `/agents/{role}/health` (harness.py:563-575) — extend to populate AgentState.

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
- Specific harness-internal event types — `health-check-result`, `intent-transition`, `vault-read`, `merge-resolved` deferred to Phase 3+ per #5613. Phase 2 only establishes the precedent that harness can inject events.

## Impact Review Note

A re-research review (PHASE2-IMPACT-REVIEW-RESEARCH.md) was conducted after 16 ships landed since original planning. Verdict: proceed with the 5 minor adjustments now incorporated above. The shipped changes (push verification #5444, .gitattributes #5469, rebase→merge #5445, PID-first health #5429, etc.) strengthen rather than undermine Phase 2 design.

## Agent Transition Plan (from PHASE2-AGENT-TRANSITION-RESEARCH.md)

5-step deployment runbook. NO agent restarts required. Total harness downtime ~5s.

1. Deploy `event_bus.py` to main repo (silent — not yet imported)
2. Deploy updated `cycle_pre.py`, `cycle_post.py`, `git_ops.py` with imports + emit calls (try/except ImportError fallback ensures safety)
3. Wait one cycle (~30 min) — agents pull, manually verify no errors
4. Graceful stop harness (Ctrl+C), deploy new harness, restart
5. Next cycle → events flow

**Rollback**: Push revert commit removing import lines + restart old harness. Agents pick up on next cycle. No work lost.

See `.squidsquad/pm/planning/PHASE2-AGENT-TRANSITION-RESEARCH.md` for the full runbook including pre-deployment checklist, per-step verification commands, and 4 rollback scenarios.
