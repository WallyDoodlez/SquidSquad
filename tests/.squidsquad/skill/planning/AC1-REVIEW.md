Now I have a thorough understanding of the codebase. Let me compile the full analysis.

---

# FEAT-SKILL-5868-AC1-REVIEW Research — event_catalog.py Three-Tier Event Model

## Summary

The proposed `event_catalog.py` for AC-1 of #5868 introduces a three-tier event type catalog (emitted / recognized / unknown) as a single source of truth. Research confirmed that **all 10 emitted event types** match actual `emit()` calls across `git_ops.py`, `tracker.py`, `cycle_pre.py`, and `cycle_post.py`. The **recognized tier** correctly captures events in `_ROLE_EVENT_TYPES` that are not yet emitted, though the count is **3, not 4** (verification-failed, verification-passed, agent-health). The three-tier model aligns with CONTEXT.md locked decisions and the existing architecture of fire-and-forget emission + per-role filtering.

**Primary risk**: Several emit sites in `git_ops.py` cannot auto-detect the emitting role from `sys.argv`, resulting in `role: "unknown"` for `pr-create` and `pr-merge` events. The catalog must either accept `"unknown"` as a valid emitting role or the emit sites should be patched.

## Vault Context
- **BRIEFING.md priorities**: #5868 Event consumption sub-skill (pending, high) — this is the feature being researched. #5613 Phase 3+ event types (pending, low) — names several planned-but-not-emitted event types relevant to the recognized tier.
- **Related decisions**: [[FEAT-PM-5622-CONTEXT]] — Q6 agent-side relevance filtering: `_ROLE_EVENT_TYPES` in `cycle_pre.py` defines the filter contract. Any event type listed there must be populated (emitted) or it's dead wire. This is the correctness constraint on the recognized tier.
- **Related patterns**: `git_ops._emit()` wrapper pattern (lines 84–101) — canonical fire-and-forget with role auto-detection from `sys.argv`. The catalog should reference this as the standard emission pattern.
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files" — event catalog is exactly this: a single mechanical truth source, not a state file to be parsed.
- **Related learnings**: [[FEAT-PM-5856-RESEARCH]] — `task-start`/`task-end` event types were dead wire since #5622 shipped because emission and consumption shipped in separate phases without reconciling type names. The catalog prevents this class of bug by being the reconciliation point.

## Impact Analysis
- **Files touched**: 
  - `references/scripts/event_catalog.py` (NEW) — the catalog module itself
  - `references/scripts/event_bus.py` — optionally, could import catalog for validation
  - `references/scripts/cycle_pre.py` (line 377) — `_ROLE_EVENT_TYPES` must stay in sync with catalog's recognized tier
  - `references/scripts/harness.py` (lines 744–800) — `_log_event()` dispatch must cover all emitted types
  - `references/scripts/git_ops.py` (lines 289, 342, 372) — role detection gaps for pr-create and pr-merge
- **Behavior changes**: None for agents — catalog is read-only/import-only documentation. No runtime enforcement in AC-1 scope.
- **Dependencies**: `event_bus.py` (already exists), `cycle_pre.py` (for filter contract), `harness.py` (for dispatch). No new dependencies.

## Side Effects
- **Risk 1: Catalog drifts from reality** — Severity: M — Mitigation: The catalog MUST be maintained as a paired-change requirement with any new event type. If a dev adds an emit call without updating the catalog, the catalog lies. Consider adding a test that introspects all `emit()` call sites and cross-references the catalog.
- **Risk 2: `_ROLE_EVENT_TYPES` and catalog recognized tier diverge** — Severity: M — Mitigation: Both are sources of truth for "what events matter to agents." The catalog's recognized tier and `_ROLE_EVENT_TYPES` unique event types should be kept identical. A mismatch means either the catalog is wrong or agents won't see events they're expecting.
- **Risk 3: Role `"unknown"` leaks into catalog as a valid emitter** — Severity: L — Mitigation: `git_ops._emit()` falls back to `role="unknown"` (line 90) when it can't auto-detect from `sys.argv`. `pr_create()` (line 289) and `pr_merge()` (lines 342, 372) hit this fallback. Decision needed: document `"unknown"` as a valid emitting role in the catalog, or fix the emit sites to pass the role explicitly.

## Edge Cases
- **`pr-create` and `pr-merge` role detection failure**: `git_ops._emit()` at line 94 checks only `args[1]` against known roles and line 96 checks only commit-like commands for `args[0]`. Neither `"pr-create"` nor `"pr-merge"` are in those lists, so role stays `"unknown"`. Catalog should either document this as intentional or the emit sites need a `role` parameter.
- **Duplicate event type `git-push` from multiple call sites**: Emitted from `push()` (line 194), `commit_code()` (line 508), and `commit_state()` (line 579). This is intentional (branch push vs. working-branch push) and each carries different payload context (`branch` field). Catalog should note that `git-push` has multiple emission sources.
- **`phase-change` in harness dispatch but not emitted**: `harness._log_event()` (line 799) and `_update_agent_from_event()` (line 751) handle `phase-change`, but no script currently emits it. Should be in the recognized tier of the catalog as planned-not-emitted.
- **`status-transition` name vs test plan's `task-transition`**: The implementation uses `status-transition` (tracker.py line 990), while the original test plan (FEAT-PM-5856-TEST-PLAN.md) and QA at CQ-5 note `task-transition`. The QA results (FEAT-QA-5856-QA-RESULTS.md line 35) confirm `status-transition` is the canonical name. Catalog must use `status-transition`.
- **Cross-role visibility**: `_ROLE_EVENT_TYPES` defines per-role visibility, but the catalog's "emitted" tier is role-agnostic. A `git-commit` event is emitted regardless of who will consume it. The catalog's "recognized" tier implicitly ties events to roles via `_ROLE_EVENT_TYPES` but the catalog itself should document which roles care about which recognized events.
- **Harness-internal events**: CONTEXT.md (4709) reserves harness-internal events for Phase 3+. The catalog needs a fourth tier or a clear boundary: "reserved for harness internal" events (e.g., `health-check-result`, `intent-transition`). Currently these don't exist, but the catalog should leave a placeholder or the three-tier model must define where harness-injected events fit.

