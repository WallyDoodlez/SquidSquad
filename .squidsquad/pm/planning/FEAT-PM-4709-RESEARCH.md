# FEAT-PM-4709 Research — Harness Phase 2: Event Bus + Agent Communication Sub-Skill

## Summary

Phase 2 adds an event bus layer on top of the Phase 1 FastAPI harness. Agents emit
lifecycle events (cycle-start, cycle-end, task transitions, errors) via HTTP POST to
`localhost:<port>/events`. The harness maintains an in-memory state model per agent and
exposes it on a streaming console and via `GET /state`.

**Recommendation**: Feasible. The emission points are well-defined (cycle_pre and
cycle_post are the natural bookends; mechanical scripts handle all I/O already). The main
design risk is backward compatibility — if the harness is not running, every `POST /events`
must silently no-op without crashing the agent. This is a one-line try/except in a helper
function, not a hard problem.

**Locked decision from brief**: Agents emit via HTTP POST to `localhost:<port>/events`.
No file-based mechanism.

---

## Vault Context

- **BRIEFING.md priorities**: v1.0.0 launch focus — harness is part of the public-facing
  control plane
- **Related decisions**: Phase 1 CONTEXT.md — harness is additive, existing scripts remain
  functional as fallback; port written to `.squidsquad/.harness-port`
- **Related patterns**: `pattern` — "HTTP wrapper over file-based control plane" (from Phase 1
  vault candidate)
- **Human preferences**: agents stay in visible terminals; harness is the operator's view;
  fire-and-forget emission (implied by Phase 2 brief)
- **Related learnings**: Phase 1 research — harness crash must not kill agents; port discovery
  via `.squidsquad/.harness-port`

---

## 1. Event Schema

### Proposed Event Types

| Event | When emitted | Key fields |
|-------|-------------|-----------|
| `cycle-start` | Start of `cycle_pre.py` | role, cycle_number, timestamp |
| `cycle-end` | End of `cycle_post.py` | role, cycle_number, cycle_type, duration_seconds |
| `task-pickup` | Agent transitions issue → in-progress | role, issue_number, title |
| `task-complete` | Agent transitions → pending-test or pending-ship | role, issue_number, title, to_status |
| `status-transition` | Any tracker status change | role, issue_number, from_status, to_status |
| `health-update` | Agent sends heartbeat (optional — .health file already does this) | role, health_status |
| `error` | Exception or unrecoverable failure in agent flow | role, error_type, message, cycle_number |
| `phase-change` | Agent writes a new phase to current-state | role, phase, description |

### Canonical Event Envelope

```json
{
  "event_type": "cycle-start",
  "role": "skill",
  "cycle_number": 42,
  "timestamp": "2026-04-28T14:30:00",
  "payload": {
    "pull_result": "ok",
    "context_pressure_pct": 23
  }
}
```

**Required fields on every event**: `event_type`, `role`, `timestamp`.
**Optional fields**: `cycle_number`, `payload` (event-specific data).

### Minimal viable set (Phase 2 scope)

Start with 3 events: `cycle-start`, `cycle-end`, `phase-change`. These give the harness
enough to show "who is alive and what cycle they're on" without requiring agents to
instrument every possible action. The full event set can grow in Phase 3+.

---

## 2. Emission Points

### Where events fit in the existing cycle flow

The cycle flow is:
```
wrapper → cycle_pre.py → [agent creative work] → cycle_post.py → wrapper
```

Natural emission points:

| Emission point | Event | Mechanism |
|---------------|-------|-----------|
| Top of `cycle_pre.py` (before git pull) | `cycle-start` | Add `_emit_event()` call |
| Bottom of `cycle_post.py` (after commit/push, before idle) | `cycle-end` | Add `_emit_event()` call |
| `_write_status_bar()` in cycle_pre/post | `phase-change` | Piggyback on existing call |
| `_do_status_transitions()` in cycle_post | `status-transition` / `task-*` | Emit per transition |

### Key finding: cycle_pre and cycle_post already have all the data

`cycle_pre.py` has `_timestamp()`, role, cycle number. `cycle_post.py` has cycle-output.json
data including all status_transitions. No new data sources are needed — the scripts have
everything required for the minimal event set.

