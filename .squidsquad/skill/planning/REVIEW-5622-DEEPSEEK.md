Now I have a thorough understanding of the codebase. Let me compile the code review.

---

# 5622 Research — Peer Review: Event Bus Read Side (PR #5821)

## Summary

This is a **peer code review** of the Phase 4 event bus read-side implementation for PR #5821. **Critical finding: source files (`event_bus_reader.py`, updated `cycle_pre.py`, `test_event_bus_reader.py`) do not exist in the current working tree.** Only stale `.pyc` artifacts remain in `references/scripts/__pycache__/` — suggesting the feature branch was deployed/tested then the sources were reverted or lost. The review therefore examines the design against the existing codebase (which *is* available — `harness.py`, `event_bus.py`, `cycle_pre.py`, `cycle_post.py`, `tracker.py`) plus the locked decisions in `FEAT-PM-5622-CONTEXT.md`, DeepSeek second-opinion research, and test plan.

**Verdict: Feasible with 6 specific issues to address before merge.** The primary concerns are: (1) `get_since` cursor logic when an event ID is evicted from the 1000-item deque — the design says "return oldest available" but the current `GET /events` at `harness.py:820-824` has no `since` filtering at all, so this must be implemented correctly; (2) `tracker.py transition()` at line 837 lacks `--suppress-event`, meaning every mechanical-reaction-triggered transition emits a new event that could cascade; (3) the `_read_working_state()` parser at `cycle_pre.py:280-347` is fragile hardcoded pattern-matching and the new `Last Processed Event ID` field is the 6th hardcoded extension.

## Vault Context

- **BRIEFING.md priorities**: #4709 EPIC Harness Phase 2 is "IN FLIGHT pending-test PR #5673" — Phase 4 depends on Phase 2 shipping. #5622 is "planning, high."
- **Related decisions**: [[decision-pid-primary-liveness]] — "just use PID, it's more direct" applies to cursor authority: an agent-side cursor in `working-state.md` is more direct than harness-managed cursor, and crash-safe. [[decision-self-healing-sentinel]] — two-tier self-healing (unstick + file root-cause bug) applies to mechanical reactions: if a reaction fires incorrectly, the sentinel should catch it.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — event consumption in `cycle_pre.py`, not creative instructions. [[pattern-model-router-architecture]] — thin adapter (`event_bus_reader.py`) + thick filtering (`cycle_pre.py`).
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files" — mechanical reactions must verify local state before acting, not just trust bus events. "Systems should self-heal" — stale event handling must auto-recover.
- **Related learnings**: [[learning-atomic-migration-strategy]] — Phase 4 is additive; agents without `event_bus_reader.py` silently skip. [[learning-commit-code-state-exclusion]] — state files vs code files separation matters for cursor persistence.

## Impact Analysis

