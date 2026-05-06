Now I have all the data I need. Let me produce the research document.

---

# 5622 Research — Event Bus Read Side: Code Review (PR #5821, Feature Branch)

## Summary

This review covers the event bus read side implementation on the PR #5821 feature branch — `event_bus_reader.py`, `cycle_pre.py` integration, `cycle_post.py` cursor advancing, `harness.py` server-side filtering, and the full test suite. The previous review flagged a cursor-not-advancing bug; that is now fixed via `_advance_event_cursor()` at `cycle_post.py:604–668`, called from `main()` at line 724 after the working state update and commit.

**Overall recommendation: Feasible with one caveat.** The implementation is structurally sound with correct error handling, conservative mechanical reactions, and well-planned crash safety. One correctness issue exists in the server-side `EventStream.get_since()` truncation logic (see Risk 1 below). It is low-severity in practice given current event volumes but violates the cursor-based pagination contract. The fix is a one-line change.

**Primary risks**: (1) `get_since` drops events between cursor and the limit window boundary — in practice only manifests when an agent is offline for >5 cycles, but is a correctness issue. (2) The no-op replace block in `_advance_event_cursor` is dead code but harmless.

## Vault Context

- **BRIEFING.md priorities**: #5622 EPIC Harness Phase 4 — Agent communication bus (planning, high, role:skill). Also #4709 Phase 2 (event emission) is the foundation. Phase 4 builds directly on Phase 2's `/events` POST endpoint and `EventStream` deque.
- **Related decisions**: [[decision-cycle-runner-architecture]] — mechanical shell / agent core split justifies read in `cycle_pre.py` and cursor advance in `cycle_post.py`. [[decision-clone-isolation-architecture]] — port discovery via parent-dir walking is duplicated between `event_bus.py` and `event_bus_reader.py` (15-line duplication, accepted by research doc).
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — event consumption lives in mechanical scripts, not agent creative instructions. Agent sees pre-filtered `recent_events` in structured JSON.
- **Human preferences**: "Systems should self-heal: detect stuck states → unstick immediately" — mechanical reactions enable this. "Prefers direct/mechanical checks over indirect state files" — the event bus is the direct mechanism; the cursor in `working-state.md` is minimal persistence.
- **Related learnings**: [[learning-atomic-migration-strategy]] — Phase 4 is additive (like Phase 2). Agents without `event_bus_reader.py` silently skip; `recent_events` defaults to `[]`.

## Impact Analysis

- **Files touched**:
  - `references/scripts/event_bus_reader.py` — **NEW** (~90 lines). `query(since, role, event_type, limit)` function.
  - `references/scripts/cycle_pre.py` — **EXTENDED** (~40 lines). Lines 377–439: `_ROLE_EVENT_TYPES`, `_filter_events_for_role()`, `_run_mechanical_reactions()`. Lines 1032–1044: event bus read + filter + reactions injection.
  - `references/scripts/cycle_post.py` — **EXTENDED** (~65 lines). Lines 604–668: `_advance_event_cursor()`. Line 724: call site in `main()`.
  - `references/scripts/harness.py` — **EXTENDED**. Lines 365–377: `EventStream.get_since()`. Lines 808–868: `GET /events` endpoint with filtering. Line 824: `received_at` stamping.
  - `tests/test_event_bus_reader.py` — **NEW** (~192 lines). Tests for `_discover_port()`, `query()`, `EventStream.get_since()`.
  - `tests/test_event_bus.py` — **EXISTING** (unchanged, Phase 2 emission tests).
  - `references/sub-skills/common/working-state.md` — **EXTENDED**. Template now includes `- **Last Processed Event ID**: [8-char hex ID, or "none"]` (line 11).

- **Behavior changes**:
  - `cycle_pre.py` issues a ~5ms HTTP GET to harness at cycle start (500ms timeout safety net).
  - `cycle-input.json` gains `recent_events` (list, possibly empty) and `mechanical_reactions` (list, possibly empty).
  - `cycle_post.py` now reads `cycle-input.json` to advance the event cursor in `working-state.md` after successful creative phase.
  - Harness stamps `received_at` epoch on every POSTed event.
  - Harness serves `GET /events` with `since`, `role`, `event_type`, `limit` query params.

