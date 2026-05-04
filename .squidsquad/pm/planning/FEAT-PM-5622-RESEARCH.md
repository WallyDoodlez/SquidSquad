Now I have a thorough understanding of the codebase. Let me compile the research document.

```markdown
# FEAT-PM-5622 Research — Phase 4: Agent Event Bus Consumer (Read Side)

## Summary

Phase 4 (#5622) closes the communication loop: agents READ from the harness event bus, not just write to it. Phase 2 (#4709) establishes fire-and-forget event emission (agents POST to harness `/events`). Phase 4 adds the read path: in `cycle_pre.py`, agents query `GET /events` with filtering to discover relevant events since their last cycle, surface them into `cycle-input.json`, and optionally trigger mechanical reactions before the agent's creative phase begins.

**Recommendation**: **Feasible — design is clean.** The read path is simpler than the write path. A new `event_bus_reader.py` (~80 lines, stdlib `urllib`) queries `GET /events` with `since=<id>` and `role=` filters. `cycle_pre.py` adds a call after its existing pull-and-triage sequence (but before writing `cycle-input.json`), injecting a `recent_events` field. A new `last_processed_event_id` field in `working-state.md` prevents re-processing. The primary risks are **loop prevention** (self-reaction, cascade) and **mechanical reaction false positives** — both manageable with conservative defaults.

**Primary risks**:
1. **Event loops**: Agent A reacts to B's event → emits new event → B reacts → cascades. Mitigated by self-event filtering, processed-event markers, and causal chain depth limiting.
2. **False-positive mechanical reactions**: Auto-transitioning on `pr-merge` when conditions aren't met could corrupt tracker state. Mitigated by conservative condition gating (must match issue number, status, and role).
3. **Phase 2 not yet landed**: This research is forward-looking. The bus doesn't exist yet, so Phase 4 design must validate against Phase 2 design docs, not running code.

---

## Vault Context

- **BRIEFING.md priorities**: #4709 EPIC Harness Phase 2 is "planned, high, role:skill" and "ready for approval." Phase 4 builds directly on Phase 2's event stream. #5613 "Phase 3+ event opportunities" is also pending and overlaps with the read-API design question (Phase 3 vs Phase 4 boundary).
- **Related decisions**: [[decision-clone-isolation-architecture]] — each agent reads the bus from its own clone via HTTP, same as Phase 2 POST. Port discovery via parent-dir walking (already battle-tested in `cycle_post.py:_discover_harness_port()`). [[decision-cycle-runner-architecture]] — mechanical shell / agent core split means read happens in `cycle_pre.py` (mechanical), not during creative phase.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — event consumption belongs in mechanical scripts, not agent creative instructions. The agent sees pre-filtered events in structured JSON. [[pattern-model-router-architecture]] — same "thin adapter, thick common core" pattern applies: `event_bus_reader.py` is a thin HTTP client; `cycle_pre.py` does the filtering/surfacing.
- **Human preferences**: "Systems should self-heal: detect stuck states → unstick immediately → file root-cause bug → agent fixes gap." Mechanical reactions enable this — e.g., auto-transition on `pr-merge` removes manual cycle latency. "Prefers direct/mechanical checks over indirect state files" — event bus is the direct mechanism; the `last_processed_event_id` field in `working-state.md` is the minimum viable persistence.
- **Related learnings**: [[learning-atomic-migration-strategy]] — Phase 4 is additive (like Phase 2). Agents without `event_bus_reader.py` silently skip the read step; `recent_events` is an empty list in `cycle-input.json`. Zero breakage for non-upgraded agents.

---

## Impact Analysis

- **Files touched**:
  - `references/scripts/event_bus_reader.py` — **NEW** (~80–100 lines). `GET /events` with `since=<id>`, `role=<role>`, `event_type=<type>` query params. Returns JSON list of events. Same port discovery via parent-dir walking as `event_bus.py` emit side. `urllib` stdlib only.
  - `references/scripts/harness.py` — **EXTEND**. Add `GET /events` endpoint with query param filtering (lines ~500 area, after existing agent routes). The bounded deque (`maxlen=1000`) exists per Phase 2 design. Filtering happens in-memory on the deque.
  - `references/scripts/cycle_pre.py` — **EXTEND** (~20 lines). After triage/build phase (line ~953 area), call `event_bus_reader.query(since=<last_id>, role=<role>)`. Inject `recent_events` field into `cycle_input` dict before writing JSON. Also: call mechanical reaction handlers if configured.
  - `references/sub-skills/common/working-state.md` — **EXTEND**. Document new field: `- **Last Processed Event ID**: <id or "none">`. Used as cursor for `since=` parameter.
  - `references/sub-skills/common/cycle-runner.md` — **UPDATE**. Document `recent_events` field in `cycle-input.json` and how agents should interpret it during creative phase.
  - `references/scripts/event_bus.py` — **UNCHANGED** (Phase 2 emission module — read path is separate to keep emit/consume concerns isolated).
  
- **Behavior changes**:
  - `cycle_pre.py` gains a ~5–10ms HTTP GET at cycle start (local network, tiny payload). 
  - `cycle-input.json` gains an optional `recent_events` list (empty if bus unreachable or no new events).
  - Agents see a new field in their input — no behavioral change required (they already critically examine `cycle-input.json` per `cycle-runner.md` line 26).
  - Mechanical reactions (if enabled) execute status transitions without agent involvement.

- **Dependencies**: 
  - Phase 2 (#4709) MUST be shipped first — `GET /events` endpoint, `EventRecord` schema with `id` field (8-char SHA per CONTEXT doc), bounded deque.
  - No new Python packages. `urllib` (stdlib), `json` (stdlib).
  - `working-state.md` parser in `cycle_pre.py:_read_working_state()` (line 277) must be extended to parse `Last Processed Event ID` — ~3 lines.

---

## Side Effects

- **Risk 1: Agent stalls on slow harness GET /events**. If the harness is CPU-thrashed or the deque is being iterated under lock contention, `GET /events` could take >500ms. The agent's `cycle_pre.py` would block. — **Severity: L** — **Mitigation**: Use the same 500ms timeout pattern as `event_bus.emit()` (Phase 2 design). If timeout fires, return empty list and continue. The `recent_events` field is `[]` — agent sees no events this cycle, catches up next cycle. Harness deque is 1000 items max (~200KB) — filtering in-memory should be <5ms on any modern CPU.

- **Risk 2: `last_processed_event_id` cursor gets corrupted**. If `working-state.md` is hand-edited or the event ID format changes, the cursor could point to a non-existent event. — **Severity: L** — **Mitigation**: Harness `GET /events?since=<id>` returns all events AFTER that ID. If the ID is not found (e.g., it was evicted from the 1000-item deque), return all events from the oldest available. Agent treats the first event ID in the returned list as the new cursor. The agent doesn't need to validate the cursor — it's just a cursor; if it's stale, the agent processes more events than strictly "new."

- **Risk 3: `recent_events` bloats `cycle-input.json` context**. At 3.3 events/sec (10 agents at 1-min cycles), a 30-min cycle gap yields ~6000 events. With filtering by role and event_type, the relevant subset for a single agent is likely 10–30 events per cycle. At ~200 bytes each, that's 2–6KB added to `cycle-input.json` — negligible. But if no filtering, the full firehose would be 1.2MB. — **Severity: L** — **Mitigation**: Default to `role=<own_role>` filter. Agents can also filter to specific `event_type=` values. The bus reader defaults to returning the most recent 100 events if no `since` cursor is set (first cycle after upgrade).

- **Risk 4: Mechanical reaction fires on stale event**. If an agent's clone is behind on git pulls relative to events (e.g., bus references commit X that agent hasn't pulled yet), a mechanical reaction like "auto-merge PR" could attempt to merge a PR the agent can't see. — **Severity: M** — **Mitigation**: Mechanical reactions MUST verify local state before acting. The `pr-merge → auto-transition` handler must check that the PR number exists in the local git log before transitioning. Run `git log --oneline origin/main | grep "Merge pull request #N"` as a precondition. If not found, skip — the event will be re-consumed next cycle (the cursor won't advance for un-actionable events).

---

## Edge Cases

- **First cycle after Phase 4 upgrade (no cursor)**: `last_processed_event_id` is "none" in `working-state.md`. `event_bus_reader.query(since=None)` returns the most recent N events (default: 100, configurable). Agent sees a burst of past events. This is acceptable — the agent's creative phase can triage the firehose once. Subsequent cycles use cursor-based incremental reads.

- **Event ID evicted from deque before agent reads**: 1000-event deque at 20 events/cycle/agent × 4 agents = 80 events/30min = ~6 hours of history. Agent cycle interval is 30 minutes — cursor is always well within the window. Even at 1-min cycles, 1000 events ÷ ~80 events/min = ~12.5 minutes of history. If an agent is stalled for >12 min, the cursor is evicted and it gets the oldest available events. Acceptable — the agent catches up on what's still in the buffer.

- **Harness restart resets event stream**: On restart, the in-memory deque is empty. All agent cursors become stale (point to IDs that no longer exist). Next `GET /events?since=<id>` returns empty list or the oldest available (which is `[]`). Agent cursor resets naturally — `last_processed_event_id` advances to the first new event ID received. No manual intervention needed.

- **Agent with Phase 4 bus reader, harness without GET /events**: `event_bus_reader.py` POSTs to `/events` (or GETs if the endpoint is different). If harness is Phase 2 (POST-only, no GET), the GET returns 404. `event_bus_reader.query()` catches `urllib.error.HTTPError(404)` silently and returns `[]`. `cycle_pre.py` injects `"recent_events": []` into `cycle-input.json`. Agent operates with zero events — same as Phase 2 behavior. Graceful degradation.

- **Same event consumed twice across cycles**: If `cycle_pre.py` crashes after reading events but before writing `cycle-input.json` (or updating `working-state.md`), the cursor doesn't advance. Next cycle re-reads the same events. This is safe because: (a) mechanical reactions are idempotent (e.g., transitioning an issue that's already in the target status is a no-op via `tracker.py transition --force`), and (b) the creative agent seeing the same event twice can apply judgment. The cost is minor context waste, not incorrect behavior.

---

## Integration Risks

- **Phase 2 (#4709) not yet implemented**: Phase 4 research is forward-looking. All design assumptions depend on Phase 2's event schema (`id` field, bounded deque, `/events` POST endpoint). If Phase 2 implementation differs from its CONTEXT doc (e.g., event IDs use a different format, deque size changes), Phase 4 reader code must adapt. **Mitigation**: Phase 4 implementation should block on Phase 2 ship. The `event_bus_reader.py` module can be written against the Phase 2 test fixtures.

- **Phase 3 (#5613) boundary ambiguity**: The task brief asks "Should the read API be Phase 3 or part of Phase 4?" Phase 3 is described as "exposes events via web API for browsers." The `GET /events` endpoint for agent consumption uses the SAME endpoint shape as a browser-facing API. The difference is intent: Phase 3 is human-facing (rich UI, WebSocket push), Phase 4 is agent-facing (poll-based, filtered). **Recommendation**: `GET /events` with query params lives in Phase 4. Phase 3 adds WebSocket/SSE push and a browser UI that consumes the same endpoint. The endpoint is the API; the consumers differ. This avoids duplicating work.

- **Interaction with harness intent API**: `cycle_post.py` already queries `GET /agents/{role}` for intent (line 566 of cycle_post.py). Both the event reader and the intent check use the same harness port discovery. If the harness is down, both fail silently. Consistent behavior — no new failure mode.

- **Interaction with state bus (#3664)**: `working-state.md` is a state-branch file (per `state_bus.py:_STATE_FILES` line 157). The `last_processed_event_id` field written to `working-state.md` is committed to the state branch by `cycle_post.py` via `_state_commit()`. This means the cursor persists across agent restarts and context resets — exactly what we need.

- **Interaction with comms adapter (#3415)**: The task brief mentions future chat integrations becoming adapters on the bus. The CommsAdapter ABC (comms_adapter.py line 77) already defines `read_messages(channel, since, limit)` — this maps cleanly to `GET /events?since=<id>&limit=<n>`. The adapter pattern is ready; Phase 4 just needs to expose the bus as a read source that adapters can subscribe to.

---

## Upgrade & Migration

- **New config values**: None required. No new config.md fields. The feature is always-on for agents that have `event_bus_reader.py` deployed. Could add optional `event-consumption: enabled|disabled` flag if human wants to disable mechanical reactions without downgrading code, but YAGNI for now.

- **New files**: 
  - `references/scripts/event_bus_reader.py` — must be deployed to each agent clone's `references/scripts/` directory (same propagation as `event_bus.py` — git pull).
  - `references/sub-skills/common/event-bus-consumer.md` — NEW sub-skill. Documents how agents interpret `recent_events` in `cycle-input.json`. Included in dev agent manifest (after `cycle-runner`) and PM/QA/DM. Provides event type catalog and reaction guidance. ~40 lines of markdown.

- **Template changes**: `references/sub-skills/common/cycle-runner.md` gains a paragraph documenting `recent_events` field. `references/sub-skills/common/working-state.md` gains `- **Last Processed Event ID**: <id or "none">` field. The `cycle-runner.md` update is informational only — no new agent instructions required (agents already read `cycle-input.json` critically).

- **Upgrade steps**: Same 5-step deployment runbook as Phase 2 (PHASE2-AGENT-TRANSITION-RESEARCH.md lines 270–356):
  1. Deploy `event_bus_reader.py` to main repo (silent — not yet imported)
  2. Deploy updated `cycle_pre.py` with import + reader call + `recent_events` injection
  3. Wait one cycle for agents to pull
  4. Deploy updated `harness.py` with `GET /events` endpoint
  5. Next cycle → agents read events
  **Rollback**: Push revert commit removing import lines + restart old harness. Agents fall back to empty `recent_events` list. No work lost.

- **Graceful degradation**: 
  - Harness unreachable: `event_bus_reader.query()` returns `[]`. `recent_events` is empty. Agent operates on cycle-based polling (current behavior) — coordination is slower but works.
  - `event_bus_reader.py` missing: ImportError caught → fallback function that returns `[]`. Agent never sees events — same as Phase 2.
  - Mixed-version squad (some agents Phase 4, others Phase 2): Phase 4 agents see events from Phase 2 agents and react eagerly. Phase 2 agents don't read the bus at all — they're "patient." No breakage. The Phase 4 agent's mechanical reaction (e.g., auto-transition on `pr-merge`) still works because it reads the event from the shared bus, not from the other agent's state.
  - Harness down for extended period: Agent's cursor stays fixed. When harness returns, `GET /events?since=<old_id>` may get "cursor evicted." Reader falls back to most recent N events. Agent catches up.

---

## Open Questions

- **Q1**: Should mechanical reactions execute in `cycle_pre.py` (before agent creative phase) or in `cycle_post.py` (after agent has had a chance to react)? — **Why**: If in `cycle_pre.py`, mechanical reactions happen before the agent sees events — the agent never knows a transition occurred. If in `cycle_post.py`, the agent can override or augment the mechanical reaction during creative phase. **Recommendation**: `cycle_pre.py` for high-confidence patterns (pr-merge → auto-transition, verification-failed → rework context). Lower-confidence patterns (intent-transition stopping → stop commits) should surface to agent for judgment. The mechanical reaction module should be configurable per pattern with a `confidence` threshold.

- **Q2**: Should `last_processed_event_id` be per-event-type or a single cursor? — **Why**: A single cursor means events of all types share one sequential ID space. If agent A processes a `cycle-start` event but not a `pr-merge` event (different handler paths), advancing the cursor past the `pr-merge` would skip it. **Recommendation**: Single cursor, but only advance past the HIGHEST event ID that was fully processed (all handlers ran). If some handlers skip an event (condition not met), the cursor doesn't advance past that event. This means some events may be re-examined each cycle until their conditions are met or they age out — acceptable and safe.

- **Q3**: Should `event_bus_reader.py` be merged into `event_bus.py` as a bidirectional module? — **Why**: Separate files keep emit and consume concerns isolated, but a single `event_bus.py` with `emit()` and `query()` functions would be simpler to deploy and maintain. **Recommendation**: Keep separate. `event_bus.py` is fire-and-forget emission (Phase 2). `event_bus_reader.py` is cursor-based consumption (Phase 4). Different import sites, different error handling, different testing. If they share port discovery logic, extract that to a shared `_discover_harness_port()` in a common utility (or copy the parent-dir walking — it's 15 lines, duplication is acceptable).

- **Q4**: Should the read API use the same `GET /events` endpoint for both agent consumption and Phase 3 browser UI? — **Why**: Browsers need richer filtering (multiple roles, date ranges, pagination) and possibly WebSocket push. Agents need simple `since=<id>&role=<role>`. If we overload the same endpoint, browser complexity leaks into agent-path simplicity. **Recommendation**: Same endpoint, different query params. `GET /events?since=<id>&role=<role>&limit=50` serves agent needs. `GET /events?roles=pm,skill&event_types=pr-merge,cycle-end&since=<timestamp>&limit=200` serves browser needs. The harness handler reads query params and filters accordingly. If the endpoint grows too complex, split later — but Phase 2/4 scope is small enough to share.

- **Q5**: Should `recent_events` in `cycle-input.json` include the full event payload or just a summary? — **Why**: Full payloads consume agent context (token budget). Summaries reduce context pressure but may omit details the agent needs. **Recommendation**: Full payload for now. At 10–30 events per cycle × 200 bytes, total is 2–6KB — well under context pressure thresholds. If event volume grows, add a `summarize=true` query param in a future phase. The agent's creative phase can always use bash to re-query the bus for full details if needed.

---

## Recommendation

**Feasible.** The read side is architecturally simpler than the write side (Phase 2). Key design decisions:

1. **GET /events lives in Phase 4, not Phase 3.** The endpoint shape is the same; Phase 3 adds WebSocket and browser UI as consumers. Avoid duplicating the read API.
2. **Poll-based, not push.** Agents poll at cycle boundaries (every 30 min). Push (WebSocket/SSE) adds persistent connection complexity with marginal benefit at 30-min cycle intervals. If cycles drop to 1-min, revisit.
3. **Hybrid reaction pattern.** Mechanical for high-confidence, idempotent patterns (pr-merge → auto-transition, cycle-end pending-test → eager QA pickup). Surface everything else to agent via `recent_events` field. The agent's SOUL.md and creative judgment handle the rest.
4. **Self-event filtering by role.** `GET /events?role=<own_role>&exclude_self=true` (or filter client-side). The agent ignores events it emitted — this is the first line of loop defense.
5. **Cursor in working-state.md.** `Last Processed Event ID` field. Simple, already git-persisted via state branch, survives context resets.
6. **No mechanical reactions in v1 unless explicitly configured.** Start with surface-only (agent sees events, decides). Add mechanical reactions incrementally as patterns prove reliable.

The implementation is ~200 lines of Python total (event_bus_reader.py + cycle_pre.py changes + harness GET /events handler) plus ~60 lines of sub-skill documentation.

---

## Vault Candidates

- **Type**: decision — "Event read API (GET /events) belongs in Phase 4, not Phase 3 — same endpoint serves both agent and browser consumers, with Phase 3 adding WebSocket push" — **Why**: The Phase 3/4 boundary ambiguity is a recurring question. This decision prevents duplicating the read API and establishes that the event bus is a unified read/write protocol regardless of consumer type.

- **Type**: pattern — "Cursor-based incremental event consumption with working-state.md persistence" — **Why**: The `last_processed_event_id` cursor in `working-state.md` pattern is reusable for any future stream-based consumption (audit log replay, notification catch-up, cross-agent sync). It's minimal, git-persisted, survives restarts, and degrades gracefully when the cursor is evicted.

- **Type**: pattern — "Hybrid mechanical/intelligent reaction with confidence gating" — **Why**: The three-tier reaction model (mechanical auto-act, surface to agent, ignore) with per-pattern confidence thresholds is applicable to any event-driven automation system. It prevents the brittleness of purely mechanical systems while avoiding the latency of purely human/agent judgment.

- **Type**: learning — "Dual-module emit/consume split (event_bus.py + event_bus_reader.py) is preferred over a monolithic bidirectional bus module" — **Why**: The emit side is fire-and-forget with zero state; the consume side is cursor-based with persistence. Different import sites (cycle_pre for consume, cycle_pre+cycle_post+git_ops for emit), different error handling, different test fixtures. This separation of concerns at the module level, even though both talk to the same HTTP endpoint, is a design choice worth preserving.

- **Type**: learning — "Phase 2 must ship before Phase 4 can begin; forward-looking research against design docs is valid but must be re-validated against implementation" — **Why**: This research is written against Phase 2 CONTEXT.md and RESEARCH.md, not running code. The `EventRecord.id` field, bounded deque size, and `/events` POST endpoint shape are design commitments, not implemented facts. This "research-against-design" pattern is valid but carries re-validation risk.
```