# FEAT-PM-7630 Context — Event-Driven Agent Architecture

## Scope

Transform SquidSquad from a cycle-based polling model to a pure event-driven architecture. The harness owns all mechanical operations. Agents are persistent sessions that sit idle until the Monitor tool detects an event, then execute exactly one creative task and ack the event. No cycles, no /loop, no cycle_pre/cycle_post — agents are stateless creative workers within a persistent session.

### What this delivers
- 5 universal events (assigned-to, stop-requested, shipped, version-bump, ack) replace 30+ event types
- Ack-based health monitoring replaces PID polling — no ack within timeout = retry → kill → reboot
- External activity detector monitors GitHub for non-SquidSquad activity, routes to PM via assigned-to
- Event bus becomes the sole agent activation mechanism
- Monitor tool (Claude Code v2.1.98+) replaces /loop as the wake mechanism
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

### 2. Stop signal — stop-requested event + ack confirmation
Harness emits `stop-requested {source, target}` on the event bus. Source can be another agent, human (Ctrl+C), or harness itself. Agent finishes current event atomically, checkpoints working-state.md, stops Monitor, and emits `ack {event_id}`. The harness recognizes an ack of a stop-requested event as shutdown confirmation. When all agents have acked their stop-requested events, the harness can exit cleanly. If reboot was requested: harness kills PID and restarts agent.

### 3. Kill cycles entirely — pure event-driven, no config gate
No /loop, no cycle_pre.py, no cycle_post.py, no cycle-input.json, no cycle-output.json, no cycle counters. The cycle concept is replaced entirely by event-driven processing. Event ID is the tracking unit. Per-event log entries replace per-cycle iteration logs. No `event-driven: yes/no` config gate — event-driven is the only mode. The old cycle code is removed, not retained for backward compat.

**Rationale**: The cycle was invented because agents had no wake mechanism. /loop was the answer to "how do agents check for work?" With the Monitor tool + event bus, agents react to work in real-time. Maintaining a config gate means maintaining two code paths indefinitely, which contradicts the goal of killing cycles entirely. If something breaks during development, fix it on the branch — that's what feature branches and QA are for.

### 4. Output contract — ack event via POST /events (replaces closure API)
Every event has a unique event ID. When the agent finishes processing an event, it emits `ack {event_id}` via the existing `POST /events` endpoint. No dedicated closure endpoint (`POST /events/{id}/complete` is eliminated). No structured closure payload — the agent handles all side effects (transitions, comments, commits) during creative work, then simply acks. The harness marks the event as handled.

**Override of original Decision #4**: The original design had a structured closure payload with status transitions, tracker comments, and commit messages passed to the harness for execution. This is replaced by the simpler model where agents do their own work and just signal completion. Rationale: agents already have full access to tracker.py, git_ops.py, and all mechanical scripts. Having the harness re-execute side effects from a payload is redundant complexity.

### 5. 5 events, all L1 — universal event model
The complete event model has exactly 5 event types, all at L1 (universal):

| Event | Direction | Payload | Purpose |
|---|---|---|---|
| `assigned-to` | agent/human/harness → target | {role, issue/pr} | Work handoff |
| `stop-requested` | agent/human/harness → target | {source, target} | Graceful shutdown |
| `shipped` | DM → harness → all | {issue/pr} | Delivery announcement |
| `version-bump` | DM → harness → all | {version} | Version announcement |
| `ack` | agent → harness | {event_id} | Confirms event handled |

No L2/L3 event-reaction sub-skills needed. Roles handle events from their existing role instructions. When an agent receives `assigned-to`, it reads the issue/PR from the forge and acts per its role — no event-specific guidance required. L3 domain variants inherit L2 behavior naturally.

**Forge is the source of truth.** `assigned-to` carries only {role, issue/pr}. All context — comments, status, history, findings — lives in the GitHub Issue or PR. Events are routing signals, not context carriers.

### 6. Terminal cleanup — Harness closes on clean stop
When an agent acks a `stop-requested` event, the harness issues a platform-appropriate terminal window close (Windows: `taskkill /PID`, Unix: `kill` the terminal process). Only on intentional stop — not on crash or context-pressure restart. Requires tracking the terminal PID separately from the agent PID at spawn time, stored in `.harness-state.json`.

### 7. Events are atomic — never interrupted mid-handling
When an agent is processing an event, it completes the entire unit of work before picking up the next event. Monitor notifications queue behind the current event. An event = one complete unit of work (verify a task, investigate a stall, process a PR merge). The agent finishes all steps, all transitions, all comments for the current event before reading the next.

### 8. Ack-based health monitoring — replaces PID polling
Health monitoring is built into the event protocol. No separate health watcher:
1. Harness sends event to agent
2. If no ack within timeout (default 10 min), harness re-emits the event (retry)
3. After max retries (default 3), harness declares agent dead, kills PID, reboots agent, re-emits event to rebooted agent
4. If reboots also fail, harness escalates to PM (self-healing tier 2)

PID check remains as a secondary verification before killing (OS-level truth).

**Override of original Decision #11**: The original design said events are single-shot and never re-emitted. The ack-based model intentionally uses re-emission as the retry mechanism. Rationale: simpler than per-event-class timeout matrices, more self-healing (retry before escalate), and integrates health monitoring and event delivery into one mechanism.

### 9. External activity detector — monitors GitHub for non-SquidSquad activity
Harness monitors GitHub for issues, PRs, and commits NOT created by SquidSquad agents. When external activity is detected, harness emits `assigned-to {role: "pm", issue: <number>}` for PM to triage. The detector:
- Filters by `squidsquad` label and agent commit prefix — must NOT react to SquidSquad's own changes
- Replaces the old git-watcher and tracker-watcher concepts (which emitted their own event types)
- Translates all external signals into `assigned-to` events — no new event types exposed to agents