### `_write_status_bar()` is already the phase notification hook

Both `cycle_pre.py` and `cycle_post.py` call `_write_status_bar(role, phase, description)`.
This function writes to `.squidsquad/<role>/current-state`. It is called at every meaningful
phase transition. Adding `_emit_event()` alongside it is the cleanest emission pattern —
no new hooks needed, no changes to the creative loop.

### Status transitions are already structured in cycle-output.json

`cycle_post.py`'s `_do_status_transitions()` iterates over the `status_transitions` list.
Adding event emission here is trivial — each transition already has `number`, `from`, `to`.

---

## 3. Sub-Skill Design

### The emission sub-skill: a Python helper module

The cleanest design is a small Python module: `references/scripts/event_bus.py`.

```python
# references/scripts/event_bus.py

import json
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
HARNESS_PORT_FILE = REPO_ROOT / ".squidsquad" / ".harness-port"


def _get_port():
    """Read harness port from discovery file. Returns int or None."""
    try:
        content = HARNESS_PORT_FILE.read_text(encoding="utf-8").strip()
        return int(content) if content else None
    except (OSError, ValueError):
        return None


def emit(event_type: str, role: str, cycle_number: int = None, payload: dict = None):
    """Emit an event to the harness. Fire-and-forget. Never raises.

    If harness is not running (.harness-port missing or connection refused),
    silently returns None — does NOT crash the agent.
    """
    port = _get_port()
    if port is None:
        return None  # Harness not running — silent no-op

    event = {
        "event_type": event_type,
        "role": role,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    if cycle_number is not None:
        event["cycle_number"] = cycle_number
    if payload:
        event["payload"] = payload

    try:
        data = json.dumps(event).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/events",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=0.5)  # 500ms max — fire and forget
    except Exception:
        pass  # Connection refused, timeout, harness crashed — all silent
    return None
```

**Why `urllib` not `requests`**: stdlib only. No new dependencies. Consistent with Phase 1
research finding that FastAPI+uvicorn were already installed but no new deps were needed.

**Timeout of 0.5s**: Agent cycles are 30-minute intervals. Even a 500ms timeout on event
emission is negligible noise. But it prevents hung cycles if the harness becomes
unresponsive.

### How cycle_pre.py uses it

```python
# At top of cycle_pre.py main():
try:
    from event_bus import emit as _emit_event
except ImportError:
    def _emit_event(*a, **kw): pass  # Fallback if event_bus.py not deployed

# After pull completes:
_emit_event("cycle-start", role, cycle_number=cycle_number)

# In _write_status_bar() — optional piggybacking:
_emit_event("phase-change", role, payload={"phase": phase, "description": description})
```

### How cycle_post.py uses it

```python
# In _do_status_transitions(), after each successful transition:
_emit_event("status-transition", role, cycle_number=cycle_number,
            payload={"issue": number, "from": from_status, "to": to_status})

# At the very end of main(), before status bar write:
_emit_event("cycle-end", role, cycle_number=cycle_number,
            payload={"cycle_type": cycle_type, "duration_seconds": elapsed})
```

### Port discovery: `.squidsquad/.harness-port`

This was already locked in Phase 1 CONTEXT.md. The harness writes its port to
`.squidsquad/.harness-port` on startup. `event_bus.py` reads this file. If the file is
absent (harness not running), `_get_port()` returns `None` and emission is silently
skipped.

**No env var needed for agents.** The file-based discovery is already the mechanism.
Agents in their own clones can all read the same `.harness-port` file since all clones
share the same project root structure (they are sibling clones of the same repo, all
pointing to the same `.squidsquad/` directory via clone-isolation architecture).

**Note on clone isolation**: Each agent runs in its own clone at a path listed in
`.squidsquad/.local-config`. The `.squidsquad/` directory is inside the repo root.
However, `.harness-port` lives in the *main* project's `.squidsquad/` directory, not the
agent's clone. The agent's `REPO_ROOT` points to its own clone. This means `event_bus.py`
needs to read the *project-canonical* `.harness-port`, not the one in the agent's clone.

