# FEAT-SKILL-5868-AC1-REVIEW Research — event_catalog.py Three-Tier Event Model

## Summary

The proposed `event_catalog.py` for AC-1 of #5868 introduces a three-tier event catalog (emitted / recognized / unknown) as a single source of truth for all events in the SquidSquad event bus. **All 10 emitted event types are verified against actual `emit()` calls** across `git_ops.py`, `tracker.py`, `cycle_pre.py`, and `cycle_post.py`. The **recognized tier** is intended to capture event types present in `_ROLE_EVENT_TYPES` (cycle_pre.py line 377) that are not yet emitted — the actual count is **3, not 4** (verification-failed, verification-passed, agent-health). The task spec says "4 recognized" events; this mismatch is the primary gap to resolve.

**Primary risk**: The `event_catalog.py` file does not exist on disk — it was marked "completed" in working state but never committed (or was lost). Additionally, `pr-create` and `pr-merge` emit with `role: "unknown"` because `git_ops._emit()` (line 89–90) cannot auto-detect the emitting role from `sys.argv` for those commands, violating the schema contract where `role` should identify the emitter.

## Vault Context
- **BRIEFING.md priorities**: #5868 (high) — this is the feature being researched. #5613 "Phase 3+ event types" (low) — lists planned-but-not-emitted types relevant to the recognized tier.
- **Related decisions**: [[FEAT-PM-5622-CONTEXT]] — Q6 agent-side relevance filtering: `_ROLE_EVENT_TYPES` defines the filter contract. Any event type listed there must be emitted or it's dead wire.
- **Related patterns**: `git_ops._emit()` wrapper (lines 84–101) — canonical fire-and-forget with role auto-detection from `sys.argv`. tracker.py duplicates the try/except pattern inline (lines 988–995, 1063–1074).
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files" — event catalog is a mechanical truth source. "Never ship with failed TCs" — catalog must be verifiably correct.
- **Related learnings**: [[FEAT-PM-5856-RESEARCH]] — `task-start`/`task-end` were dead wire since #5622 shipped because emission and consumption shipped without reconciling type names. The catalog prevents this class of bug.

## Impact Analysis
- **Files touched**:
  - `references/scripts/event_catalog.py` (NEW — does not exist yet, must be created)
  - `references/scripts/cycle_pre.py` lines 377–383 — `_ROLE_EVENT_TYPES` must stay in sync with catalog
  - `references/scripts/harness.py` lines 744–800 — `_log_event()` dispatch coverage (11 types; `phase-change` has no emitter)
  - `references/scripts/git_ops.py` lines 84–101, 289, 342, 372 — role detection gap for `pr-create`/`pr-merge`
  - `references/scripts/tracker.py` lines 988–995, 1063–1074 — inline emit patterns
  - `references/scripts/cycle_post.py` line 742 — `cycle-end` emission
- **Behavior changes**: None for agents — catalog is read-only documentation in AC-1 scope. No runtime enforcement.
- **Dependencies**: `event_bus.py` (exists), `cycle_pre.py` (filter contract), `harness.py` (dispatch). No new deps.

## Side Effects
- **Risk 1: Catalog drifts from reality** — Severity: M — Mitigation: Paired-change requirement: any new `emit()` site must update the catalog. Consider a runtime test that introspects all `emit()` call sites via AST or regex and cross-references the catalog.
- **Risk 2: `_ROLE_EVENT_TYPES` and catalog recognized tier diverge** — Severity: M — Mitigation: Two sources of truth for "what events matter." A mismatch means either the catalog is wrong or agents miss expected events. The recognized tier should be either auto-derived from `_ROLE_EVENT_TYPES` or kept synchronized via a paired-change requirement.
- **Risk 3: `event_catalog.py` file missing** — Severity: H — Mitigation: The working state says AC-1 was completed, but no `event_catalog.py` exists anywhere on disk (`glob **/event_catalog*` returns zero matches). It may have been written to the `squidsquad/task/5868` feature branch but not committed, or was created in a cycle that didn't persist. Must be recreated.

## Edge Cases
- **`pr-create` and `pr-merge` role: `"unknown"`**: `git_ops._emit()` (line 94) checks only `args[1]` against known roles and line 96 checks only commit-like commands. Neither `"pr-create"` nor `"pr-merge"` are in those lists, so role stays `"unknown"` (line 90). Catalog must either document `"unknown"` as a valid emitting role or the emit sites need a `role` parameter passed explicitly.
- **Duplicate `git-push` from 3 call sites**: Emitted from `push()` (line 194), `commit_code()` (line 508), and `commit_state()` (line 579). Intentional (different branches, different payloads). Catalog should note multi-source emission.
- **`phase-change` dispatched but never emitted**: `harness._log_event()` (line 799) and `_update_agent_from_event()` (line 751) handle `phase-change`, but no script emits it. It was planned in CONTEXT.md 4709 but implementation was deferred. Should be in recognized tier or flagged as planned-not-emitted.
- **`status-transition` name confirmed**: Implementation uses `status-transition` (tracker.py line 990). QA results (FEAT-QA-5856-QA-RESULTS.md line 35) confirm this is canonical, replacing the old `task-transition` from the test plan. Catalog must use `status-transition`.
- **Cross-role visibility asymmetry**: 6 of 10 emitted types (`git-pull`, `git-push`, `git-commit`, `pr-create`, `branch-checkout`, `tracker-comment`) are in no role's `_ROLE_EVENT_TYPES` filter — they pass through harness but are invisible to agents. The catalog makes this visible for the first time.
- **Harness dispatch ≠ emission coverage**: `_log_event()` dispatches 11 types. 10 have emitters; `phase-change` does not. If a new type is emitted without a harness dispatch branch, console detail is empty string (cosmetic only — events still stored/served).