### 10. Behavioral tuning defaults at L1, overridable at L4
Tuning defaults ship with SquidSquad core (L1). Projects override via config.md (L4):
- `scan-cooldown`: 15 minutes between self-initiated scans, scan immediately on idle
- `events-atomic`: true (events never interrupted mid-handling)

### 11. Scan trigger — agent self-initiates per cooldown
Agent self-initiates improvement scans per 15-minute cooldown when idle. No `scan-due` event from harness.

**Override of original Decision #5**: The original design had harness emit `scan-due` after 10 min idle. This is simplified — the agent knows when it's idle (no events to process) and can self-initiate per the cooldown. The harness doesn't need to track idle time per agent.

### 12. Each ack is independent — no multi-consumer tracking
Announcement events (`shipped`, `version-bump`) go to all agents. Each agent acks independently. Harness does NOT wait for all agents to ack before marking the event handled. No multi-consumer tracking.

### 13. Idempotency — ack is idempotent
Emitting `ack {event_id}` multiple times is safe. Harness processes the first ack and ignores duplicates.

**Override of original Decision #12**: The original design had structured idempotency markers (HTML markers in tracker comments, commit trailers, API result cache). With the simplified ack model where agents handle their own side effects, idempotency is the agent's responsibility during creative work (tracker.py already validates from→to transitions). The ack itself is simply idempotent.

### 14. No file-based event delivery — poll script + HTTP API only
The harness does NOT write files to agent filesystems. Event delivery is API-only: agents run a poll script that queries `GET /events` from the harness. This eliminates file coordination, clone path management, file cleanup, and TOCTOU races on Windows.

### 15. Phased implementation — keep the loop alive until the last phase
Implementation is phased. Each phase keeps the existing /loop cycle model alive alongside new event infrastructure. The loop is only killed in the final phase. Each phase is independently testable and verifiable. The dev agent drafts the implementation plan with phase boundaries.

## Dev Discretion (dev agent can choose)

- Event bus storage format (file-per-event vs. append-only log vs. SQLite) — whatever is most reliable on Windows
- Monitor tool invocation pattern (exact API call syntax, polling interval if any)
- Harness continuous monitor implementation (thread per monitor vs. async loop vs. scheduled executor)
- Migration path for cycle_pre/cycle_post code into harness (refactor in place vs. rewrite)
- Per-event log format and storage (replaces iteration logs)
- Phase boundaries and task breakdown for implementation plan
- Whether `cycle.py` is renamed or kept as a utility module

## Side Effect Mitigations (required)

- **Event idempotency**: Agent handles side effects (transitions, comments, commits) during creative work. tracker.py already validates from→to transitions. Ack itself is idempotent.
- **Working-state continuity**: Working-state.md must be checkpointed after each event completion and on stop-requested. Agent writes working state directly.
- **Context pressure management**: Harness monitors context pressure via ack timeout (agent stops acking = something wrong). PID check as secondary verification.
- **Concurrent event handling**: Agent processes one event at a time. Harness must not emit a second event to the same role while the first is unacked (queue events per role).

## Requirements from Gap Review (DeepSeek analysis)

### Phase 1 Prerequisites (must be done before event-driven waking works)

- **Event bus disk persistence**: EventStream is currently an in-memory deque (1000 events, lost on harness restart). Since events are the sole activation mechanism, they MUST survive restarts. Dev chooses storage format.
- **Clone event bus discovery fix**: `event_bus_reader.py _discover_port()` walks parent directories to find `.harness-port`. Clone isolation uses sibling directories, not nested ones. The walk never finds the port — agents in clones silently receive zero events. Fatal in event-driven model.
- **Per-role in-flight event queue**: Harness must track which events have been dispatched but not yet acked, per role. Must not emit a second event to the same role while one is unacked.
- **Harness thread safety**: `_update_agent_from_event` and `update_health` both mutate AgentState fields outside the lock. Must be made thread-safe before event volume increases.

### Monitor Tool Validation Checklist (human upgraded Claude Code)

Before prototyping the wake mechanism, validate:
- [ ] Monitor tool exists and is callable from agent sessions
- [ ] Monitor can watch custom shell command stdout (for event bus polling)
- [ ] Monitor timeout behavior: what is the max timeout? Does it auto-reconnect?
- [ ] Multiple Monitor subscriptions per session
- [ ] Windows behavior
- [ ] Latency: actual wake latency from event emission to agent awareness

## Upgrade Path (required)

- **No config gate**: Event-driven is the only mode. No `event-driven: yes/no` flag.
- **Claude Code upgrade**: Human must upgrade to v2.1.98+ before prototyping. Validate Monitor tool API.
- **Template migration**: All cycle prose stripped from instructions.md and sub-skills. Replaced with event-driven workflow guidance.
- **Phased rollout**: Each implementation phase is independently testable. The loop stays alive until the final phase removes it.

## Out of Scope

- **Chat events** — agent-to-agent and human-to-agent messaging, separate task
- **External model routing changes** — model_router.py is unaffected
- **Tracker protocol changes** — GitHub Issues remains the tracker, labels/transitions unchanged
- **Vault protocol changes** — vault reading/writing stays the same
- **Soul shepherd changes** — character signal detection remains agent creative work
- **Branch workflow changes** — feature branches, PR lifecycle managed by harness (already partially true)
- **Stateless spawn model** — decided against; using persistent session + Monitor tool instead
