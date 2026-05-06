Now I have all the information needed. Let me compile the research document.

```markdown
# FEAT-PM-5856 Research — Status-Transition Events on Event Bus

## Summary
Tracker.py's `transition()` function (line 837) already contains event-bus emission code (lines 986–1003), but it only fires on two transitions: `→ in-progress` (`task-start`) and `→ pending-test` (`task-end`). These events use type names that don't match what agents filter for. The per-role event-type filter in `cycle_pre.py` (lines 377–383) expects `task-transition` — a type that nothing in the codebase actually emits. This means the existing event-bus code in `transition()` is **dead wire**: events are sent to the harness but silently dropped by every agent's filter.

The fix expands emission to cover **all 20+ legal status transitions**, unifies them under the `task-transition` event type that agents expect, and adds `task-transition` to harness.py's logging dispatch. The existing `task-start`/`task-end` emissions should be retired (they serve no purpose since agents don't read them). Backward compat is already handled by the try/except ImportError guard (lines 1002–1003).

**Primary risk**: Harness.py `_log_event()` (line 755) has no `task-transition` branch — it will fall through to empty detail, producing a terse but ugly log line. This is cosmetic only; the harness stores and serves events regardless of whether it has a pretty-print branch.

## Vault Context
- **BRIEFING.md priorities**: #5622 (Harness Phase 3, shipped) and #4709 (Harness Phase 2, shipped) — event bus bidirectional is live. #5613 "Phase 3+ event types (pending, low)" — this task is effectively Phase 3+ wiring for the most important signal.
- **Related decisions**: [[decision-cycle-runner-architecture]] — mechanical operations belong in scripts, not agent creative phase. This task extends mechanical emission in tracker.py, consistent with that architecture.
- **Related patterns**: (none directly, but the `_emit()` wrapper pattern in `git_ops.py` lines 84–101 shows the canonical fire-and-forget style with role auto-detection)
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files." Status-transition events are a direct mechanical signal — exactly the kind of ground-truth data the human values.
- **Related learnings**: [[learning-commit-code-state-exclusion]] — mechanical scripts are more reliable than agent-managed git state. This task adds mechanical emission to a script already trusted for deterministic operations.

## Impact Analysis
- **Files touched**:
  - `references/scripts/tracker.py` — expand event emission block (lines 986–1003), replace `task-start`/`task-end` with unified `task-transition` for all transitions
  - `references/scripts/harness.py` — add `task-transition` branch to `_log_event()` (after line 794)
- **Behavior changes**:
  1. **All** status transitions now emit `task-transition` events (currently only 2 do)
  2. Event type changes from `task-start`/`task-end` → `task-transition`, matching the filter in `cycle_pre.py` `_ROLE_EVENT_TYPES`
  3. Agents (PM, QA, skill, DM) will actually see status transitions in their `recent_events` for the first time
  4. Harness console gains `task-transition` log lines with detail like `#123: approved → in-progress`
- **Dependencies**: `event_bus.py` (already imported, line 988). No new dependencies. `harness.py` is a sibling consumer, not a dependency — it reads events passively.

## Side Effects
- **Risk 1: Event volume spike for PM agent** — Severity: M — Mitigation: PM runs many transitions per cycle (intake, verification, shipping). Each now emits an event. The `recent_events` field already has a `limit=100` cap (cycle_pre.py line 1037), and the per-role filter (line 1039) already selects for `task-transition`. No unbounded growth. PM's filter already includes `task-transition` — this just starts populating it.
- **Risk 2: `--force` transitions with no `--role`** — Severity: L — Mitigation: When `--force` is passed without `--role`, the `role` parameter is `None`. Current code at line 990 handles this: `emit_role = (role or "unknown").replace("-lead", "")`. The event will have `role: "unknown"` which is fine — agents filter by event_type, not emitter role. And `--force` is a human override used rarely.
- **Risk 3: Duplicate emissions** — Severity: L — Mitigation: Each `transition()` call still produces exactly one event. The existing `task-start` and `task-end` are being replaced, not supplemented. No double-fire.

