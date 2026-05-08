Now I have all the data I need. Let me compile the research document.

---

# FEAT-SKILL-5868-AC4-REVIEW Research — Cross-agent event contract validation in `event_validator.py`

## Summary

`references/scripts/event_validator.py` (245 lines) is a standalone, deterministic Python validator implementing four checks against the `## Event Reactions` section of `config.md`: hallucinated events (unknown tier → error), missing consumers (reacts-to with no emitter → error), orphaned emits (emit with no consumer → warning), and reaction cycles (bidirectional same-event emit+react → error). It reads the event catalog from `event_catalog.py` (three-tier: `EMITTED`, `RECOGNIZED`, unknown) and uses catalog descriptions (`get_description()`) to translate raw event names into process-gap language. **The validator is not yet integrated into `compose.py`** — no caller exists anywhere in the codebase. It is structurally sound but has three concrete correctness issues: (1) the hallucinated-events check exposes raw event names in its detail message, contradicting the docstring claim that raw names never appear in user-facing output; (2) the reaction-cycle check will produce false positives if any two roles both list `status-transition` in their `emits` and `reacts_to` (a realistic LLM-derivation scenario since `status-transition` is universal); and (3) the cycle check only detects same-event-type bidirectional cycles, not multi-event indirect cycles or self-cycles.

**Recommendation**: Feasible with caveats. The three issues above are fixable — none are structural blockers. The validator also needs integration into `compose.py` (zero callers exist) and test coverage (zero tests exist). The human-readable output quality is good for checks 2–4 (using catalog descriptions) but inconsistent for check 1.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill — compose-time config" is an active high priority (role:skill). #5856 "tracker.py status-transition events" shipped — directly relevant because `status-transition` is the event most likely to cause false-positive cycle detections.
- **Related decisions**: [[decision-sub-skill-architecture]] — validation must run at compose time, not runtime. The standalone validator aligns with this but still needs compose.py integration. [[decision-self-healing-sentinel]] — two-tier response (immediate fix, root-cause filing). The "fix loop" concept in the test plan references this, but event_validator itself only reports findings — the fix loop lives in compose.py (not yet implemented).
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — event_validator is a deterministic script, correctly implementing this pattern. No LLM involvement in validation.
- **Human preferences**: "Prefers direct/mechanical checks" — the set-intersection approach in all four checks is direct and mechanical. "Never ship with failed TCs" — zero tests exist for event_validator. "Context pressure threshold: 70%" — the validator output is compact but could be optimized further.
- **Related learnings**: [[learning-atomic-migration-strategy]] — event_validator must ship together with compose.py integration, config.md population, and cycle_pre.py refactoring. Standalone deployment would have zero effect (no callers).

## Impact Analysis

- **Files touched**:
  - `references/scripts/event_validator.py` — the validator itself (already exists, lines 1–248)
  - `references/scripts/event_catalog.py` — imported for tier validation and descriptions (already exists, lines 1–202)
  - `references/scripts/config.py` — `get_event_reactions()` imported for reading config section (already exists, lines 212–257)
  - `references/scripts/compose.py` — **NOT YET TOUCHED** — must call `event_validator.validate()` after each deploy
  - `tests/` — **NO TEST FILE EXISTS** for event_validator

- **Behavior changes**: None yet — zero callers. When integrated into compose.py, validation runs after every compose (single-role and deploy-all). Exit code 1 on errors blocks deployment (or enters fix loop per test plan TC-11).

- **Dependencies**:
  - `event_catalog.py` — `EMITTED`, `RECOGNIZED`, `get_tier()`, `get_description()`, `all_event_types()`
  - `config.py` — `get_event_reactions()`
  - Both are in the same directory, importable via `SCRIPT_DIR` path manipulation (line 32)

## Side Effects

- **Risk 1: Reaction cycle false positives from `status-transition`** — Severity: **H** — The cycle check (lines 136–166) flags any pair of roles where the same event type appears in both `emits_a & reacts_b` AND `emits_b & reacts_a`. If the LLM derivation (or manual config) assigns `status-transition` to every role's `emits` list (since all roles trigger status transitions via `tracker.py`), every pair of roles will produce a cycle error. `status-transition` is infrastructure-emitted by `tracker.py` (line 990), not role-emitted. **Mitigation**: Add a pre-filter to the cycle check that excludes events whose catalog source is a script (`EMITTED` events) from the `emits` side of the comparison. Alternatively, add a dedicated check that role `emits` lists must not include infrastructure-emitted events (a new validation rule).

- **Risk 2: Hallucinated-event detail exposes raw event names** — Severity: **M** — Lines 80 and 89 use `f"The event '{event_type}' is not in the event catalog"`, exposing the raw event type string. The docstring (line 15) claims "Raw event names do not appear in user-facing output." The other three checks correctly use `_describe()` which maps to catalog descriptions. **Mitigation**: Change the hallucinated check's detail to use a generic message like `"This event type is not recognized by the system"` without the raw name, or add a separate `_describe_or_raw()` helper.