- **Files touched**: `references/scripts/event_bus_reader.py` (NEW), `references/scripts/harness.py` (EXTEND: `GET /events` filtering), `references/scripts/cycle_pre.py` (EXTEND: reader call, filtering, mechanical reactions, cursor injection), `references/sub-skills/common/working-state.md` (EXTEND: `Last Processed Event ID` field), `references/sub-skills/common/cycle-runner.md` (EXTEND: `recent_events` documentation), `references/installer-files.txt` (EXTEND per iter-707), `tests/test_event_bus.py` or new `tests/test_event_bus_reader.py` (tests).
- **Behavior changes**: `cycle_pre.py` gains ~5-50ms HTTP GET at start. `cycle-input.json` gains `recent_events` and `mechanical_reactions` fields. Mechanical reactions can advance tracker state without agent creative phase involvement.
- **Dependencies**: Phase 2 (#4709) `POST /events` must ship first. No new Python packages. `state_bus.py` must correctly handle the new `Last Processed Event ID` field in `working-state.md`.

## Side Effects

- **Risk 1: `tracker.py transition()` emits events without `--suppress-event` flag — cascade risk**. Every call to `tracker.py transition()` at line 986-1003 emits `task-start` or `task-end` events. If a mechanical reaction calls `transition()`, the resulting event re-enters the bus and could trigger another mechanical reaction. The `comment()` function (line 1054) already has `_suppress_event=False` parameter, but `transition()` (line 837) does not. — **Severity: H** — **Mitigation**: Add `_suppress_event=False` parameter to `transition()` matching the `comment()` pattern. Mechanical reactions pass `_suppress_event=True`. Until this is done, mechanical reactions should be limited to patterns that don't call `transition()` — or the reaction handler must guard against re-entry via event ID set-dedup. The test plan TC-23 acknowledges this risk but assumes `tracker.py` state machine prevents loops — this is true for terminal states but NOT for mid-pipeline transitions like `approved → in-progress` or `pending-test → rework`.

- **Risk 2: 500ms timeout is adequate for localhost but not for overloaded harness**. `event_bus.py` uses 500ms (`_TIMEOUT = 0.5` at line 25). This works for a healthy harness on localhost. However, if the harness is CPU-thrashed (e.g., 4 agents emitting concurrently + health polling every 5s + `save_state()` JSON serialization), the deque lock contention could push `GET /events` latency above 500ms. — **Severity: L** — **Mitigation**: The timeout is read-side only — `cycle_pre.py` falls back to `recent_events: []` on timeout. Agent catches up next cycle. Acceptable for now. Consider configurable timeout in a future phase.

- **Risk 3: Mechanical reaction false-positive on stale local state**. If an agent's clone is behind on git pulls and a `pr-merge` event arrives, a mechanical reaction could attempt to transition an issue that doesn't have the PR merged locally. The design (TC-14) requires local state verification, but the verifier must be robust. — **Severity: M** — **Mitigation**: The `pr-merge` reaction MUST verify `git log --oneline origin/main | grep "Merge pull request #N"` before transitioning. If the merge commit isn't in the local log yet, skip the reaction and do NOT advance the cursor past this event — it must be retried next cycle.

- **Risk 4: `working-state.md` cursor loses events on `cycle_pre.py` crash**. If `cycle_pre.py` reads events, advances the cursor in `working-state.md`, but then crashes before the agent's creative phase processes them, those events are permanently skipped. — **Severity: M** — **Mitigation**: The cursor should be advanced ONLY by `cycle_post.py` AFTER the creative phase completes successfully. `cycle_pre.py` should read the cursor, query events, inject them, but NOT update `working-state.md`. The cursor update happens in `cycle_post.py` only if the creative phase completed and `cycle-output.json` was valid. This is already the pattern described in the design (Q1 research, CQ-3), but the implementation must confirm this split.

## Edge Cases

- **Event ID evicted from deque (cursor points to non-existent event)**: The harness deque holds 1000 events (`EventStream.__init__`, line 348). If an agent stalls for >~6 hours (80 events/30min × 4 agents = ~160 events/hour, 1000/160 ≈ 6.25h), the cursor event is evicted. The `GET /events?since=<evicted_id>` must return events from the oldest available, not error. **Gap**: The current `harness.py:820-824` has NO `since` parameter — it only supports `limit`. The Phase 4 harness extension must implement `since` filtering with eviction handling: iterate the deque, find the index of `since` event, return everything after it, and if not found, return all events from position 0. The ordering is deque-insertion order, which is consistent under the lock.

- **Harness restart resets deque to empty**: All agent cursors become stale. `GET /events?since=<old_id>` returns `[]` (deque empty). Agent resets cursor to `"none"` on next write. This is correct per TC-21 — but the agent must handle "empty result with valid cursor" gracefully. If `[]` is returned and cursor is non-none, the agent should re-check: maybe the harness restarted. Log a diagnostic but don't crash.

- **Self-event consumption**: Agents emit events in `cycle_pre.py` (line 986-988) and `cycle_post.py` (line 671-677). On the NEXT cycle, the agent reads those same events back via the bus. If the agent's role filter includes its own event types, it will see its own past emissions. This is NOT a loop risk (the events are from the PAST cycle, different context), but it wastes token budget. **Mitigation**: Either exclude `role=<self>` events client-side in `_filter_events_for_role`, or accept the minor redundancy (the agent's own past events are contextually relevant for continuity).

- **`Last Processed Event ID` field missing from `working-state.md` template**: The current template at `working-state.md` (line 8-20) has `Task`, `Status`, `Started` but no `Last Processed Event ID`. Newly deployed agents will have the field absent. The parser at `_read_working_state()` (lines 280-347) returns `"none"` for unknown fields by default. This is correct per TC-16 — but the field should be documented in the template.