**Resolution**: `event_bus.py` should read from the agent's own clone's `.squidsquad/.harness-port`.
The harness writes to the main project's `.squidsquad/.harness-port`. For agents in sibling
clones to find it, either:
- **Option A**: Harness also writes to all known clone paths (complex, fragile).
- **Option B**: Each agent's clone has `.squidsquad/.harness-port` synced via git push.
  (Works but adds latency.)
- **Option C** (recommended): `event_bus.py` reads the port from `.squidsquad/.harness-port`
  in the agent's own clone. The cycle_pre.py git pull already syncs the file. Since cycle_pre
  pulls before emitting cycle-start, the port file is always current.

**Option C** is the right answer. The harness writes `.harness-port` to main branch,
git commit/push is part of harness startup. Agents pull at cycle start (cycle_pre already
does `git pull --rebase`). After pull, `.harness-port` is present. `event_bus.py` in the
agent's clone finds it.

**Edge case**: First cycle after harness starts — agent pulls, gets the port file, emits
correctly. This is fine.

---

## 4. Harness State Model

### In-memory model (extends Phase 1 AgentState)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
import threading

@dataclass
class AgentState:
    role: str
    # Phase 1 fields (existing)
    status: str = "unknown"     # spawning | alive | dead | stopped
    wrapper_pid: Optional[int] = None
    claude_pid: Optional[int] = None
    last_heartbeat: Optional[float] = None  # epoch from .health file
    clone_path: Optional[str] = None
    boot_time: Optional[datetime] = None
    # Phase 2 additions
    current_cycle: int = 0
    current_phase: str = ""
    current_task: str = ""
    last_cycle_start: Optional[datetime] = None
    last_cycle_end: Optional[datetime] = None
    last_cycle_type: str = ""   # active | quiet | suppressed
    last_event_at: Optional[datetime] = None
    event_count: int = 0

@dataclass
class EventRecord:
    event_type: str
    role: str
    timestamp: datetime
    cycle_number: Optional[int]
    payload: dict = field(default_factory=dict)
    received_at: datetime = field(default_factory=datetime.now)

class HarnessState:
    def __init__(self, max_events: int = 1000):
        self.agents: dict[str, AgentState] = {}
        self.events: List[EventRecord] = []
        self.max_events = max_events
        self._lock = threading.Lock()

    def ingest_event(self, event: EventRecord):
        with self._lock:
            # Update agent state
            agent = self.agents.setdefault(event.role, AgentState(role=event.role))
            agent.last_event_at = event.timestamp
            agent.event_count += 1
            if event.cycle_number:
                agent.current_cycle = event.cycle_number
            if event.event_type == "cycle-start":
                agent.last_cycle_start = event.timestamp
                agent.status = "alive"
            elif event.event_type == "cycle-end":
                agent.last_cycle_end = event.timestamp
                agent.last_cycle_type = event.payload.get("cycle_type", "")
            elif event.event_type == "phase-change":
                agent.current_phase = event.payload.get("phase", "")
                agent.current_task = event.payload.get("description", "")
            # Append to event stream (bounded)
            self.events.append(event)
            if len(self.events) > self.max_events:
                self.events = self.events[-self.max_events:]