## Edge Cases
- **Force-mode transitions (no role)**: `--force` bypasses authority check but `role` can be `None`. Current code handles this gracefully with `(role or "unknown")`. Event still emits — harness stores it, agents see `role: "unknown"`. Harmless.
- **Illegal transitions (rejected before emission)**: The legal check (line 853) happens before emission (line 986). If the transition is illegal, `sys.exit(1)` fires first. No event emitted — correct.
- **Blocked transitions (unread feedback, TC gate, unmerged PR)**: Similarly, these guards (lines 880, 898, 935) call `sys.exit(1)` before reaching the emission block. No event emitted for blocked transitions — correct.
- **event_bus import failure**: Already wrapped in try/except ImportError (line 1002). Silent no-op. Backward compat preserved.
- **Harness not running (no .harness-port)**: `event_bus.emit()` returns silently when port discovery fails (event_bus.py line 75–76). No error, no delay.
- **Forgejo/non-GitHub backends**: `transition()` calls `_get_forge_adapter()` for the label swap (line 966) but event emission is backend-agnostic (it's a local HTTP POST to harness). No impact.

## Integration Risks
- **`task-transition` missing from harness `_log_event()` dispatch**: The harness `_log_event()` function (harness.py line 755) has explicit branches for `task-start`, `task-end`, `task-transition` is absent. Events will still be stored and served via the `/events` endpoint — the dispatch is purely for console pretty-printing. Without a branch, detail will be empty string, producing a log line like `[12:34:56] pm     task-transition     `. This is a minor cosmetic gap. Fix: add `elif event_type == "task-transition": detail = f"#{payload.get('task_number','?')}: {payload.get('from_status','?')} → {payload.get('to_status','?')}"` after line 794.
- **`task-start`/`task-end` retirement**: These event types are in harness.py's dispatch (lines 791–794) and nowhere else. Removing emission from tracker.py means they stop flowing. This is safe — no agent filter includes them, so nothing is consuming them. The harness dispatch branches become dead code but are harmless to leave in place.
- **`cycle_pre.py` mechanical reactions**: The `_run_mechanical_reactions()` function (line 398) currently handles `pr-merge` and `verification-failed` only. `task-transition` events will pass through to `recent_events` but won't trigger mechanical reactions. This is correct — status transitions are informational, not actionable by a reaction. Agents interpret them during creative phase.

## Upgrade & Migration
- **New config values**: none
- **New files**: none
- **Template changes**: none — agent sub-skills already reference `recent_events` in their cycle-input.json reading instructions (cycle-runner.md line 22)
- **Upgrade steps**: N/A — no upgrade impact. The change is purely additive emission in an existing try/except block. Old agents that don't read events continue working; new agents that do read events start seeing status transitions.
- **Graceful degradation**: If event_bus is unavailable (ImportError), the try/except at line 1002 catches it. Transition still completes — status label is applied. The event is silently skipped. This is the same degradation pattern already in production for `task-start`/`task-end` and `tracker-comment` events.

## Open Questions
- **Q1**: Should `task-start` and `task-end` event types be completely removed from harness.py dispatch, or left as dead branches for potential future use? — **Why**: Leaving dead dispatch branches is harmless but adds clutter. Removing them is a separate cleanup. The harness will log `task-transition` with empty detail until the dispatch is updated — deciding scope boundary matters.
- **Q2**: Should the event payload include the `force` flag so agents know it was a human override? — **Why**: Agents might interpret a human-forced transition differently (e.g., skip re-checking authority). Currently `force` is not in the payload. Adding it would be a one-line change in the payload dict.
- **Q3**: Should `cycle_post.py` also emit `task-transition` events for the transitions it orchestrates (via `_do_status_transitions`, line 163)? — **Why**: `cycle_post.py` calls `tracker.py transition` which will now emit. No need for double emission. But worth confirming the call chain: cycle_post → tracker.py transition → event_bus.emit. One event per transition is correct.

## Recommendation
**Straightforward.** The scaffolding already exists — event_bus imported, try/except guard in place, role resolution handled. The work is two changes: (1) replace the two-transition `if/elif` block with a single unconditional `emit("task-transition", ...)` call that fires on every successful transition, and (2) add a `task-transition` branch to harness.py `_log_event()` for console visibility. No config, no templates, no upgrade.

## Vault Candidates
- **Type**: learning — `task-start`/`task-end` event types were dead wire since #5622 shipped — emitted but filtered out by all agents — **Why**: Classic integration gap — emission and consumption shipped in separate phases but event type naming wasn't reconciled. Worth recording so Phase 4+ event types (#5613) are validated end-to-end before shipping.
- **Type**: pattern — The `_emit()` wrapper in `git_ops.py` (line 84–101) is the canonical pattern for fire-and-forget emission with role auto-detection from sys.argv — **Why**: tracker.py currently duplicates the try/except/import pattern inline. If more scripts need event emission, centralizing in event_bus.py (or a shared helper) would reduce duplication. Flag for #5613 planning.
- **Type**: learning — `_ROLE_EVENT_TYPES` in `cycle_pre.py` defines the filter contract — any new event type must be added there to be consumed — **Why**: Future event-type additions (Phase 3+, #5613) risk the same dead-wire problem if the filter isn't updated simultaneously. Document as a paired-change requirement.
```