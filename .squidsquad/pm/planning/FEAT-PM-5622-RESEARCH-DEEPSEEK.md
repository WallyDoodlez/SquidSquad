Now I have all the data I need. Let me compile the second-opinion analysis.

---

# FEAT-PM-5622 Research — Phase 4: Agent Communication Bus (Second Opinion)

## Summary

This is a second-opinion review of the existing [FEAT-PM-5622-RESEARCH.md](`.squidsquad/pm/planning/FEAT-PM-5622-RESEARCH.md`) against the live codebase. The Claude research is thorough on architecture and graceful degradation, but I found **9 gaps, 2 architectural discrepancies with locked decisions, and 4 integration risks** the research either misses or undersells. The core feasibility verdict stands — the read path is mechanically simpler than the write path. But two design issues demand attention before implementation: (1) the locked Q2 decision (harness-side cursor via `X-Consumer-Cursor` + `.harness-state.json`) conflicts with the Claude research's agent-side `working-state.md` cursor, requiring a re-design of persistence; (2) the `_read_working_state()` parser in `cycle_pre.py` (lines 277–345) is brittle — it hardcodes field names via pattern matching rather than parsing generically, so adding `Last Processed Event ID` requires a parser extension that's easy to get wrong.

**Primary risks**: (a) cursor state loss on harness restart (`.harness-state.json` is saved periodically, not per-event), (b) event ordering — Phase 2 provides no ordering guarantees across concurrent agent emitters, making cursor-based consumption unreliable if events arrive out-of-order, (c) tracker.py double-signaling when mechanical reactions trigger status transitions that themselves emit events.

## Vault Context

- **BRIEFING.md priorities**: #4709 Phase 2 is "in-flight pending-test PR #5673" and #5622 Phase 4 is "planning, high". Phase 4 cannot begin implementation until Phase 2 ships. Also relevant: #5613 "Phase 3+ event opportunities (pending, low)" — the Phase 3/4 boundary question is still open.
- **Related decisions**: [[decision-clone-isolation-architecture]] — agents in sibling clone directories means `.harness-port` distribution (not walking) is the correct discovery method. The Phase 2 CONTEXT doc (lines 157-171) explicitly CORRECTED away from parent-dir walking, but `event_bus.py:_discover_port()` (lines 41-55) still walks parent dirs as a fallback — this works but is technically the rejected approach. [[decision-cycle-runner-architecture]] — mechanical/creative split means all event consumption must happen in `cycle_pre.py`, not during creative phase. This limits reaction latency to one full cycle.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — event consumption belongs in deterministic scripts, not agent instructions. Same as Claude research noted.
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files — 'just use PID, it's more direct.'" This applies to event cursors: a harness-side cursor in `.harness-state.json` (Q2 locked decision) is more "direct" than agent-side `working-state.md` because the harness owns the event stream and can verify cursor validity. "Systems should self-heal" — mechanical reactions should auto-recover from stale events, not crash. "Context pressure threshold: 70%" — full event payloads in `cycle-input.json` must not push agents over threshold.
- **Related learnings**: [[learning-atomic-migration-strategy]] — Phase 4 is additive, like Phase 2. Agents without `event_bus_reader.py` silently skip.

## Impact Analysis

- **Files touched**:
  - `references/scripts/harness.py` — **EXTEND**: `GET /events` endpoint at line 820 already exists but needs query param filtering (`since`, `role`, `event_type`). Cursor tracking via `X-Consumer-Cursor` response header + `.harness-state.json` persistence (new fields per consumer).
  - `references/scripts/event_bus_reader.py` — **NEW**: ~80 lines. `query(since, role, event_types)` using `urllib`. Sends `X-Consumer-Cursor` header in request, reads updated cursor from response.
  - `references/scripts/cycle_pre.py` — **EXTEND**: Call `event_bus_reader.query()` after `_validate_config_version()` (~line 940), inject `recent_events` into `cycle_input` dict (~line 956). Extend `_read_working_state()` parser (lines 277–345) for any agent-side cursor field if needed. Add mechanical reaction calls.
  - `references/scripts/event_bus.py` — **UNCHANGED** (fire-and-forget emission, Phase 2).
  - `references/sub-skills/common/working-state.md` template — **POSSIBLY EXTEND** (only if cursor field lives in working-state; if harness-side per Q2, working-state is unchanged).
  - `references/sub-skills/common/cycle-runner.md` — **UPDATE**: Document `recent_events` field in `cycle-input.json`.
  - `tests/test_event_bus.py` — **EXTEND**: Add reader tests (analogous to existing emit tests, lines 57–125).
  - `tests/test_harness.py` — **EXTEND**: Add `GET /events` filtering tests (analogous to existing endpoint tests, lines 306–451).
  - `tests/test_cycle_pre.py` — **EXTEND**: Add tests for `recent_events` injection and working-state parser extension.