- **Risk 3: No caller exists — validation is dead code** — Severity: **H** — `event_validator.py` is never imported or executed by any other file in the codebase (confirmed by grep of `compose.py`, `cycle_pre.py`, `wizard.py`, `add_role.py`). It can only be run manually via CLI (`python scripts/event_validator.py validate`). **Mitigation**: Must be integrated into `compose.py`'s `deploy_role()` or `deploy_all()` functions. This is AC-4's primary integration task.

- **Risk 4: Orphaned-emit check ignores infrastructure-emitted events** — Severity: **L** — Lines 116–133 only check role `emits` against role `reacts_to`. Infrastructure events from `EMITTED` (like `branch-checkout`, `pr-create`, `git-commit`) are never checked for orphan status, even though they could legitimately have no consumers. This is probably intentional (the check is about cross-agent role contracts), but diverges from what the docstring suggests ("role emits something nothing consumes"). **Mitigation**: Document the scope explicitly or add infrastructure-event orphan checking as a separate low-severity warning.

## Edge Cases

- **`status-transition` in role `emits` (LLM derivation):** If the LLM assigns `status-transition` to every role's `emits` list (because every role triggers status transitions), and every role also has it in `reacts_to`, the cycle check flags every role pair. This is the most likely false-positive scenario. The cycle check needs to distinguish "role emits" from "infrastructure emits on behalf of role."

- **Empty `Event Reactions` section or missing config.md:** `get_event_reactions()` returns `{}` → `validate()` returns `[], False` → no validation runs, no errors. This is correct for graceful degradation. However, the validator never warns that no contracts exist at all — it silently passes. The compose integration layer should handle this (warn/prompt for first-time population).

- **Role listed in Event Reactions that doesn't exist as an agent:** The validator iterates all roles in the parsed section without checking against actual `.squidsquad/<role>/` directories. A stale or deleted role's contract would still be validated, potentially producing misleading errors. **Mitigation**: Cross-reference against `config.get_agents()` or directory existence.

- **Indirect cycles (A→B via e1, B→C via e2, C→A via e3):** Not detected. The check only catches direct pairwise same-event cycles. This is a deliberate conservative scope — indirect cycles are exponentially harder to detect and might be legitimate workflows. The docstring should clarify this scope.

- **Self-cycle (role emits AND reacts to the same event):** Not detected because the pairwise loop only compares distinct roles (`roles[i+1:]`). A role reacting to its own emit could be intentional (different cycle) or a misconfiguration. Worth a warning, not an error.

- **Event in `RECOGNIZED` with reacts-to but no emitter:** Line 106: `if event_type not in all_emits and event_type not in RECOGNIZED`. Reacting to a `RECOGNIZED` (planned) event is explicitly allowed — no error. This is correct per the three-tier authority model. However, there's no informational message saying "this event is recognized but not yet emitted."

- **Malformed `Event Reactions` section:** The parser in `config.py` silently skips unrecognized lines (AC2 review confirmed this). The validator would see whatever partial data was parsed. No crash, but potentially incomplete validation. The graceful degradation is acceptable.

## Integration Risks

- **compose.py integration point:** The validator needs a call site in `compose.py`. Per the PM research (FEAT-PM-5868-RESEARCH.md line 33), it should be called from `deploy_role()` (line ~640). Since `deploy_role()` can be called for single-role deploys, validation must check the deploying role's contract against all other roles' contracts in config.md — not against their CLAUDE.md files. This is already how the validator works (reads from config.md section, not CLAUDE.md). The integration risk is that compose.py currently has no `Event Reactions` section population logic — if the section doesn't exist, validation silently passes (returns `[], False`). The integration must ensure the section is populated before validation runs.

- **Fix loop integration:** The test plan (TC-11) describes an interactive fix loop. The validator only reports findings — it doesn't implement the fix loop itself. The fix loop lives in compose.py and must consume `findings` list, present them to the human, and offer options. The validator's `Finding` objects have sufficient information (`severity`, `check`, `message`, `detail`) to drive this.

- **test_compose.py backward compatibility:** TC-20 requires existing compose tests to pass without modification. Since event_validator has no callers yet, this is automatically satisfied. When integration adds the call, the test environment may not have a populated Event Reactions section → validation returns `[]` → no impact.

- **test_cycle_pre.py backward compatibility:** TC-19 requires cycle_pre tests to pass. event_validator doesn't touch cycle_pre.py — no risk.

## Upgrade & Migration

- **New config values**: `## Event Reactions` section in config.md — currently absent from all config.md files. When absent, validation silently passes (returns `[], False`).