```

### Why bounded event stream (not append-only log)

The harness is an in-memory process. An unbounded event list will grow forever across a
multi-day run. 1000 events at ~200 bytes each = ~200KB — negligible. This is fine for
Phase 2. Phase 3+ can add persistence (SQLite, log file) if needed.

---

## 5. New Harness Endpoints (Phase 2)

Adds to the Phase 1 endpoint set:

```
POST /events                  # Agent emits an event (body: EventRecord JSON)
GET  /state                   # Full harness state: all agents + recent events
GET  /state/<role>            # Single agent state
GET  /events?limit=50&role=pm # Filtered event stream
```

The `POST /events` endpoint validates the envelope and calls `harness_state.ingest_event()`.
It returns `{"ok": true}` immediately (no blocking). The 500ms client timeout means the
harness must respond in <500ms — trivially satisfied since it's just a dict write with a lock.

---

## 6. Console Display

### Streaming log (primary)

The harness console already shows agent start/stop events (Phase 1 design). Phase 2 adds
event stream printing:

```
[14:30:00] skill      cycle-start    cycle=42  pull=ok
[14:30:01] skill      phase-change   triaging | tracker-protocol — Building work queue
[14:31:05] skill      status-trans   #4500 approved → in-progress
[14:31:05] skill      phase-change   coding | implementing — #4500 harness event bus
[14:45:00] skill      cycle-end      cycle=42 active (15m 00s)
[14:45:30] pm         cycle-start    cycle=723 pull=ok
```

Format: `[HH:MM:SS] <role padded>  <event_type padded>  <summary>`

This is printed by the harness to its own terminal as events arrive via POST /events.

### Optional: live dashboard table

A periodically-refreshed (every 5s) table showing current agent state, similar to
health_check.py's `format_table()`. This is a "nice to have" for Phase 2 — the streaming
log is sufficient for the MVP.

**Recommendation**: Streaming log only for Phase 2. Dashboard table as a Phase 3 option.

---

## 7. Failure Handling

### What if the harness is down when an agent tries to emit?

**Strategy: fire-and-forget with silent failure.**

From `event_bus.emit()`:
1. `_get_port()` reads `.harness-port`. If file missing → returns None → no HTTP call.
2. If `urllib.request.urlopen()` raises any exception (ConnectionRefused, timeout, socket
   error) → silently caught → `pass`.
3. Agent cycle continues normally.

**No retry, no buffer, no queue.** Rationale:
- Events are informational — they update the operator's dashboard, not the agent's behavior.
- Missing a few events during a harness restart is acceptable. The harness will reconstruct
  agent state from the next cycle-start event.
- Buffering would require the agent to manage a queue, adding complexity and failure modes
  to the agent itself. The harness is an optional enhancement — it must not burden agents.

**What if the harness restarts mid-run?**

The harness loses its in-memory state. On restart, it starts with empty agent state. The
next `cycle-start` event from each agent repopulates the harness's view. There is a window
of 0–30 minutes (one cycle interval) where the dashboard shows no data. This is acceptable.

If persistence is needed (e.g., harness must survive restarts), the Phase 1 harness already
polls `.health` files. The harness could re-seed its state model from those files on startup.
This is a Phase 3 concern.

---

## 8. Backward Compatibility

### If harness is not running

`event_bus.py` reads `.squidsquad/.harness-port`. If the file does not exist, `_get_port()`
returns `None`. No HTTP call is made. The agent cycle proceeds exactly as today.

### If `event_bus.py` is not deployed to an agent's clone

`cycle_pre.py` and `cycle_post.py` import `event_bus` with a try/except:

```python
try:
    from event_bus import emit as _emit_event
except ImportError:
    def _emit_event(*a, **kw): pass