- **Behavior changes**:
  - `cycle_pre.py` gains ~5–50ms HTTP GET at cycle start (local network, filtered deque).
  - `cycle-input.json` gains a `recent_events` list field (empty if harness unreachable).
  - `GET /events` response gains `X-Consumer-Cursor` header with the next cursor value.
  - `.harness-state.json` gains per-consumer cursor fields if harness-side cursor (per Q2).

- **Dependencies**:
  - **Phase 2 (#4709) MUST ship first**. Event schema (`id`, `event_type`, `role`, `timestamp`, `cycle_number`, `payload`), bounded deque (maxlen=1000 at `harness.py:349`), `EventStream.get_recent()` (line 360). The `GET /events` endpoint stub already exists at line 820 but needs filtering logic.
  - No new Python packages needed. `urllib`, `json` (stdlib). `fastapi.Query` for query param parsing (already imported via FastAPI).
  - `state_bus.is_state_file()` (line 160) classifies `working-state.md` as a state-branch file — any new cursor field in `working-state.md` would auto-sync via existing state branch commit in `cycle_post.py:_state_commit()` (line 412).

## Side Effects

- **Risk 1: Cursor lost on harness restart before `.harness-state.json` save** — `.harness-state.json` is persisted in `update_health()` (5s poller, line 252) and on explicit intent changes. But event cursors would advance on every `GET /events` request (~every 30 min per agent). If harness crashes between a cursor update and the next `save_state()`, the cursor reverts to the last save. The agent would re-read events it already processed. — **Severity: M** — **Mitigation**: Save `.harness-state.json` on every cursor update (after `GET /events` response). The atomic write (`.tmp` → `replace`, line 306) is fast (~1ms) and won't block the event loop. Alternatively, use explicit acknowledge: agent sends `ack=<event_id>` in next request, harness advances cursor only on ack. The Claude research's `working-state.md` approach avoids this entirely — the cursor lives on the agent side and is committed atomically by `cycle_post.py`.

- **Risk 2: Event ordering is not guaranteed across agents** — Four agents emit concurrently to the same deque. `event_stream.append()` (line 354) is thread-safe (single lock), but the append order depends on thread scheduling, not real-time event ordering. Agent A's `cycle-start` might appear after Agent B's `cycle-end` even if A started first. A cursor-based `since=<id>` filter assumes total ordering; with concurrent emitters, events interleave unpredictably. — **Severity: M** — **Mitigation**: The harness serializes at append time (single lock), so de-facto ordering is by HTTP arrival time. This is consistent within a single deque but not necessarily causally accurate. For Phase 4, this is acceptable — agents treat all events as "happened since last cycle," not "happened in causal order." Document this limitation explicitly. A future phase could add Lamport clocks or causal IDs.

- **Risk 3: Tracker.py double-signaling from mechanical reactions** — If a mechanical reaction calls `tracker.py transition()` (e.g., `pending-ship → shipped` on `pr-merge`), that `transition()` call will emit a `status-transition` event (per Phase 2 CONTEXT, lines 46-53). That event enters the bus and could trigger ANOTHER mechanical reaction. — **Severity: H** — **Mitigation**: (a) Mechanical reactions MUST call `tracker.py transition()` with a `--suppress-event` flag (not yet implemented — new tracker.py feature needed). (b) Self-event filtering: the reacting agent's own events are ignored by its own reader. (c) Depth limiting: each event carries its causal chain depth; reactions don't fire beyond depth 2. The Claude research mentions "causal chain depth limiting" but doesn't flag that tracker.py needs the `--suppress-event` flag as a prerequisite.

- **Risk 4: `cycle_suppressed` events and event consumption gaps** — Phase 2 defines `cycle-suppressed` events (emitted instead of `cycle-start` when an agent is in planning phase). If an agent's cycle is suppressed, `cycle_pre.py` still runs (it always runs — the suppression is about creative phase, not mechanical). Wait — actually let me check. Looking at `cycle_pre.py` lines 973-985: it always runs, always writes `cycle-input.json`, always emits `cycle-start`. The `cycle-suppressed` event type is defined but not yet implemented in `cycle_pre.py`. This is actually a Phase 2 gap — it's in the CONTEXT but not in the code. For Phase 4, the key concern is: does `cycle_pre.py` always run? Yes — via `cycle-runner.md` line 9: `python references/scripts/cycle_pre.py [ROLE]`. So agents always read events at cycle boundaries regardless of suppression.

- **Risk 5: Full payload context pressure** — Locked decision Q5 says "full payload in cycle-input.json." At 16 event types × potential high volume, the `recent_events` list could grow. Claude estimated 2–6KB (10-30 events × 200 bytes). But extreme cases (agent stalls for hours, deque fills with 1000 events, no filtering) could produce ~200KB in `cycle-input.json`. The agent's context pressure (human threshold: 70%) doesn't directly measure JSON size, but large inputs increase token consumption. — **Severity: L** — **Mitigation**: Default `limit=100` in `event_bus_reader.query()`. The harness already defaults `limit=50` in `get_events()` (line 821). Add `role=` filter by default to only fetch events relevant to the requesting agent's role + cross-role events it cares about (e.g., skill cares about QA rejections). Document that `limit` is configurable.

## Edge Cases

- **First cycle after Phase 4 upgrade (no cursor)**: The Claude research says the reader returns "most recent N events." With harness-side cursor (Q2), the harness would receive `GET /events` with no `X-Consumer-Cursor` header, return the most recent N events, and set the cursor to the newest event ID in the response. Next request includes that cursor and gets only newer events. This works seamlessly.

- **Cursor evicted from deque**: The harness deque holds 1000 events. If agent cursor points to an event that's been evicted, `GET /events?since=<evicted_id>` returns events from the oldest available event. Agent cursor is reset. No crash — just a catch-up burst. Claude correctly identifies this.

- **Harness GET /events endpoint returns 404 for older harness**: The stub endpoint already exists at `harness.py:820`. If Phase 4 is deployed before harness update, the endpoint exists but lacks filtering. The reader would receive ALL recent events (up to `limit`), unfiltered. This is actually usable — just less efficient. If the harness is truly old (no GET /events at all), 404 → `[]`. Graceful degradation. Claude correctly identifies this.

- **Concurrent cursor updates**: Two agents read events simultaneously, both get the same cursor, both advance it. This is fine — each consumer has its own cursor. The locked Q2 decision (harness-side cursor) means the harness tracks `cursor_skill`, `cursor_pm`, etc. separately. No contention.

- **Cycle_post crash between event read and cursor save**: If `cycle_pre.py` reads events and writes them to `cycle-input.json`, but then the agent crashes before `cycle_post.py` runs, the cursor isn't advanced. Next cycle re-reads the same events. This is safe because: (a) mechanical reactions are idempotent (must be designed that way), and (b) the agent sees duplicate events and can handle them. The Claude research identifies this correctly but misses that with harness-side cursor, the cursor wouldn't advance at all until the next `GET /events` — so the agent MUST explicitly acknowledge via a separate endpoint or the cursor must advance on read (which is what happens with `GET /events` → cursor advances in response header, agent stores it, but if agent crashes, stored value is lost). **This is a real gap**: with harness-side cursors, the cursor advances on read, not on ack — meaning events could be permanently skipped if the agent crashes after reading but before acting.

## Integration Risks

- **Risk: Harness-side cursor (Q2) vs agent-side cursor tension**: The locked Q2 decision (harness manages cursor via `X-Consumer-Cursor` + `.harness-state.json`) conflicts with the Claude research's recommendation (cursor in `working-state.md`). The harness-side approach has two advantages: (a) cursor persistence is controlled by the harness, not distributed across agent clones, and (b) cursor validity can be checked against the deque. But it has one critical disadvantage: **the cursor advances on read, not on ack**, meaning if `cycle_pre.py` crashes after reading events but before the agent acts on them, those events are lost (cursor advanced, agent never saw them). The `working-state.md` approach is crash-safe because the cursor only advances when the agent explicitly writes it. **Recommendation**: Use the `working-state.md` approach for the cursor but have the harness also track it in `.harness-state.json` as a backup/recovery mechanism. Send `X-Consumer-Cursor` from agent to harness, but the agent advances its own cursor.

- **Risk: `_discover_port()` duplication**: `event_bus.py:_discover_port()` (lines 28-55) and `cycle_post.py:_discover_harness_port()` (lines 501-530) are near-identical copies of the same parent-dir walking + port-file reading logic. `event_bus_reader.py` would be a THIRD copy. — **Severity: L** — **Mitigation**: Extract `_discover_harness_port()` into a shared utility (or let the reader import from `event_bus` and refactor later). The Phase 2 CONTEXT (line 167) says "Read `.harness-port` from THIS clone's `.squidsquad/.harness-port`" — the parent-dir walk should be removed from `event_bus._discover_port()` per the corrected Phase 2 design.

- **Risk: `_read_working_state()` parser fragility**: The parser at `cycle_pre.py:277-345` iterates lines and matches hardcoded field patterns (`- **Task**:`, `- **Status**:`, `- **Phase**:`, `- **Quiet Cycles**:`). Adding `Last Processed Event ID` requires adding another hardcoded pattern. If the format changes, the parser silently returns `"none"` for unknown fields. — **Severity: L** — **Mitigation**: Add the field to the parser. But more importantly: if using harness-side cursor per Q2, `working-state.md` doesn't need this field at all — the harness tracks it. If using agent-side cursor (my recommendation), the field goes in `working-state.md` and the parser needs the extension. Either way, note this is the 5th hardcoded field in a parser that should eventually become a generic `**Key**: value` extractor.

- **Risk: Existing `GET /events` endpoint returns ALL events unfiltered**: At `harness.py:820-824`, the endpoint exists and returns `get_recent(limit)`. Phase 4 needs to ADD filtering without breaking Phase 2's endpoint contract. The endpoint isn't used by anything yet (Phase 2 only defines POST for agents), so this is safe — but the Phase 4 implementation should use query params (`since`, `role`, `event_type`) and fall back to unfiltered if none are provided (backward compat).

## Upgrade & Migration

- **New config values**: None required initially. Could add `event-consumption: enabled|disabled` flag for disabling mechanical reactions, but the Claude research correctly identifies this as YAGNI.
- **New files**: `references/scripts/event_bus_reader.py` (deployed to each agent clone via git pull, same as `event_bus.py`).
- **Template changes**: `cycle-runner.md` (line 20 area) gains documentation of `recent_events` field. `working-state.md` template MAY gain `Last Processed Event ID` field if agent-side cursor is used. No agent behavioral changes required — agents already critically examine `cycle-input.json` (per line 24).
- **Upgrade steps**: Same 5-step deployment runbook as Phase 2 (from PHASE2-AGENT-TRANSITION-RESEARCH.md). Critical: `event_bus_reader.py` must deploy BEFORE the harness update, because `cycle_pre.py` import is wrapped in `try/except ImportError`.
- **Graceful degradation**: Harness unreachable → `recent_events: []`. `event_bus_reader.py` missing → ImportError caught → empty list. Mixed-version squad → Phase 4 agents read bus, Phase 2 agents don't. Harness restart → deque empty, cursors stale, agents catch up on next cycle. Same as Claude research — verified against actual code.

## Open Questions

- **Q1**: Should the cursor advance on read (harness-side) or on explicit ack (agent-side)? — **Why**: Read-advance risks permanent event loss on agent crash. Ack-advance is crash-safe but requires the agent to persist the cursor before acknowledging. The locked Q2 decision says "single cursor managed by harness" — but the persistence semantics (read vs ack) are unresolved. If the cursor advances on read and the agent crashes before acting, those events are gone forever. **Recommendation**: Agent-side cursor in `working-state.md`, committed by `cycle_post.py` via state branch. Harness-side cursor as recovery-only (not authoritative). Send `X-Consumer-Cursor` header with the last processed event ID from `working-state.md` — harness uses it for filtering, not for state management.

- **Q2**: Does `tracker.py transition()` need a `--suppress-event` flag before Phase 4 can ship mechanical reactions? — **Why**: Without suppression, every mechanical-reaction-triggered transition emits a new event, which could trigger another reaction, creating cascades. The Claude research mentions "causal chain depth limiting" but doesn't flag that the event emission funnel needs a bypass valve. **Recommendation**: Add `--suppress-event` flag to `tracker.py transition()` as a Phase 4 prerequisite. Mechanical reactions pass this flag.

- **Q3**: What is the ordering contract of events in the deque? — **Why**: The cursor-based consumption model (`since=<id>`) assumes events have a total order. With 4 agents emitting concurrently, events interleave based on HTTP arrival time, not causal time. If Agent A's `task-start` arrives after Agent B's `task-end` for the same task (impossible causally but possible due to network), the ordering is misleading. **Recommendation**: Document that event ordering is "as received by harness," not "causal." Accept this limitation for Phase 4. Add a `harness_received_at` timestamp (harness-side, not agent-side) for diagnostics.

- **Q4**: Should `event_bus_reader.py` share port discovery with `event_bus.py` or duplicate it? — **Why**: Three modules (`event_bus.py:28-55`, `cycle_post.py:501-530`, future `event_bus_reader.py`) all need the same 15-line function. The Phase 2 CONTEXT says the original parent-dir walking approach was WRONG for clone isolation (lines 157-171) — but `event_bus.py` still uses it. The reader should use the simpler approach: read `.harness-port` from own clone + fallback to 7373. **Recommendation**: `event_bus_reader.py` uses the corrected approach (read own clone's `.harness-port`, no walking). Refactor `event_bus._discover_port()` separately (debt ticket, not Phase 4).

## Recommendation

**Feasible with caveats.** The read path is architecturally simpler than the write path and the Claude research correctly identifies most integration points. However, two pre-implementation actions are required:

1. **Resolve the cursor authority question (Q2 locked vs agent-side)**. My recommendation is agent-side cursor in `working-state.md` (crash-safe, git-persisted, survives harness restart) with harness-side cursor as recovery backup only. The locked Q2 decision ("harness manages cursor") needs a clarification: does it manage as authoritative (read-advance) or as recovery (ack-advance)?

2. **Add `--suppress-event` to `tracker.py transition()` before implementing mechanical reactions**. Without it, mechanical reactions create event cascades. This is a Phase 4 prerequisite that the Claude research missed.

The remaining risks are manageable with the mitigations described above. Total implementation: ~250 lines Python + ~40 lines sub-skill docs.

## Vault Candidates

- **Type**: decision — "Event cursor authority: agent-side (working-state.md, crash-safe) vs harness-side (.harness-state.json, centralized). Prefer agent-side for crash safety; harness tracks for recovery." — **Why**: This is a recurring architectural choice whenever a consumer reads from a central stream. The tradeoff (centralized simplicity vs distributed crash resilience) generalizes beyond this feature.

- **Type**: learning — "`_read_working_state()` parser is fragile — hardcoded field patterns. Adding fields requires parser code changes. Future: replace with generic key-value extraction." — **Why**: This parser has been extended 4 times (Task → Status → Phase → Quiet Cycles). Each extension added ~5 lines of hardcoded matching. A generically-parsed KV approach would make future fields (like `Last Processed Event ID`) zero-code changes. Good candidate for a follow-up improvement.

- **Type**: pattern — "Mechanical reaction double-signaling prevention: all mechanical reactions must bypass event emission when calling shared funnels like `tracker.py transition()`." — **Why**: This is a general rule for any system where mechanical scripts both consume and produce events through the same funnels. The `--suppress-event` flag pattern is reusable across all tracker interaction points.

- **Type**: learning — "`event_bus._discover_port()` still uses parent-dir walking despite Phase 2 CONTEXT correction saying this doesn't work for sibling clones. The harness's per-clone `.harness-port` distribution is the correct approach." — **Why**: The Phase 2 CONTEXT has a detailed correction (lines 157-171) explaining why parent-dir walking fails. But the code at `event_bus.py:41-55` still does it as a fallback. This code-debt should be cleaned up — and the reader should use the corrected approach from day one.

- **Type**: decision — "Event ordering in the bus is 'as received by harness,' not causal. Cursor-based consumption with `since=<id>` operates on this ordering. Document the limitation." — **Why**: This is a fundamental constraint of the event bus architecture. Consumers that assume causal ordering will see anomalies. This should be documented in the bus contract so future consumers don't build on a false assumption.