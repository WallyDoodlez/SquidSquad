# FEAT-PM-7630 Context — Event-Driven Agent Architecture

## Scope

Transform SquidSquad from a cycle-based polling model to a pure event-driven architecture. The harness owns all mechanical operations and emits events. Agents are persistent sessions that sit idle until the Monitor tool detects an event, then execute exactly one creative task and close the event via API callback. No cycles, no /loop, no cycle_pre/cycle_post — agents are stateless creative workers within a persistent session.

### What this delivers
- Harness continuous monitors replace all agent cycle steps (pipeline sentinel, health check, BRIEFING staleness, scan triggers, etc.)
- Event bus becomes the sole agent activation mechanism
- Monitor tool (Claude Code v2.1.98+) replaces /loop as the wake mechanism
- Event closure API with mandatory acknowledgment and diagnostic detection of unclosed events
- Agent templates shrink by ~60% (all cycle prose removed)
- Per-event tracking replaces per-cycle tracking (event ID = tracking unit)

### What this supersedes
- #6056 (Replace /loop with Monitor tool) — absorbed into wake mechanism
- #5775 (Move pipeline sentinel to harness) — absorbed into Phase 1
- #5613 (Phase 3+ event types) — absorbed into new event types
- The entire cycle-runner sub-skill concept

## Locked Decisions (human decided)

### 1. Wake model — Persistent session + Monitor tool + poll script
Agents stay alive between work items. A lightweight poll script (`event_poll.py`, ~30 lines) queries `GET /events?since=<cursor>&role=<role>` from the harness API at configurable interval. The Monitor tool (Claude Code v2.1.98+) watches the poll script's stdout. When new events arrive, the script outputs them and the Monitor tool wakes the agent. No file-based event inbox — the harness is a pure HTTP server and does not write to agent filesystems. The poll script reads `.harness-port` locally for discovery (works for clones). Human will upgrade Claude Code to v2.1.98+ before prototyping; validate Monitor tool exists and works before committing.

### 2. Stop signal — Event bus stop event
Harness emits `intent:stop-requested` on the event bus. The Monitor tool (already watching for events) detects it. Agent reads the event, checkpoints working-state.md, and exits cleanly. Unified channel — wake and stop use the same event bus.

### 3. Kill cycles entirely — pure event-driven
No /loop, no cycle_pre.py, no cycle_post.py, no cycle-input.json, no cycle-output.json, no cycle counters, no iteration logs in the current format. The cycle concept is replaced entirely by event-driven processing. Event ID is the tracking unit. Per-event log entries replace per-cycle iteration logs.

**Rationale**: The cycle was invented because agents had no wake mechanism. /loop was the answer to "how do agents check for work?" With the Monitor tool + event bus, agents react to work in real-time. The cycle becomes a polling wrapper around an event system — which is the exact pattern #7630 eliminates. All mechanical operations cycles provided (health, git pull, tracker queries, pipeline sentinel) move to harness continuous monitors.

### 4. Output contract — Event closure via harness API callback
Every event emitted by the harness has a unique event ID. When the agent finishes processing an event, it MUST call `POST /events/{event_id}/complete` with a structured result payload (status transitions, tracker comments, commit message, summary). The harness processes the result (executes transitions, commits, pushes) and marks the event closed.

**Unclosed events = diagnostic signal**: If an event remains unclosed beyond a timeout, the harness knows something is wrong — agent crash, context pressure exceeded, stuck in creative work. The harness can diagnose (check PID, context pressure), take action (respawn, re-emit, alert human), and report the failure. No silent failures.

### 5. Scan trigger — scan-due event on 10-minute idle timeout
Harness tracks `last_event_completed[role]` timestamp per role. After 10 minutes with no completed events, harness emits a `scan-due` event. PM wakes, runs improvement scan, closes the event with findings. Deterministic — harness enforces it regardless of agent prose. Issue gate: harness checks for open issues assigned to the role before emitting (skip scan if role has active bugs).

### 6. Terminal cleanup — Harness closes on clean stop
When an agent exits with `intent=stopping`, the harness issues a platform-appropriate terminal window close (Windows: `taskkill /PID`, Unix: `kill` the terminal process). Only on intentional stop — not on crash or context-pressure restart. Requires tracking the terminal PID separately from the agent PID at spawn time, stored in `.harness-state.json`.

## Dev Discretion (dev agent can choose)