```

An agent without `event_bus.py` simply skips all event emission. The harness won't receive
events from that agent, but nothing breaks.

### Existing scripts unaffected

`boot_remote.py`, `start_team.py`, `health_check.py`, `reboot_agent.py` — none of these are
modified. They continue to work standalone. The event bus is additive: cycle_pre + cycle_post
gain import calls, nothing else changes.

---

## Impact Analysis

- **Files touched**:
  - `references/scripts/event_bus.py` — NEW (emission helper)
  - `references/scripts/harness.py` — EXTEND (add `/events` endpoint, state model,
    console printing) — this is the Phase 1 file being built
  - `references/scripts/cycle_pre.py` — ADD import + 2-3 `_emit_event()` calls
  - `references/scripts/cycle_post.py` — ADD import + 2-3 `_emit_event()` calls
  - `references/sub-skills/common/cycle-runner.md` — UPDATE to document event emission
    (informational, no behavior change for agents)
- **Behavior changes**: Agents gain a non-blocking HTTP POST at cycle boundaries. Timing
  impact is negligible (<500ms fire-and-forget, typically <5ms on localhost).
- **Dependencies**: None new. `urllib` is stdlib. FastAPI + uvicorn already installed.

---

## Side Effects

- **Risk 1**: Port file staleness. If `.harness-port` contains a stale port (harness crashed
  and left the file), agents will `POST` to a dead port and get `ConnectionRefused`. This is
  caught silently. — Severity: **Low** — Mitigation: Phase 1 CLI already handles stale port
  detection; agent-side emission gracefully falls through.
- **Risk 2**: Harness becomes a subtle performance dependency. If the harness is running but
  slow (CPU thrash), the 500ms timeout means agents could hang up to 500ms per emission.
  At 3 emissions per cycle, worst case 1.5s overhead per 30-minute cycle — trivial.
  — Severity: **Low**
- **Risk 3**: Clone isolation means `.harness-port` is in each agent's clone. Each agent's
  clone's `.squidsquad/.harness-port` is only current after `git pull`. If an agent hasn't
  pulled yet when the harness starts, the file is absent, and emission silently no-ops until
  the next pull. — Severity: **Very Low** (cycle_pre always pulls first)
- **Risk 4**: `event_bus.py` import added to `cycle_pre` and `cycle_post`. If the file has
  a syntax error (introduced by dev mistake), the try/except fallback masks the error — the
  agent silently skips event emission instead of alerting. — Severity: **Low** — Mitigation:
  unit tests for event_bus.py in `tests/`.

---

## Edge Cases

- **Agent emits `cycle-start` but never `cycle-end`** (agent crashes mid-cycle): Harness
  notes `last_cycle_start` but never updates `last_cycle_end`. The operator can see the agent
  went silent. This is useful information — no mitigation needed.
- **Two agents with same role** (misconfigured): Harness state dict is keyed by role. Second
  agent's events overwrite first's. Acceptable for Phase 2 (clone isolation already prevents
  this in practice via `.pid` singleton lock).
- **Harness receives events after it has been stopped by `squidsquad stop`**: The harness
  process is gone. Connection refused. All silent. No issue.
- **Event payload contains non-serializable types**: `event_bus.emit()` calls `json.dumps()`
  with stdlib defaults. Any non-serializable payload will raise `TypeError`. Mitigation: wrap
  the `json.dumps()` call with a fallback (`default=str`) or validate payloads to only include
  str/int/bool/list/dict.
- **Very high event volume** (e.g., agent emitting on every `_write_status_bar` call): current-
  state is written every ~30 seconds in creative work. At 30-minute cycles, ~60 phase-change
  events per cycle across 4 agents = 240 events/cycle. At 1000-event buffer, ~4 cycles of
  history retained. This is fine.

---

## Integration Risks

- **#4439 (Phase 1)**: Phase 2 depends on Phase 1 harness being built and running. The
  harness.py file does not exist yet (confirmed: `ls references/scripts/harness*` found
  nothing). Phase 2 implementation cannot begin until harness.py exists with the FastAPI
  server and `/events` endpoint added.
- **cycle_pre.py / cycle_post.py changes**: These are shared mechanical scripts used by
  all 4 agent roles (skill, pm, qa, dm). Any change here affects all agents simultaneously.
  The try/except import guard ensures zero behavior change for agents without `event_bus.py`.

---

## Upgrade & Migration

- **New config values**: None required. No new config fields needed.
- **New files**: `references/scripts/event_bus.py` — must be copied to each agent clone.
  `compose.py deploy-all` handles propagation of `references/` to live `.squidsquad/` per
  agent.
- **Template changes**: None. `cycle_pre.py` and `cycle_post.py` are scripts, not agent
  templates. No agent CLAUDE.md changes needed for Phase 2 emission (emission is mechanical,
  not creative-phase agent behavior).
- **Sub-skill documentation**: `references/sub-skills/common/cycle-runner.md` should be
  updated to describe event emission as a mechanical behavior. This is informational for
  agents who read it, not behavioral.
- **Upgrade steps**: `squidsquad-upgrade` should copy `event_bus.py` to all clone
  `references/scripts/` directories. Existing agents without it silently skip emission —
  graceful degradation is built in.
- **Graceful degradation**: Full backward compat. If `event_bus.py` is missing from a clone,
  all imports fail silently (try/except guard). If harness is not running, all emissions are
  no-ops. Phase 2 features are strictly additive.

---

## Capability Gaps

No capability gaps. All required packages (`urllib`, `json`, `threading`, `dataclasses`
from Python 3.7+) are stdlib. FastAPI and uvicorn already present from Phase 1.

---

## Open Questions

- **Q1**: Should `event_bus.py` also be imported by the *creative* agent (Claude) or only
  by the mechanical scripts (cycle_pre, cycle_post)? **Why it matters**: If agents emit
  events during creative work (e.g., "I picked up task #4500"), events are richer but the
  creative agent must be instructed to call a shell command. The current design keeps
  emission entirely in deterministic scripts — cleaner, but no mid-cycle events.
  **Recommendation**: Keep emission in mechanical scripts only for Phase 2. Mid-cycle
  events are a Phase 3 enhancement.

- **Q2**: Should `.harness-port` be committed to git (so agents get it on pull) or written
  as a runtime-only file (gitignored)? **Why it matters**: If gitignored, agents in sibling
  clones never see the port file — their `event_bus.py` always returns `None`. If committed
  on harness start, agents get it on next pull. **Recommendation**: Harness commits
  `.harness-port` to main on startup (or writes to a path that gets committed as part of
  normal cycle_post git flow). Alternatively, the harness could also copy the port file to
  each agent's clone path directly (reads `.local-config`, writes port file to each clone).
  This is the most reliable option — no git required.

- **Q3**: Should the harness console show a live dashboard (rich/curses) or just a scrolling
  log? **Why it matters**: A dashboard requires `rich` or `curses`; a scrolling log needs
  only `print`. **Recommendation**: Scrolling log for Phase 2 (zero new dependencies).
  Dashboard as optional Phase 3+ with `rich` (already evaluating it for Phase 1 anyway).

- **Q4**: Should `POST /events` validate the event schema strictly (reject malformed events
  with HTTP 400) or accept anything? **Why it matters**: Strict validation catches agent
  bugs but adds harness complexity. Loose acceptance is simpler but lets bad data in.
  **Recommendation**: Loose validation for Phase 2 — require only `event_type`, `role`,
  `timestamp`; accept unknown fields. Strict validation as Phase 3 hardening.

- **Q5**: Should the harness write a `.squidsquad/.harness-port` copy to each agent's clone
  on start (reading `.local-config`), or rely on git-committed port file? **Why it matters**:
  Direct write to clone paths is instant and doesn't require a git cycle. But it adds
  file-system coupling between the harness and agent clones. **Recommendation**: On harness
  startup, write port to both the main repo's `.squidsquad/.harness-port` AND to each agent
  clone's `.squidsquad/.harness-port` directly (reading from `.local-config`). This is the
  most reliable option and doesn't require agents to pull.

---

## Recommendation

Straightforward. Phase 2 implementation risk is low:

1. `event_bus.py` is ~50 lines of stdlib Python. Unit-testable in isolation.
2. Emission points in `cycle_pre.py` and `cycle_post.py` are well-defined and already have
   all required data.
3. Backward compatibility is guaranteed by the try/except import guard and the `_get_port()`
   None check.
4. The harness state model is a straightforward extension of Phase 1's `AgentState` dict.

**Dependency**: Phase 1 (`harness.py`) must exist and be at least partially implemented
before Phase 2 can be wired in. Recommend sequencing: Phase 1 task completes → Phase 2
adds `POST /events` to `harness.py` + delivers `event_bus.py` + updates cycle_pre/post.

**Resolve Q2 and Q5** (port distribution to agent clones) before implementation begins —
this is the only meaningful architectural decision left open.

---

## Vault Candidates

- **Type**: pattern — "Fire-and-forget event emission with try/except guard" — **Why**:
  the pattern of wrapping cross-process calls in a silent fallback (try/except + port file
  check) is reusable for any optional harness integration going forward.
- **Type**: decision — "Event emission lives in mechanical scripts, not creative agent" —
  **Why**: keeping emission out of agent-visible instructions keeps the creative loop clean
  and makes emission deterministic and testable.
- **Type**: learning — "Port distribution across sibling clones is the critical Phase 2 risk"
  — **Why**: the clone-isolation architecture means `.harness-port` is not automatically
  visible in agent clones; this is the one non-obvious problem that must be solved at design
  time.

---

*Research by PM subagent — 2026-04-28*
