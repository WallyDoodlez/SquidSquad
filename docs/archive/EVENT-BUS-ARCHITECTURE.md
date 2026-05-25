# Event Bus Architecture

_PRD — System design document for the SquidSquad event bus._

## Overview

The event bus is a lightweight, fire-and-forget observability layer that enables agents to react to coordination signals without polling GitHub Issues. It is **purely additive** — agents function identically when the harness is unreachable. All emission calls are non-blocking (500ms timeout) with silent failure.

## System Diagram

```mermaid
graph TB
    subgraph emitters["Event Emitters (Mechanical Scripts)"]
        CP["cycle_pre.py<br/>cycle-start"]
        CPO["cycle_post.py<br/>cycle-end"]
        GO["git_ops.py<br/>git-pull, git-push, git-commit<br/>pr-create, branch-checkout"]
        HA["harness.py<br/>pr-merged, compose-completed"]
        TR["tracker.py<br/>status-transition, tracker-comment"]
    end

    subgraph harness["Harness (harness.py)"]
        API["FastAPI REST API<br/>Port 7373"]
        ES["EventStream<br/>In-memory deque<br/>maxlen=1000"]
        AS["AgentState<br/>cycle, phase, health"]
        LOG["Console Log<br/>_log_event()"]
    end

    subgraph consumers["Event Consumers (Next Agent Cycle)"]
        EBR["event_bus_reader.py<br/>GET /events?since=cursor"]
        FILTER["_filter_events_for_role()<br/>Role-based type filter"]
        MECH["_run_mechanical_reactions()<br/>Deterministic pre-processing"]
        CIJ["cycle-input.json<br/>recent_events + mechanical_reactions"]
        AGENT["Agent Creative Phase<br/>Reads JSON, decides action"]
        CURSOR["_advance_event_cursor()<br/>working-state.md"]
    end

    CP -->|POST /events| API
    CPO -->|POST /events| API
    GO -->|POST /events| API
    HA -->|POST /events| API
    TR -->|POST /events| API

    API --> ES
    API --> AS
    API --> LOG

    ES -->|GET /events| EBR
    EBR --> FILTER
    FILTER --> MECH
    MECH --> CIJ
    CIJ --> AGENT
    AGENT --> CURSOR
```

## Event Lifecycle

```mermaid
sequenceDiagram
    participant Script as Mechanical Script
    participant EB as event_bus.py
    participant H as Harness API
    participant ES as EventStream
    participant Agent as Next Agent Cycle

    Script->>EB: emit(type, role, payload)
    EB->>EB: Discover port (.harness-port)
    EB->>H: POST /events
    H->>ES: append(event)
    H->>H: _update_agent_from_event()
    H->>H: _log_event() to console

    Note over Agent: Next cycle starts
    Agent->>H: GET /events?since=cursor
    H->>ES: get_since(cursor_id)
    H-->>Agent: {events: [...]}
    Agent->>Agent: _filter_events_for_role()
    Agent->>Agent: _run_mechanical_reactions()
    Agent->>Agent: Write cycle-input.json
    Agent->>Agent: Creative phase reads events
    Agent->>Agent: _advance_event_cursor()
```

## Event Type Catalogue

### Infrastructure Events (emitted by scripts)

| Event Type | Emitter | Payload | When |
|------------|---------|---------|------|
| `cycle-start` | cycle_pre.py | `{}` | Beginning of agent cycle |
| `cycle-end` | cycle_post.py | `{cycle_type, summary}` | End of agent cycle |
| `git-pull` | git_ops.py | `{result}` | After git pull |
| `git-push` | git_ops.py | `{branch}` | After git push |
| `git-commit` | git_ops.py | `{message, branch, files_changed, commit_type}` | After commit |
| `pr-create` | git_ops.py | `{pr_number, title, branch}` | After PR created |
| `pr-merged` | harness.py | `{pr_number, branch, issue_number, files_changed, success, error}` | After PR merged by harness |
| `compose-completed` | harness.py | `{roles_affected, trigger}` | After harness recomposes agent templates post-merge |
| `branch-checkout` | git_ops.py | `{branch, task_number}` | After branch switch |
| `status-transition` | tracker.py | `{issue_number, from, to}` | After status change |
| `tracker-comment` | tracker.py | `{issue_number, commenter_role, comment_preview, mentioned_roles}` | After comment posted |

### Planned Events (not yet emitted)

| Event Type | Planned Emitter | Purpose |
|------------|----------------|---------|
| `phase-change` | harness.py | Agent phase change signal |
| `agent-health` | harness.py | Agent health observation |
| `verification-failed` | QA creative phase | QA rejection signal |
| `verification-passed` | QA/PM creative phase | QA approval signal |

## EventStream Architecture