- **New files**: `references/scripts/event_validator.py` — already exists. `references/scripts/event_catalog.py` — already exists (used by validator). No new files needed for AC-4 itself beyond what already exists.

- **Template changes**: None. event_validator doesn't modify agent templates.

- **Upgrade steps**:
  1. Integrate `event_validator.validate()` call into `compose.py` deploy pipeline
  2. Ensure config.md has a populated `## Event Reactions` section before validation runs (compose populates it)
  3. On first compose after upgrade, validation runs against newly populated section
  4. Pre-upgrade state: no Event Reactions section → validation returns `[]` → no errors → zero behavior change

- **Graceful degradation**: When Event Reactions section is absent → `get_event_reactions()` returns `{}` → `validate()` returns `[], False` → validation passes silently. When event_catalog or config imports fail → the caller (compose.py) should catch and degrade. The validator itself has no try/except around imports — it will crash if `event_catalog` or `config` modules are missing.

## Open Questions

- **Q1**: Should the cycle check exclude infrastructure-emitted events (`EMITTED` tier) from the role `emits` side of the comparison? — **Why**: Without this exclusion, any LLM-derived config that puts `status-transition` in role `emits` lists will produce a cycle error for every role pair. Since `status-transition` is emitted by `tracker.py` (infrastructure), not by roles, roles listing it in their `emits` is already a configuration error — but one that should be caught by a separate, clearer check ("role claims to emit an infrastructure event") rather than buried in cycle detection noise.

- **Q2**: Should the validator check that all roles listed in Event Reactions correspond to actual deployed agents? — **Why**: Stale role entries from deleted agents would produce misleading validation errors. Cross-referencing against `config.get_agents()` or `.squidsquad/<role>/` directories would prevent this.

- **Q3**: Should the hallucinated-events check also use `_describe()` for consistency, even though unknown events have no catalog description? — **Why**: The docstring promises "Raw event names do not appear in user-facing output," but the hallucinated check breaks this promise. A generic message like "This event type is not recognized by the system" preserves the promise while still being actionable.

- **Q4**: Should the orphaned-emit check also cover infrastructure-emitted events? — **Why**: If `tracker.py` emits `branch-checkout` and no role reacts to it, is that a gap? The current check only covers role-contract emits. This may be intentional (cross-agent = role-to-role), but should be documented explicitly.

## Recommendation

**Feasible with caveats.** The validator's core logic is correct for all four checks. The three issues found are concrete and fixable:

1. **Must fix — false-positive risk**: Add a guard to the cycle check to exclude infrastructure-emitted events (those whose source is a script in `EMITTED`) from role `emits` comparison, or add a dedicated "role claims to emit infrastructure event" check. Without this, LLM-derived configs that assign `status-transition` to all roles' `emits` will produce a flood of cycle errors.

2. **Should fix — output contract**: Make the hallucinated-events check use catalog descriptions or generic language instead of raw event names, matching the docstring promise and the behavior of the other three checks.

3. **Must do — integration**: The validator has zero callers. It must be integrated into `compose.py`'s deploy pipeline.

4. **Must do — tests**: Zero test coverage exists. Tests for all four checks with mock reaction data are needed.

## Vault Candidates

- **Type**: pattern — "Three-tier event catalog as validation ground truth" — **Why**: `event_catalog.py` defines `EMITTED` (scripts), `RECOGNIZED` (planned), and unknown (error) tiers. This is the foundational pattern for the entire #5868 feature — it enables deterministic validation of LLM-derived contracts against hardcoded truth. Applicable to any future system where LLMs propose structured data that must be validated against code-level ground truth.

- **Type**: learning — "Cycle detection must exclude infrastructure-emitted events from role emit comparison" — **Why**: The `status-transition` false-positive risk is a specific instance of a general problem: when infrastructure (scripts) emits events on behalf of roles, those events should not be treated as role-emitted for cycle detection. This distinction between "emitted by role" and "emitted by script for role" is worth preserving as a design rule.

- **Type**: learning — "Standalone validators with zero callers are integration debt" — **Why**: `event_validator.py` is fully implemented but has no callers. The same is true for `write_event_reactions()` and `get_event_filters_for_role()` in `config.py` (per AC2 review). The pattern of implementing functions before their callers creates a risk that interfaces don't match when integration happens. All such functions should have at least one caller (even in tests) before being considered "done."

- **Type**: decision — "Validation output must use catalog descriptions, not raw event names, in all error messages" — **Why**: The docstring promise that "Raw event names do not appear in user-facing output" is partly broken (hallucinated check). This is a cross-cutting design rule for #5868 — the validation output is human-facing process-gap language. If this rule is inconsistently applied, it undermines the entire "process-gap" design goal. Worth vaulting so future validators uphold it uniformly.