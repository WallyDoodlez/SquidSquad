# Event Bus — How Agents Coordinate in Real-Time

SquidSquad agents normally coordinate through git — each agent pulls, works, pushes, and the next agent picks up changes on its next cycle. This works reliably but means agents wait up to 30 minutes to notice each other's work.

The **event bus** eliminates that delay. When QA verifies a fix, the dev agent knows within seconds. When a PR is merged, PM reacts immediately. Agents still use git as the durable record — the event bus is a fast, ephemeral notification layer on top.

---

## The Big Picture

```mermaid
graph LR
    subgraph Agents
        SKILL[Skill Agent]
        PM[PM Agent]
        QA[QA Agent]
        DM[DM Agent]
    end

    subgraph Harness
        API["FastAPI Server<br/>(port 7373)"]
        STREAM["Event Stream<br/>(in-memory, last 1000)"]
    end

    SKILL -->|"POST /events"| API
    PM -->|"POST /events"| API
    QA -->|"POST /events"| API
    DM -->|"POST /events"| API

    API --> STREAM

    STREAM -->|"GET /events?since=X"| SKILL
    STREAM -->|"GET /events?since=X"| PM
    STREAM -->|"GET /events?since=X"| QA
    STREAM -->|"GET /events?since=X"| DM
```

Every agent emits events during its work (status changes, PR merges, commits). The harness collects them in memory. At the start of each cycle, every agent reads new events and decides how to react.

---

## How an Event Flows

```mermaid
sequenceDiagram
    participant QA as QA Agent
    participant T as tracker.py
    participant H as Harness
    participant C as cycle_pre.py
    participant SK as Skill Agent

    Note over QA: QA verifies a fix
    QA->>T: transition #42 pending-test → pending-ship
    T->>H: POST /events<br/>{"type": "status-transition",<br/>"from": "pending-test",<br/>"to": "pending-ship"}
    H->>H: Store in memory<br/>Stamp received_at

    Note over SK: Next cycle starts
    C->>H: GET /events?since=last_id
    H-->>C: [status-transition for #42]
    C->>C: Filter for skill's event types
    C->>C: Write to cycle-input.json
    SK->>SK: Reads cycle-input.json<br/>Sees #42 is verified
```

The key design: **emitting never blocks** (500ms timeout, silent on failure) and **reading never breaks** (returns empty list on failure). If the harness is down, agents fall back to their normal 30-minute git polling — zero behavior change.

---

## Event Types

Agents emit these events during normal operations:

### Work Coordination

| Event | Emitted By | When | What It Tells Other Agents |
|-------|-----------|------|---------------------------|
| `status-transition` | tracker.py | Any status label change | "Issue #42 moved from pending-test to pending-ship" |
| `pr-merge` | git_ops.py | A PR is merged | "PR #99 was merged — related issue can ship" |
| `pr-create` | git_ops.py | A PR is opened | "New PR #99 for review" |
| `verification-failed` | QA scripts | QA rejects work | "Issue #42 failed verification — dev needs to rework" |

### Lifecycle

| Event | Emitted By | When | What It Tells Other Agents |
|-------|-----------|------|---------------------------|
| `cycle-start` | cycle_pre.py | Agent begins a cycle | "Skill agent started cycle 862" |
| `cycle-end` | cycle_post.py | Agent finishes a cycle | "Skill agent finished — quiet cycle" |
| `git-pull` | git_ops.py | Agent pulls latest | "Skill agent synced with remote" |
| `git-push` | git_ops.py | Agent pushes changes | "New commits on main from skill" |
| `git-commit` | git_ops.py | Agent creates a commit | "Skill committed code changes" |
| `branch-checkout` | git_ops.py | Agent switches branches | "Skill checked out task/5868" |

### Event Format

Every event is a JSON object:

```json
{
  "id": "a1b2c3d4",
  "event_type": "status-transition",
  "role": "qa",
  "timestamp": "2026-05-07T14:30:00",
  "payload": {
    "issue_number": "42",
    "from": "pending-test",
    "to": "pending-ship"
  },
  "received_at": 1746538200.123
}
```

The `id` is a content hash — the same event at the same time always produces the same ID, which prevents duplicate processing.

---

## What Each Agent Sees

Not every agent needs every event. Each role has a filter that surfaces only relevant signals:

```mermaid
graph TD
    EVENTS["All Events<br/>(harness stream)"]

    EVENTS --> PM_FILTER["PM Filter"]
    EVENTS --> QA_FILTER["QA Filter"]
    EVENTS --> SKILL_FILTER["Skill Filter"]
    EVENTS --> DM_FILTER["DM Filter"]

    PM_FILTER --> PM_EVENTS["pr-merge<br/>status-transition<br/>cycle-start/end<br/>verification-failed/passed<br/>agent-health"]

    QA_FILTER --> QA_EVENTS["pr-merge<br/>status-transition<br/>cycle-end<br/>verification-failed"]

    SKILL_FILTER --> SKILL_EVENTS["pr-merge<br/>status-transition<br/>verification-failed"]

    DM_FILTER --> DM_EVENTS["status-transition<br/>verification-passed<br/>pr-merge"]
```

For example, DM only cares about status transitions (to catch pending-ship items) and PR merges. It doesn't need to see every git pull or cycle start.

---

## Mechanical Reactions vs. Creative Decisions

When an agent reads events, some patterns are so predictable that the system handles them automatically. Others require the agent's judgment.

```mermaid
flowchart TD
    EVENTS["New events from harness"]

    EVENTS --> CHECK{"High-confidence<br/>pattern?"}

    CHECK -->|Yes| MECHANICAL["Mechanical Reaction<br/>(automatic, deterministic)"]
    CHECK -->|No| CREATIVE["Creative Phase<br/>(agent decides what to do)"]

    MECHANICAL --> M1["PR merged → PM notified<br/>(pr-merge-detected)"]
    MECHANICAL --> M2["QA rejected → Dev notified<br/>(rework-needed)"]

    CREATIVE --> C1["Agent reads events<br/>in cycle-input.json"]
    CREATIVE --> C2["Applies judgment:<br/>prioritize, investigate,<br/>or ignore"]
```

**Mechanical reactions** are conservative — only two patterns currently qualify:
1. **PR merge detected** (PM): "PR #99 was merged for issue #42" — surfaces merge context
2. **Rework needed** (dev): "QA rejected issue #42" — surfaces the failure reason

Everything else lands in `recent_events` in the agent's `cycle-input.json` for the creative phase to interpret.

---

## The Cursor — Tracking What's Been Read

Each agent tracks a **cursor** — the ID of the last event it processed. This prevents re-reading the same events every cycle.

```mermaid
sequenceDiagram
    participant WS as working-state.md
    participant CP as cycle_pre.py
    participant H as Harness
    participant CPO as cycle_post.py

    Note over WS: Last Processed Event ID: a1b2c3d4

    CP->>WS: Read cursor
    CP->>H: GET /events?since=a1b2c3d4
    H-->>CP: Events e5, f6, g7
    CP->>CP: Write events to cycle-input.json

    Note over CP: Agent does creative work...

    CPO->>WS: Update cursor to g7

    Note over WS: Last Processed Event ID: g7g7g7g7
```

If the agent crashes mid-cycle, the cursor hasn't advanced yet — events are safely re-delivered next cycle. This is crash-safe by design.

---

## What Happens When the Bus Is Down

The event bus is **strictly optional**. Every interaction is wrapped in error handling that silently falls back:

| Scenario | What Happens | Agent Impact |
|----------|-------------|-------------|
| Harness not running | Port file missing, no network calls made | Zero — agents cycle normally via git |
| Harness crashes mid-cycle | Emit timeout (500ms), returns silently | Event not recorded, no other effect |
| Network blip on read | `query()` returns `[]` | Agent sees no events, works from git state |
| Cursor points to evicted event | Harness returns oldest available events | Possible replay, but reactions are idempotent |
| Harness restarts | In-memory events lost, stream starts fresh | Agents resume from cursor, no gap errors |

The contract: **agents behave identically with or without the event bus.** The bus makes them faster, not different.

---

## Architecture in Context

The event bus sits at **L1 (Transport)** in SquidSquad's [six-layer architecture](ARCHITECTURE.md). It's mechanical plumbing — deterministic scripts emit and read events. The agent's creative phase (L3 Behavior) decides what the events mean.

```
L6  Memory        ← what the squad knows
L5  Soul          ← how the agent thinks
L4  Sub-skills    ← reusable capabilities
L3  Behavior ★    ← decides what events MEAN
L2  Orchestration ← timing & lifecycle
L1  Transport     ← event bus lives here (emit/read)
```

---

## Quick Reference

**Emit an event** (from any script):
```python
from event_bus import emit
emit("status-transition", "qa", {"issue_number": "42", "from": "pending-test", "to": "pending-ship"})
```

**Read events** (handled automatically by `cycle_pre.py`):
```python
from event_bus_reader import query
events = query(since="a1b2c3d4", limit=100)
```

**Check harness status**:
```bash
python references/scripts/squidsquad_cli.py status
```

**View the event stream** (direct API):
```bash
curl http://127.0.0.1:7373/events?limit=10
```