- **Dependencies**:
  - Phase 2 (#4709) — `event_bus.py` emission, `POST /events`, `EventStream` deque. Must be shipped first.
  - No new Python packages (stdlib only: `urllib`, `json`, `hashlib`, `re`).
  - `state_bus.py` — `working-state.md` is a state-branch file; cursor persists across restarts via `_state_commit()` in `cycle_post.py` (line 410–412).

## Side Effects

- **Risk 1: `get_since` truncation drops events between cursor and limit boundary** — `EventStream.get_since()` at `harness.py:374` uses `after[-limit:]` (last N events after cursor) rather than `after[:limit]` (first N events after cursor). If 200 events exist after the cursor and `limit=100`, events 101–200 (most recent) are returned but events 1–100 (closest to cursor) are silently dropped. The server-side `get_events` handler (line 854) compounds this: it calls `get_since(since, limit=limit*3)`, then applies `events[-limit:]` at line 866. So with `limit=100` from the client, the over-fetch gets 300 events, then the final truncation takes the last 100 — meaning events 201–300 after cursor are returned, events 1–200 are dropped. — **Severity: L** (in practice — event volume is <20 per cycle per agent, so `after` is nearly always smaller than `limit*3`) — **Mitigation**: Change `harness.py:374` from `after[-limit:]` to `after[:limit]` (return first N events after cursor). The `get_events` handler at line 866 would then use `events[:limit]` instead of `events[-limit:]` to preserve chronological order. Alternatively, remove truncation from `get_since` entirely (return all events after cursor) and let the `get_events` handler apply the single limit at line 866.

- **Risk 2: cursor lost if agent's `working_state_update` omits the cursor line and `_advance_event_cursor` fails** — If `_do_working_state_update` at `cycle_post.py:593` writes a new working-state.md that lacks `- **Last Processed Event ID**:`, then `_advance_event_cursor` adds it. But if `_advance_event_cursor` itself encounters an error (unlikely: file permissions, disk full, encoding issue), the cursor line is lost. On next cycle, `cycle_pre.py` reads `last_processed_event_id` as `None`, fetches recent events, and the agent re-processes. — **Severity: L** — **Mitigation**: This is self-healing — the agent catches up on the next cycle. The re-processing is safe (events are idempotent, mechanical reactions are idempotent).

- **Risk 3: agent modifies `cycle-input.json` during creative phase** — `_advance_event_cursor` reads `recent_events` from `cycle-input.json` (line 617). If the agent modifies `cycle-input.json` during its creative phase (which it shouldn't), the cursor could advance based on wrong data. — **Severity: L** — **Mitigation**: `cycle-input.json` is an input file — agents read it, they should not write to it. The `cycle-runner.md` sub-skill already documents that `cycle-input.json` is read-only during creative phase.

- **Risk 4: `_advance_event_cursor` no-op replace block is dead code** — Lines 648–652 in `cycle_post.py`: `content.replace("- **Status**:", "- **Status**:", 1)` is a self-replacement (no-op). The subsequent split-and-insert logic works correctly regardless. — **Severity: L** (no functional impact) — **Mitigation**: Remove the dead code block; keep only the split/insert logic from line 654 onward.

- **Risk 5: client doesn't pass `role`/`event_type` to server-side filtering** — `cycle_pre.py:1037` calls `_query_events(since=last_event_id, limit=100)` without `role` or `event_type` params. Server returns all events; client filters afterward. This is correct but inefficient — the server could filter before transmission, reducing payload size. — **Severity: L** (100 events × ~200 bytes = ~20KB — negligible) — **Mitigation**: Pass `role=role` to `query()` for a small optimization. Not required for correctness.

## Edge Cases

- **First cycle after upgrade (no cursor)**: `working-state.md` has `Last Processed Event ID: none` or the field is absent. `_read_working_state()` at `cycle_pre.py:309-312` parses `"none"` → `last_processed_event_id = None`. `query(since=None)` → harness returns most recent N events. Agent gets a one-time burst. Subsequent cycles use cursor-based incremental reads. **Handled correctly.**

- **Cursor ID evicted from deque**: If agent was offline long enough for its cursor ID to fall off the 1000-event deque, `get_since()` at `harness.py:376-377` falls back to returning the most recent events. Agent catches up on what's still in the buffer. **Handled correctly.**

- **Harness restart resets deque**: All cursors become stale (point to IDs in the old, now-empty deque). `get_since()` returns `[]` or recent events. Agent cursor resets naturally — `last_processed_event_id` advances to the first new event ID. **Handled correctly.**

- **Same event consumed twice (crash recovery)**: If agent crashes after `cycle_pre` reads events but before `cycle_post` advances cursor, the next cycle re-reads the same events. Mechanical reactions are idempotent (informational only — no state mutation). Creative agent applies judgment to duplicates. **Handled correctly.**

- **`_advance_event_cursor` with empty/recent_events**: Returns early at line 622-623 if `recent_events` is empty. Returns early at line 627-628 if last event has no `id`. **Handled correctly.**

- **`_advance_event_cursor` with missing working-state.md**: Returns early at line 632-633. **Handled correctly.**

- **`_advance_event_cursor` insertion when no `Status`/`Started` header lines**: Falls back to appending the cursor line at the end of the file (line 666). **Handled correctly**, though an empty working-state.md with just a cursor line is a degenerate case — acceptable.

- **Mixed-version squad (Phase 2 + Phase 4 agents)**: Phase 4 agents see events from Phase 2 agents. Phase 2 agents don't read the bus. No breakage — Phase 4 `cycle_pre.py` gracefully degrades to `recent_events: []` if reader or harness is unavailable. **Handled correctly** (verified in TC-20, TC-29, TC-30, TC-31).

## Integration Risks

- **`_advance_event_cursor` modifies working-state.md AFTER commit**: The cursor change to `working-state.md` is made at line 724, after `_do_commit_push` at line 712. This means the cursor update is NOT committed in the current cycle — it will only be committed in the NEXT cycle's state commit. If the agent process terminates between the cursor write and the next commit, the cursor change persists locally but is lost from git. However, the cursor value in `working-state.md` on disk is still correct for the next cycle's read. **This is acceptable** — the cursor is a local mechanical concern, not a cross-clone coordination mechanism.

- **Interaction with `_do_working_state_update` ordering**: `_do_working_state_update` (line 721) runs BEFORE `_advance_event_cursor` (line 724). If the agent provides a `working_state_update` that includes a `- **Last Processed Event ID**: old_value` line, `_advance_event_cursor` will overwrite it with the correct new value. The mechanical layer is authoritative for the cursor. **Correct ordering.**

- **`received_at` ordering vs. insertion ordering**: The harness stamps `received_at` at POST time (line 824) and appends to the deque under lock. Events are in insertion order, which matches arrival order. The `received_at` field could differ from insertion order if there's clock skew, but since all agents run on the same machine, this is not a practical concern. **Low risk.**

- **Phase 2 POST /events unchanged**: The `POST /events` endpoint (line 808) gains only the `received_at` stamp (line 824) — a one-line addition. No other changes to the emission path. **Low regression risk.**

## Upgrade & Migration

- **New config values**: None. The feature is always-on for agents that have `event_bus_reader.py` deployed. No `config.md` flags required per CONTEXT.md lines 46-51.

- **New files**:
  - `references/scripts/event_bus_reader.py` — new module
  - `tests/test_event_bus_reader.py` — new test file

- **Template changes**:
  - `references/sub-skills/common/working-state.md` — template now includes `- **Last Processed Event ID**: [8-char hex ID, or "none"]` (line 11 of the template).
  - `references/sub-skills/common/cycle-runner.md` — expected to gain documentation for `recent_events` field (per research doc line 36; not verified on this branch).

- **Upgrade steps** (5-step sequence from CONTEXT.md lines 46-51):
  1. Deploy `event_bus_reader.py` to main repo (silent — not yet imported)
  2. Deploy updated `cycle_pre.py` and `cycle_post.py` (ImportError catch ensures no crash if reader missing)
  3. Wait one cycle for agents to git pull
  4. Deploy updated `harness.py` with `GET /events` endpoint + `get_since` method
  5. Next cycle → agents read events

- **Graceful degradation**:
  - Harness unreachable: `query()` returns `[]` → `recent_events: []`. Agent continues normally.
  - `event_bus_reader.py` missing: `ImportError` caught at `cycle_pre.py:1040` → `recent_events: []`. Agent continues normally.
  - Harness restarts: Cursor becomes stale → `get_since` returns recent events → agent catches up.
  - Old harness (Phase 2, no GET /events): `query()` returns `[]` on 404 → agent continues normally.

## Open Questions

- **Q1**: Should `get_since` return `after[:limit]` (first N chronologically) or `after[-limit:]` (most recent N)? — **Why**: Current behavior returns most-recent-N, which drops events between the cursor and the limit window. The research doc (line 66) and test plan (TC-4) describe cursor-based pagination as "events strictly after that ID" — implying chronological order, not most-recent-only. If an agent is offline for many cycles, it should process events in order, not skip the oldest new ones. The practical impact is low (current event volume is small) but the semantic mismatch is real and should be resolved before the bus scales to more agents or shorter cycles.

- **Q2**: Should the `_advance_event_cursor` dead code (no-op replace, lines 648–652) be removed? — **Why**: It adds confusion without effect. A reader might wonder why `- **Status**:` is being replaced with itself. The split/insert logic below it handles insertion correctly; the no-op replace is a leftover from an earlier approach.

- **Q3**: Should `cycle_pre.py:1037` pass `role` to `query()` for server-side filtering? — **Why**: Currently the client fetches all events and filters locally. Passing `role=<own_role>` to the server would reduce HTTP payload size and leverage the server's `event_type` filter too. The over-fetch pattern (`limit * 3`) in the server is designed for exactly this purpose. The change is a one-line addition: `_query_events(since=last_event_id, role=role, limit=100)`.

## Recommendation

**Feasible with one caveat.** Fix the `get_since` truncation at `harness.py:374` (change `after[-limit:]` to `after[:limit]` and adjust `get_events` line 866 from `events[-limit:]` to `events[:limit]`). Then ship. The remaining issues are cosmetic (dead code removal, optional role-param optimization) and should not block merge.

## Vault Candidates

- **Type**: pattern — "Cursor-based incremental event consumption with working-state.md persistence" — **Why**: The `last_processed_event_id` cursor in `working-state.md` is a minimal, git-persisted, restart-surviving pattern for stream consumption. Reusable for audit log replay, notification catch-up, and cross-agent sync. Already flagged in the research doc but worth confirming after implementation review.

- **Type**: learning — "Crash-safe cursor advancement: advance AFTER creative phase, not before" — **Why**: `_advance_event_cursor` runs in `cycle_post.py` after the agent's creative phase completes. If the agent crashes mid-cycle, the cursor doesn't advance and events are re-read next cycle. This "process-then-advance" ordering is the correct pattern for any cursor-based consumption in an unreliable execution environment.

- **Type**: learning — "Test class that copies production logic can drift from the real implementation" — **Why**: `test_event_bus_reader.py:132-150` defines a `TestStream` class with `get_since` logic that duplicates `harness.py:EventStream.get_since` rather than importing it. Both contain the same `after[-limit:]` truncation pattern — meaning the test validates the same (potentially incorrect) behavior. When production code is fixed, the test must be updated separately. This dual-maintenance risk is worth documenting.

- **Type**: pattern — "Mechanical reactions as informational surface, not state mutation" — **Why**: The current `_run_mechanical_reactions` in `cycle_pre.py:398-439` only creates reaction entries for agent awareness — it does NOT mutate tracker state. This is a conservative design choice that prevents cascade loops. When future reactions mutate state (e.g., auto-transition), this pattern provides a safe baseline to measure against.

- **Type**: decision — "No per-role cursor — single cursor per agent" — **Why**: The research doc Q2 (line 122) considered per-event-type cursors vs. a single cursor. The implementation uses a single `Last Processed Event ID` field. This means events of all types share one cursor, and advancing past any event implicitly marks all prior events as processed. If an agent skips an event (irrelevant type), the cursor still advances past it — that event will not be re-offered. This is correct for the current architecture where per-role filtering happens before the agent sees events (filtered events are always relevant), but worth documenting as a design constraint if per-event-type cursors are ever needed.