- Event bus storage format (file-per-event vs. append-only log vs. SQLite) — whatever is most reliable on Windows
- Monitor tool invocation pattern (exact API call syntax, polling interval if any)
- Event closure API endpoint design (`POST /events/{id}/complete` is the concept; exact path, payload schema, error handling is dev's call)
- Harness continuous monitor implementation (thread per monitor vs. async loop vs. scheduled executor)
- How to handle event re-emission on agent crash (idempotency strategy for transitions/comments)
- Migration path for cycle_pre/cycle_post code into harness (refactor in place vs. rewrite)
- Per-event log format and storage (replaces iteration logs)

## Side Effect Mitigations (required)

- **Event idempotency**: Status transitions called via the closure callback must be idempotent. If an event is re-emitted (after crash recovery), processing it twice must not create duplicate tracker comments or invalid state transitions. tracker.py already validates from→to transitions; comments need dedup by event_id.
- **Working-state continuity**: With persistent sessions and event-driven work, working-state.md must be checkpointed after each event completion so crash recovery can resume. The closure callback should include working state update.
- **Context pressure management**: Harness must monitor context pressure files and trigger restarts independently. Agent no longer checks this (no cycle step for it). Harness reads `.squidsquad/<role>/context-pressure` and sets `intent=restarting` when exceeded.
- **Git operations**: Harness owns git pull (before delivering work-context) and git commit/push (after processing closure callback). Agent never runs git operations directly in the event-driven model.
- **Concurrent event handling**: Agent processes one event at a time. Harness must not emit a second event to the same role while the first is unclosed (queue events per role).
- **Graceful degradation during upgrade**: Feature is gated behind `event-driven: yes` config. Existing cycle model preserved when `event-driven: no`. Both models cannot run simultaneously for the same role.

## Requirements from Gap Review (DeepSeek analysis)

### Phase 2 Prerequisites (must be done before event-driven waking works)

- **Event bus disk persistence**: EventStream is currently an in-memory deque (1000 events, lost on harness restart). Since events are the sole activation mechanism, they MUST survive restarts. Dev chooses storage format (file-per-event, append-only log, SQLite).
- **Clone event bus discovery fix**: `event_bus_reader.py _discover_port()` walks parent directories to find `.harness-port`. Clone isolation uses sibling directories (e.g., `../SquidSquad-skill/`), not nested ones. The walk never finds the port — agents in clones silently receive zero events. This is a latent bug today that becomes fatal with event-driven architecture.
- **Per-role in-flight event queue**: Harness must track which events have been dispatched but not yet closed, per role. Must not emit a second event to the same role while one is unclosed.
- **Harness thread safety**: `_update_agent_from_event` and `update_health` both mutate AgentState fields outside the lock. Must be made thread-safe before event volume increases.

### Monitor Tool Validation Checklist (human upgraded Claude Code)

Before prototyping the wake mechanism, validate:
- [ ] Monitor tool exists and is callable from agent sessions
- [ ] Monitor can watch custom shell command stdout (for event bus polling)
- [ ] Monitor timeout behavior: what is the max timeout? Does it auto-reconnect?
- [ ] Multiple Monitor subscriptions per session: can one session watch for both work events and stop events?
- [ ] Windows file watching behavior: does Monitor use inotify/ReadDirectoryChanges or polling?
- [ ] Latency: what is the actual wake latency from event emission to agent awareness?

### Event Crash Recovery

- **Closure crash window**: If harness crashes between processing the closure callback and persisting "event closed" state, events replay on restart causing duplicate work. Need atomicity strategy: either persist "closed" before executing side effects (at-most-once), or make all side effects idempotent (at-least-once).
- **Agent crash mid-event**: Health polling (5s) detects dead agent. Must distinguish "crashed mid-event" from "working on long task." Timeout per event type: short tasks (scan, comment) = 5 min, long tasks (implementation) = 60 min.

## Upgrade Path (required)

- **Pre-public**: No migration needed. Feature gated behind config flag.
- **Claude Code upgrade**: Human must upgrade to v2.1.98+ before prototyping. Validate Monitor tool API.
- **Config**: New `event-driven: yes/no` flag. New `scan-idle-timeout: 10` (minutes). New `wake-mechanism: monitor` (future: could support `spawn` fallback).
- **Template migration**: All cycle prose stripped from instructions.md and sub-skills. Replaced with event handler descriptions: "when woken by event X, do Y, close event via API."

### 7. Event reactions follow L1-L4 layered structure
Event reactions are NOT a flat single sub-skill. They follow the existing L1-L4 compose layers:
- **L1 (universal)**: `common/event-driven-workflow.md` + `common/event-reactions.md` (stripped to universal-only: stop-requested, idempotency, catch-all)
- **L2 (role-specific)**: `roles/{role}/event-reactions.md` — each role gets its own reaction table (PM, Technical Worker, Verifier, DM)
- **L3 (behavioral adaptation)**: Separate mechanism from SOUL.md. Soul is personality only. Behavioral tuning (event-sensitivity, reaction-latency, scan-priority) uses config or dedicated behavior files.
- **L4 (human overrides)**: config.md fields for muting events, tuning timeouts, setting escalation thresholds

### 8. Harness filters mechanical events before delivery
18 of 32 event types are purely mechanical (git ops, cycle bookkeeping, work lifecycle). The harness filters these out — agents only see the 14 events requiring creative judgment. This saves agent context and prevents LLMs from "noting" events that need no action.

### 10. No file-based event delivery — poll script + HTTP API only
The harness does NOT write files to agent filesystems (no `event-inbox/`, no `wake-event.json`). Event delivery is API-only: agents run a poll script that queries `GET /events` from the harness. This eliminates file coordination, clone path management, file cleanup, and TOCTOU races on Windows. The harness remains a pure HTTP server.

### 9. Role terminology in PRD
PRD uses generic role terminology: PM, Technical Worker (dev/skill), Verifier (QA), DM. Event-reaction sub-skills are per-role regardless of what the technical worker role is named.

## Out of Scope

- **External model routing changes** — model_router.py is unaffected by event-driven architecture
- **Tracker protocol changes** — GitHub Issues remains the tracker, labels/transitions unchanged
- **Vault protocol changes** — vault reading/writing stays the same, only the trigger mechanism changes (harness emits vault-reflect event instead of agent checking a counter)
- **Soul shepherd changes** — character signal detection remains agent creative work, triggered by events
- **Branch workflow changes** — feature branches, PR lifecycle managed by harness (already partially true)
- **Stateless spawn model** — decided against; using persistent session + Monitor tool instead