```mermaid
graph LR
    subgraph memory["In-Memory Storage"]
        D["collections.deque<br/>maxlen=1000<br/>Thread-safe (Lock)"]
    end

    subgraph api["REST API"]
        POST["POST /events<br/>Append + stamp received_at"]
        GET["GET /events<br/>?since=cursor_id<br/>?role=filter<br/>?event_type=filter<br/>?limit=100"]
    end

    subgraph id["Event ID"]
        HASH["sha256(timestamp + role<br/>+ event_type + payload + nonce)[:16]<br/>Content-hash + per-emit nonce, 16-char hex (64-bit, #9415)"]
    end

    POST --> D
    D --> GET
    HASH -.-> POST
```

**Properties:**
- **Bounded**: oldest events evicted at 1000 capacity
- **No persistence**: harness restart clears all events
- **Thread-safe**: Lock on every read/write
- **Port discovery**: `.squidsquad/.harness-port` file, walked up 5 parent dirs for clone isolation

## Role-Based Filtering

Each role only sees events relevant to its responsibilities:

```mermaid
graph TD
    ALL["All Events in EventStream"]

    ALL --> PM["PM sees:<br/>pr-merged, compose-completed<br/>verification-failed, verification-passed<br/>cycle-start, cycle-end<br/>status-transition, agent-health"]
    ALL --> QA["QA sees:<br/>pr-merged, compose-completed<br/>status-transition, cycle-end<br/>verification-failed"]
    ALL --> SKILL["Skill sees:<br/>pr-merged, compose-completed<br/>verification-failed, status-transition"]
    ALL --> DM["DM sees:<br/>status-transition, pr-merged<br/>verification-passed, compose-completed"]

    style PM fill:#4a9eff
    style QA fill:#ff9f43
    style SKILL fill:#54a0ff
    style DM fill:#5f27cd
```

Filtering is **client-side** in `cycle_pre.py` via `_ROLE_EVENT_TYPES` dict. Roles not in the dict receive all events (no filtering).

## Mechanical Reactions

Pre-processed deterministic responses to specific events:

```mermaid
flowchart TD
    E["recent_events"] --> SF{"Self-event?<br/>event.role == my_role"}
    SF -->|Yes| SKIP["Skip (cascade protection)"]
    SF -->|No| TYPE{"Event type?"}

    TYPE -->|pr-merged + PM| R1["Reaction: pr-merge-detected<br/>PM checks issue status"]
    TYPE -->|verification-failed + dev| R2["Reaction: rework-needed<br/>Dev prioritizes fix"]
    TYPE -->|other| PASS["No reaction<br/>Pass to creative phase"]

    R1 --> CIJ["cycle-input.json<br/>mechanical_reactions: [...]"]
    R2 --> CIJ
    PASS --> CIJ
```

## Cursor Model and Delivery Guarantees

```mermaid
sequenceDiagram
    participant WS as working-state.md
    participant CP as cycle_pre.py
    participant Agent as Creative Phase
    participant CPO as cycle_post.py

    WS->>CP: Read Last Processed Event ID
    CP->>CP: Query events since cursor
    CP->>CP: Filter + react
    CP->>Agent: cycle-input.json (events)

    alt Agent completes successfully
        Agent->>CPO: cycle-output.json
        CPO->>WS: Write new cursor ID
        Note over WS: Cursor advances
    else Agent crashes mid-cycle
        Note over WS: Cursor stays<br/>Same events re-delivered
    end
```

**Delivery semantics**: At-least-once. Cursor only advances after successful cycle completion. Crashed agents re-process the same events on restart.

## Cascade Protection

Two safeguards prevent infinite event loops:

1. **Self-event filter**: `if event.get("role") == role: continue` in `_run_mechanical_reactions()`. An agent's own emissions never trigger its own mechanical reactions.

2. **Cursor deduplication**: Events before the cursor are never re-read. A mechanical reaction that triggers a tracker transition (which emits a new `status-transition` event) will only be seen by *other* agents on their next cycle, not by the emitting agent.

## Port Discovery (Clone Isolation)

```mermaid
flowchart TD
    START["Agent needs harness port"] --> CHECK1[".squidsquad/.harness-port<br/>in repo root?"]
    CHECK1 -->|Found| USE["Use port from file"]
    CHECK1 -->|Not found| WALK["Walk up parent dirs<br/>(max 5 levels)"]
    WALK -->|Found| USE
    WALK -->|Not found| NOOP["Return None<br/>Silent no-op"]

    HARNESS["Harness startup"] --> WRITE["Write port to primary repo"]
    HARNESS --> DIST["Distribute to all<br/>agent clone dirs"]
```

## Design Properties

| Property | Implementation |
|----------|---------------|
| **Non-blocking** | 500ms timeout on all HTTP calls, exceptions silently swallowed |
| **Observational** | Events are advisory signals, not commands. Creative phase decides action |
| **No persistence** | In-memory deque. Harness restart clears history |
| **Self-isolation** | Agents only react to other agents' events |
| **At-least-once** | Cursor advances only after successful cycle |
| **Role authority** | Event bus has no knowledge of permissions — tracker.py enforces |
| **Graceful degradation** | Harness unreachable = empty events = zero behavior change |