## Integration Risks
- **`event_bus_reader.query()` `event_type` filter** (line 64): The reader supports server-side filtering, but `cycle_pre.py` does client-side filtering via `_filter_events_for_role()` (line 386). If the catalog later enforces validation, the reader endpoint won't enforce it — potential inconsistency.
- **`_ROLE_EVENT_TYPES` silent filter**: Events not in any role's filter are invisible to agents. The catalog exposes this for the first time — agents may discover they can't see events they expect. Document clearly that the emitted tier includes harness-display events, not just agent-consumable ones.
- **tracker.py inline emit patterns** (lines 988–995, 1063–1074): Duplicate the `try/except ImportError` wrapper vs. the centralized `git_ops._emit()` pattern. If emission expands, this duplication is a maintenance risk.

## Upgrade & Migration
- **New config values**: none
- **New files**: `references/scripts/event_catalog.py` — the catalog module (MUST be created — currently missing)
- **Template changes**: none — catalog is mechanical-script-only
- **Upgrade steps**: N/A — no upgrade impact. Catalog is read-only import in AC-1. Rollback is deleting the file.
- **Graceful degradation**: If catalog import fails, nothing changes — no agent behavior depends on it in AC-1. If later ACs add validation, degradation must be silent no-op matching existing `try/except ImportError` pattern.

## Open Questions
- **Q1**: Is the recognized tier count 3 or 4? The task says "4 recognized" but only 3 event types in `_ROLE_EVENT_TYPES` are not emitted (verification-failed, verification-passed, agent-health). — **Why**: If the catalog states 4 and only 3 exist, it undermines its authority. Clarify whether `phase-change` (in harness dispatch but NOT in `_ROLE_EVENT_TYPES`) should be the 4th recognized event, or whether the AC spec needs adjusting to expect 3.
- **Q2**: Should `"unknown"` be a first-class emitting role in the catalog, or should `pr_create()`/`pr_merge()` be patched to pass `role` explicitly? — **Why**: Events with `role: "unknown"` are un-attributable. Agents filter by event_type, so it's cosmetic — but violates the schema contract.
- **Q3**: Should the recognized tier be auto-derived from `_ROLE_EVENT_TYPES` (import it and compute the union) or independently maintained? — **Why**: Derivation guarantees consistency but creates circular dependency (`event_catalog` → `cycle_pre`). Independent maintenance risks drift (the `task-start`/`task-end` bug pattern).
- **Q4**: Where does `phase-change` belong in the three-tier model? It has harness dispatch (harness.py lines 751, 799) but no emitter and is absent from `_ROLE_EVENT_TYPES`. — **Why**: If future harness-injected events appear with no catalog entry, they hit the "unknown" tier defined as an error, breaking fire-and-forget. The catalog needs a boundary for harness-reserved events.

## Recommendation

**Feasible with caveats.** The three-tier model is architecturally sound. However, three concrete issues must be resolved before AC-1 is complete:

1. **Create the file**: `event_catalog.py` does not exist on disk. It must be written and committed.
2. **Correct the recognized tier count**: 3 types (verification-failed, verification-passed, agent-health), not 4. Either add `phase-change` to `_ROLE_EVENT_TYPES` (making 4), or adjust the AC spec.
3. **Fix or document the `role: "unknown"` gap**: `pr-create` and `pr-merge` at git_ops.py lines 289, 342, 372 emit with `role: "unknown"`. Either pass `role` explicitly or document `"unknown"` as valid.

## Vault Candidates
- **Type**: learning — `_ROLE_EVENT_TYPES` + event catalog = dual-source-of-truth risk — **Why**: Two locations define which events matter. Future event type additions must update both. The `task-start`/`task-end` dead-wire bug (#5856) was caused by this exact dual-maintenance failure. Record as paired-change requirement.
- **Type**: pattern — `git_ops._emit()` wrapper (lines 84–101) as canonical fire-and-forget emission with role auto-detection — **Why**: tracker.py duplicates the pattern inline (lines 988–995, 1063–1074). If emission expands to more scripts, centralize this pattern in `event_bus.py`.
- **Type**: learning — 10 emitted / 3 recognized / 11 harness-dispatched = three views never reconciled before — **Why**: Adding an event type requires touching emit site + catalog + harness dispatch + `_ROLE_EVENT_TYPES`. Future maintainers need this checklist. The catalog is the first place all three views coexist.
- **Type**: learning — `phase-change` planned but never emitted (4709 context vs. reality) — **Why**: Research documents from #4709 (FEAT-PM-4709-CONTEXT.md, FEAT-PM-4709-RESEARCH.md) planned `phase-change` emission, harness dispatch was built, but emission was never wired. Catalog must flag planning-vs-reality gaps like this.
- **Type**: decision — `"unknown"` role handling policy — **Why**: Two emit sites produce un-attributable events. If the decision is to document this as valid, future scripts must know when `"unknown"` is acceptable vs. when an explicit role parameter is required.