## Integration Risks
- **`_ROLE_EVENT_TYPES` as a silent filter**: Events emitted but not in any role's filter (e.g., `git-pull`, `git-push`, `git-commit`, `pr-create`, `branch-checkout`, `tracker-comment`) silently pass through the harness but are invisible to agents. The catalog makes this visible for the first time — agents may start asking "why can't I see git-pull events?" Document in catalog that the emitted tier includes events for harness display/telemetry, not necessarily for agent consumption.
- **`harness._log_event()` dispatch incomplete**: The harness pretty-prints 11 event types (cycle-start, cycle-end, git-commit, git-pull, git-push, pr-create, pr-merge, branch-checkout, status-transition, tracker-comment, phase-change). Of these, `phase-change` is not emitted. If a new emitted event type is added without a harness dispatch branch, the console shows an empty detail field. The catalog should cross-reference harness dispatch coverage.
- **`event_bus_reader.query()` `event_type` filter**: The reader supports server-side filtering by event_type (line 64), but `cycle_pre.py` does its own client-side filtering via `_filter_events_for_role()` (line 386). Potential inconsistency if the catalog introduces validation that the reader endpoint doesn't enforce.

## Upgrade & Migration
- **New config values**: none
- **New files**: `references/scripts/event_catalog.py` — the catalog module
- **Template changes**: none — catalog is mechanical-script-only
- **Upgrade steps**: N/A — no upgrade impact. Catalog is a new import with no runtime enforcement in AC-1. Rollback is simply deleting the file.
- **Graceful degradation**: If catalog import fails, nothing changes — no agent behavior depends on it in AC-1. If later ACs add validation (e.g., `event_bus.emit()` checks catalog before emitting), degradation must be silent no-op (matching the existing `try/except ImportError` pattern).

## Open Questions
- **Q1**: Should the catalog's "recognized" tier be automatically derivable from `_ROLE_EVENT_TYPES` (import it and compute the union), or maintained independently? — **Why**: Derivation guarantees consistency but creates a circular dependency (`event_catalog` → `cycle_pre`). Independent maintenance risks drift. The current `_ROLE_EVENT_TYPES` has 7 unique types; 3 are planned-not-emitted.
- **Q2**: Is the recognized tier count 3 or 4? The task description says "4 recognized events" but only 3 event types in `_ROLE_EVENT_TYPES` are not currently emitted (verification-failed, verification-passed, agent-health). — **Why**: If the catalog states 4 and only 3 exist, it undermines the catalog's authority as a source of truth. Clarify whether `phase-change` (planned in CONTEXT.md 4709 but absent from `_ROLE_EVENT_TYPES`) should be the 4th.
- **Q3**: Should `"unknown"` be a first-class emitting role in the catalog, or should the `pr-create`/`pr-merge` emit sites be fixed to pass role explicitly? — **Why**: Events with `role: "unknown"` pollute the event stream with un-attributable entries. Agents filter by event_type, not role, so this is cosmetic — but it violates the schema contract where `role` should identify the emitter.
- **Q4**: Does the catalog need a "reserved" tier for harness-internal events (per CONTEXT.md 4709: "The harness MAY inject its own events"), or do those fall under "recognized"? — **Why**: If harness-internal events appear in the stream with no catalog entry, they'd hit the "unknown" tier which is defined as an error. This breaks the fire-and-forget contract.

## Recommendation

**Feasible with caveats.** The three-tier model is correct and the 10 emitted events are verified. However, there are two concrete issues to resolve before AC-1 is complete:

1. **Correct the recognized tier count**: Only 3 event types (verification-failed, verification-passed, agent-health) are in `_ROLE_EVENT_TYPES` but not yet emitted — not 4. Either add `phase-change` to `_ROLE_EVENT_TYPES` (making it 4), or adjust the AC spec to expect 3.
2. **Fix or document the `role: "unknown"` gap**: `pr-create` and `pr-merge` events (git_ops.py lines 289, 342, 372) emit with `role: "unknown"` because `_emit()` cannot auto-detect the role from `sys.argv` for those commands. Either pass `role` explicitly (requires adding a `role` parameter to `pr_create()` and `pr_merge()`) or document `"unknown"` as a valid emitting role in the catalog.

## Vault Candidates
- **Type**: learning — `_ROLE_EVENT_TYPES` + event catalog = dual-source-of-truth risk — **Why**: Two locations define which events matter (catalog + filter dict). Any future event type addition must update both. Worth recording as a paired-change requirement so Phase 3+ events (#5613) don't repeat the `task-start`/`task-end` dead-wire bug.
- **Type**: pattern — `git_ops._emit()` wrapper (lines 84–101) as canonical fire-and-forget emission with role auto-detection — **Why**: tracker.py duplicates the try/except/import pattern inline (lines 988–995, 1063–1074). If event emission expands to more scripts, this pattern should be centralized rather than copy-pasted.
- **Type**: learning — 10 emitted / 3 recognized / 11 harness-dispatched = three views of the same event stream, each with different coverage — **Why**: The harness dispatch, agent filter, and emission sites have never been reconciled in one place. The catalog is the first attempt. Future maintainers need to know that adding an event type requires touching multiple files (emit site + catalog + harness dispatch + `_ROLE_EVENT_TYPES`).