- **Event ID collision across harness restarts**: Event IDs are 8-char SHA256 prefixes generated from `timestamp + role + event_type + payload` (`event_bus.py:60-61`). Across harness restarts, duplicate event IDs are possible (same event content at same second). The cursor-based `since=<id>` logic MUST handle this: if multiple events share the same ID, `since=<id>` should return events strictly AFTER all occurrences, not just the first. The deque is linear — iterate to find the LAST occurrence of the `since` ID.

## Integration Risks

- **`_read_working_state()` parser fragility**: The parser at `cycle_pre.py:280-347` uses hardcoded prefix matching (`- **Task**:`, `- **Status**:`, `- **Phase**:`, `- **Quiet Cycles**:`). Adding `Last Processed Event ID` is the 5th hardcoded field (6th counting `Started` in the template). If the field format differs (e.g., `- **Last Processed Event ID**:` vs `- **Last Processed Event**:`), the parser silently returns `"none"`. **Recommendation**: Add the field to the parser, but also add an assertion in tests that verifies the field was parsed correctly when present. Better: extract a generic `**Key**: value` parser — but that's a separate improvement.

- **`harness.py` `GET /events` endpoint backward compatibility**: The current endpoint (`harness.py:820-824`) wraps results in `{"events": [...], "total": N}`. The Phase 4 `event_bus_reader.py` must unwrap this — it expects a list, not an object. If future code forgets to unwrap, `recent_events` will be an object instead of a list, breaking the agent's creative phase JSON parsing. **Must verify in tests** that the reader handles the `{"events": [...]}` wrapper correctly.

- **`state_bus.py` classification of `working-state.md`**: `working-state.md` is classified as a state-branch file (via `state_bus.is_state_file()`). The new `Last Processed Event ID` field is committed to the state branch by `cycle_post.py:_state_commit()` (line 410-412). This means the cursor survives agent restarts. **Verify**: `state_bus.is_state_file()` must still return `True` for the modified `working-state.md` format.

- **`installer-files.txt` must include new files**: Iter-707 notes `event_bus_reader.py` was added to installer manifest. Without it, fresh agent clones won't have the reader module. `cycle_pre.py`'s `try/except ImportError` guard prevents crashes, but agents silently run with `recent_events: []` forever.

- **Phase 2 is not yet shipped**: `harness.py:345-372` has `EventStream` and `POST /events` implemented, but Phase 2 (#4709) is still in `pending-test` per BRIEFING.md. Phase 4 cannot be validated against live traffic until Phase 2 lands.

## Upgrade & Migration

- **New config values**: `event-consumption: enabled|disabled` — **not yet implemented, YAGNI per research**. If mechanical reactions fire erroneously, there's no kill-switch except downgrading code.
- **New files**: `references/scripts/event_bus_reader.py` — must be in installer manifest. `references/sub-skills/common/event-bus-consumer.md` — planned but optional for v1.
- **Template changes**: `working-state.md` gains `- **Last Processed Event ID**: <id or "none">`. `cycle-runner.md` gains documentation of `recent_events` and `mechanical_reactions` fields.
- **Upgrade steps**: 5-step runbook (deploy reader → deploy cycle_pre → wait one cycle → deploy harness → agents read). Must verify that step 4 (deploy harness with `GET /events?since=`) doesn't break Phase 2 agents that are still on the old `cycle_pre.py`.
- **Graceful degradation**: Harness unreachable → `recent_events: []`. Reader missing → `ImportError` caught → `[]`. Mixed-version squad → Phase 4 agents read, Phase 2 agents don't. Harness restart → deque empty, cursors reset naturally.

## Open Questions

- **Q1**: Does the implementation advance the cursor in `cycle_pre.py` (before creative phase) or `cycle_post.py` (after)? — **Why**: If in `cycle_pre.py`, a crash during creative phase permanently skips events. The design (CQ-3 in test plan) says `cycle_post.py` updates the cursor, but the implementation must confirm this. The DeepSeek review flagged this as the #1 architectural concern.

- **Q2**: Is `--suppress-event` implemented in `tracker.py transition()`? — **Why**: Without it, mechanical reactions that call `transition()` emit new events that can trigger cascade reactions. The `comment()` function has this flag (line 1054), but `transition()` (line 837) does not. This is a prerequisite for enabling any mechanical reaction that touches tracker state.

- **Q3**: Does `GET /events?since=<id>` handle the case where `<id>` appears multiple times in the deque? — **Why**: Event IDs are 8-char SHA prefixes — collisions across harness restarts are possible. If `since=<id>` matches only the first occurrence, events between the first and second occurrence of that ID would be incorrectly returned.

- **Q4**: What is the default `limit` for `event_bus_reader.query()` and does it match harness default? — **Why**: Harness defaults to `limit=50` (`harness.py:821`). If reader defaults to a different value (e.g., 100 per CONTEXT doc line 59), mismatch could cause confusion. The first cycle (no cursor) should use `limit=100` to catch up; subsequent cycles should use a smaller `limit` since only incremental events are expected.

- **Q5**: Are `recent_events` and `mechanical_reactions` field names reserved/unique? — **Why**: If any role builder (e.g., `_build_pm_input`) already uses these field names, injecting them at `cycle_pre.py` line ~959 would clobber existing data. The current `cycle_input` dict at lines 959-967 has no such fields, but role-specific builders could theoretically collide.

## Recommendation

**Feasible with caveats — 6 issues must be addressed before merge:**

1. **CRITICAL**: Add `--suppress-event` / `_suppress_event` to `tracker.py transition()` (line 837) before enabling any mechanical reaction that calls it. Without this, every mechanical transition re-emits to the bus, creating cascade risk.

2. **IMPORTANT**: Implement `GET /events?since=<id>` with correct eviction handling in `harness.py`. The current endpoint (line 820-824) has no `since` parameter. Must iterate deque linearly, find the position of `since` event (last occurrence if duplicates exist), return everything after it, fall back to all events if not found.

3. **IMPORTANT**: Verify cursor advancement happens in `cycle_post.py`, NOT `cycle_pre.py`. If cursor advances before creative phase completion, a crash permanently loses events. The test plan (CQ-3) says `cycle_post.py`, but this must be confirmed in implementation.

4. **MEDIUM**: Mechanical reaction local-state verification must be robust. The `pr-merge → auto-transition` handler MUST check `git log` for the merge commit before acting. If verification fails, the cursor MUST NOT advance past the un-actionable event.

5. **LOW**: The `_read_working_state()` parser's hardcoded field matching is at its limits. Adding `Last Processed Event ID` as the 6th hardcoded field works but the parser should eventually become a generic `**Key**: value` extractor.

6. **LOW**: Restore or push the source files: `event_bus_reader.py`, `test_event_bus_reader.py`, and the modified `cycle_pre.py`. Only `.pyc` artifacts exist. Without sources, the PR cannot be reviewed or merged.

## Vault Candidates

- **Type**: learning — "`_read_working_state()` parser in `cycle_pre.py:280-347` uses hardcoded field prefix matching — fragile, now 6 fields. Generic KV extraction would make future fields zero-code." — **Why**: This pattern has been extended 4+ times. Documenting the fragility signals that the next extension should refactor to a generic approach.

- **Type**: pattern — "Event emission funnel bypass: any mechanical consumer of a shared event bus that calls shared funnels (`tracker.py transition()`) MUST have a `--suppress-event` flag to prevent re-emission cascades." — **Why**: This generalizes beyond Phase 4 — applies to any future bus consumer that both reads and writes through shared infrastructure.

- **Type**: decision — "Cursor advances in `cycle_post.py` (after creative phase completes), not in `cycle_pre.py` (before). Crash safety: if agent crashes during creative phase, cursor doesn't advance, events are re-read next cycle." — **Why**: This architectural detail is easy to get wrong and has permanent data-loss consequences. Worth preserving as a locked decision.

- **Type**: learning — "`event_bus._discover_port()` at lines 28-55 still uses parent-dir walking as fallback despite Phase 2 CONTEXT correction (lines 157-171) saying this doesn't work for sibling clone isolation. `event_bus_reader.py` should use the corrected approach (read own clone's `.harness-port` only)." — **Why**: Code debt discovered during Phase 4 design that should be cleaned up. The reader being a new module is the right time to fix this.

- **Type**: pattern — "Dual-module emit/consume split (`event_bus.py` + `event_bus_reader.py`) is correct. Emit is fire-and-forget with zero state; consume is cursor-based with persistence. Different import sites, different error handling, different timeout strategies." — **Why**: This design choice was debated in open questions (Q3) and the locked decision (Q3 in CONTEXT.md) confirms separation. Worth vaulting so future bus extensions follow the same pattern.