---

# PR-5994-CODE-REVIEW Research — Event Consumption Sub-Skill (Compose-Time Reaction Config + Runtime Mechanical Execution)

## Summary

This review analyzes the proposed implementation for #5868 (PR #5994, branch `squidsquad/task/5868`). **The PR branch files are not present in the current working tree** — `event_catalog.py`, `event_validator.py`, config-driven filtering in `cycle_pre.py`, LLM derivation functions in `compose.py`, and config.md Event Reactions parsers in `config.py` are all absent from the repository root. This review therefore synthesizes findings from the skill agent's own AC reviews (AC1 through AC5 in `.squidsquad/skill/planning/`) cross-referenced against the existing codebase architecture, design decisions, and vault patterns.

**Primary risk: The implementation appears to contain a blocking bug (missing `subprocess`/`json` imports in `derive_event_contract()` in `compose.py` — AC3 review, Risk 1) that makes the entire LLM derivation pipeline non-functional.** Beyond the import fix, three design-level concerns exist: (1) full-section replacement in config.md on partial derivation, (2) no idempotency guarantees on event type arrays, and (3) silent hallucination suppression masking systematic LLM errors. The validator (`event_validator.py`) has three concrete correctness issues including a high-severity false-positive risk from `status-transition` cycle detection. The config-driven filter in `cycle_pre.py` (AC5) appears correctly implemented. **Zero test files exist** for `event_catalog.py`, `event_validator.py`, or the new `compose.py` derivation functions.

**Recommendation: Needs rethinking before merge.** Fix the import bug, address the three design concerns in derivation, fix the cycle-detection false-positive in the validator, and add test coverage for all new modules.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill" is active high priority (role:skill), listed as "QA verified, PR #5994 awaiting human review. Validator cycles downgraded to warnings." #5622 and #5856 (event bus emission + status-transition events) are SHIPPED dependencies.
- **Related decisions**: [[decision-sub-skill-architecture]] — Composition is build-time concatenation; event derivation at compose time, not runtime. [[decision-local-config-priority]] — `.squidsquad/config.md` is authoritative config source; Event Reactions section lives there.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — Validation via `event_validator.py` is deterministic; the "LLM proposes, deterministic script validates" pattern is correctly applied. The three-tier catalog (`EMITTED`/`RECOGNIZED`/unknown) as ground truth is architecturally sound.
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files" — three-tier catalog ground truth aligns with this. "Never ship with failed TCs" — **zero tests exist for any new module.** "Systems should self-heal" — the validator reports findings but the interactive fix loop is not implemented. "Context pressure threshold: 70%" — derivation sends up to 8000 chars of instruction text, which is safe.
- **Related learnings**: [[learning-atomic-migration-strategy]] — All ACs (catalog, config, cycle_pre, validation, sub-skill, derivation) must ship together; partial deployment would leave inconsistent state. [[learning-commit-code-state-exclusion]] — Config.md's Event Reactions section straddles code/state boundary; atomic write pattern must be preserved.

## Impact Analysis

- **Files touched** (per AC reviews of PR branch implementation):
  - `references/scripts/event_catalog.py` — **NEW** (three-tier event model: EMITTED, RECOGNIZED, unknown)
  - `references/scripts/event_validator.py` — **NEW** (deterministic cross-agent contract validation, 245 lines)
  - `references/scripts/config.py` — **EXTENDED** with `get_event_reactions()`, `get_event_filters_for_role()`, `write_event_reactions()` (per AC2/AC5 reviews)
  - `references/scripts/compose.py` — **EXTENDED** with `derive_event_contract()` (line ~550) and `derive_and_write_event_contracts()` (line ~642), integrated into `deploy` (line ~1141) and `deploy-all` (line ~1164) commands (per AC3 review)
  - `references/scripts/cycle_pre.py` — **MODIFIED** `_filter_events_for_role()` (line ~386) to try config-driven filters before hardcoded `_ROLE_EVENT_TYPES` fallback (per AC5 review)
  - `references/sub-skills/common/event-reactions.md` — **NEW** sub-skill (per working-state AC-6)
  - `.squidsquad/config.md` — receives new `## Event Reactions` section on first compose
  - `tests/` — **NO test files exist** for event_catalog, event_validator, or derivation functions

- **Behavior changes**:
  1. Every `compose.py deploy <role>` now derives event contracts via Claude CLI for ALL roles (not just deployed one), writes to config.md, runs cross-agent validation
  2. Every `compose.py deploy-all` does the same
  3. `cycle_pre.py` reads event filters from config.md when `## Event Reactions` section is present; hardcoded `_ROLE_EVENT_TYPES` is fallback
  4. Validation failures print WARNING but **do not block deployment** — compose continues (per AC3 line 1143-1145)
  5. When `## Event Reactions` is absent: **zero behavior change** — cycle_pre falls back to hardcoded dict exactly as before

- **Dependencies**:
  - `claude` CLI must be available on PATH (always true per CONTEXT.md lock)
  - `event_bus.py` and `event_bus_reader.py` (already shipped)
  - `config.py` existing `_read_config()`, `_parse_sections()` infrastructure
  - `tempfile` module (used by derivation functions)

## Side Effects

- **Risk 1: CRITICAL — `derive_event_contract()` has missing `subprocess`/`json` imports** — The only imports of `subprocess` and `json` in compose.py are local to `agent_compose()` at lines 565-566. `derive_event_contract()` uses `subprocess.run()` and `json.loads()` at its call sites but these names are undefined in its scope — `NameError: name 'subprocess' is not defined` at runtime. The `except` clause also references `json.JSONDecodeError` and `subprocess.TimeoutExpired`, which would trigger a secondary `NameError` during exception matching. **Fix**: Add `import subprocess` and `import json` at module level (after line 17, alongside `import re, import sys`). **Severity: H — blocking bug.**

- **Risk 2: CRITICAL — `derive_and_write_event_contracts()` does full replacement, not merge** — If 2 of 4 roles fail derivation, the other 2 roles' contracts are silently deleted from config.md. Partial-failure corruption risk is high. **Mitigation**: Read existing contracts first, update only successfully-derived roles, preserve the rest. **Severity: H.**

- **Risk 3: IMPORTANT — `status-transition` causes false-positive cycle errors in validator** — The cycle check (event_validator.py lines 136-166 per AC4) flags any pair of roles where the same event type appears in both `emits_a & reacts_b` AND `emits_b & reacts_a`. If LLM derivation assigns `status-transition` to every role's `emits` list (realistic — all roles trigger status transitions via `tracker.py`), every role pair produces a cycle error. `status-transition` is emitted by `tracker.py` (infrastructure, line 990), not by roles. **Mitigation**: Exclude infrastructure-emitted events (those whose source is a script in `EMITTED` tier) from role `emits` comparison in cycle detection. **Severity: H.**

- **Risk 4: IMPORTANT — Silent hallucination suppression masks systematic LLM errors** — Lines 628-631 of compose.py (per AC3) silently drop any event types not in the catalog. If the LLM consistently invents or misnames event types, contracts silently become empty/incomplete. **Mitigation**: Log a warning when event types are filtered out.

- **Risk 5: IMPORTANT — Validation runs even if no contracts derived, masks systemic failure** — `derive_and_write_event_contracts()` returns `True` (success) when `contracts` dict is empty. If ALL roles fail derivation (e.g., Claude CLI broken), compose proceeds with misleading "validation found errors" message when no validation actually ran.

- **Risk 6: MINOR — `deploy_role()` line 682 also uses `subprocess.run()` without module-level import** — The uncommitted-edits guard inside `deploy_role()` uses `subprocess.run()` at line 682. Since it's wrapped in `except Exception: pass`, the `NameError` is silently swallowed and the guard simply doesn't work. Same fix as Risk 1.

- **Risk 7: MINOR — 8000-character truncation may cut off L3/L4 event semantics** — `composed_text[:8000]` assumes the most event-relevant content is in the first 8K chars. For large roles with deep L3/L4 layers (variants, project-specific instructions), truncation may systematically exclude the content that most defines role-specific event behavior.

- **Risk 8: MINOR — `derive_and_write_event_contracts()` runs for ALL roles on single-role deploy** — Deploying one role re-derives contracts for all roles, calling Claude once per role. For a 4-role system with 60s timeout each, this adds ~4 minutes to every single deploy. PHASE2-PREP.md recommended option C (first-time only during setup, validate-only thereafter).

- **Risk 9: MINOR — No `agent-compose` gate on derivation** — Derivation runs unconditionally, bypassing the `agent-compose: yes` gate that `agent_compose()` respects. If `agent-compose` is `no` (as it currently is in config.md line 87), derivation still runs Claude on every deploy — if the imports worked.

## Edge Cases

- **Text truncation at 8000 chars (line 583)**: Assumes most event-relevant content is in first 8K. For roles with large L3/L4, truncation may exclude critical event semantics. **Mitigation**: Extract and prioritize headings/sections relevant to event behavior rather than raw truncation.
- **Claude returns markdown-fenced JSON with leading/trailing text**: Fence-stripping logic (lines 606-609) only checks outermost fences. If Claude outputs `Some text\n\`\`\`json\n{...}\n\`\`\`\nMore text`, stripping fails. **Mitigation**: Use regex to extract first JSON object: `re.search(r'\{.*\}', raw, re.DOTALL)`.
- **Claude returns valid JSON with extra/unexpected keys**: `contract.get("emits", [])` silently ignores unrecognized keys. Correct — gated by dict/list type checks.
- **Claude returns empty arrays**: `{"emits": [], "reacts_to": []}` is accepted and written. Validation will produce orphaned-emit warnings. Acceptable.
- **Role with no CLAUDE.md on disk**: `derive_and_write_event_contracts()` skips it. But with full-replace semantics, the missing role's contract is silently deleted from config.md.
- **Config.md doesn't exist yet (first compose)**: `write_event_reactions` appends to end. If `.squidsquad/` dir doesn't exist, `tmp.write_text()` fails with `FileNotFoundError`. Caught by `except Exception` → prints warning, returns True. Graceful but silent.
- **Empty `reacts_to` list in config**: `get_event_filters_for_role` returns `None` (config.py line 272-273), indistinguishable from "section absent". User cannot configure a role to receive NO events via config. Ambiguous design — may be intentional.
- **Self-event consumption**: Agent's own past-cycle events pass through `_filter_events_for_role` (different from `_run_mechanical_reactions`'s self-guard at line 413). Not a loop risk (different cycle), but wastes token budget.
- **Indirect cycles (A→B via e1, B→C via e2, C→A via e3)**: Not detected by validator. Deliberate conservative scope — indirect cycles are exponentially harder and may be legitimate workflows.
- **Self-cycle (role emits AND reacts to same event)**: Not detected because pairwise loop only compares distinct roles. Worth a warning, not an error.
- **`phase-change` in harness dispatch but never emitted**: Has no emitter and is absent from `_ROLE_EVENT_TYPES`. If a future harness-injected event has no catalog entry, it hits "unknown" tier defined as error. Catalog needs a boundary for harness-reserved events.
- **`pr-create`/`pr-merge` emit with `role: "unknown"`**: `git_ops._emit()` (line 94) cannot auto-detect role for those commands. Catalog must either document `"unknown"` as valid or emit sites need explicit `role` parameter.

## Integration Risks

- **Derivation runs unconditionally, bypassing `agent-compose: yes` gate**: `agent_compose()` respects the gate (line 561-562), but `derive_and_write_event_contracts()` does not. Since `agent-compose: yes` is currently `no` (config.md line 87), this means derivation would run Claude on every deploy — if the imports worked. The two features should share the same gate or have independent config flags.
- **Validation runs but never blocks deployment**: Lines 1143-1145 print WARNING but never `sys.exit(1)`. Compose succeeds even with validation errors. Contradicts TC-9's expected behavior. The fix loop is not implemented.
- **Validator has zero callers — integration debt**: Per AC4 review, `event_validator.py` exists on branch but is never imported or executed by any other file. Must be integrated into compose.py's deploy pipeline. Same for `write_event_reactions()` and `get_event_filters_for_role()` in config.py — functions implemented before their callers, risking interface mismatch.
- **`event_bus_reader.query()` supports `event_type` server-side filter but `cycle_pre.py` does client-side filtering**: If config-driven filters grow large, server-side filtering could reduce wire overhead. Not needed now, but future optimization path.
- **`_run_mechanical_reactions` still hardcoded with its own self-event guard (line 413)**: AC-5 only touched filtering, not reactions. The cascade safeguard is preserved. But reactions remain hardcoded — if new event types are added to config, they won't trigger mechanical reactions.
- **Dual-source-of-truth risk**: `_ROLE_EVENT_TYPES` (cycle_pre.py line 377) and config.md Event Reactions both define which events agents see. When config is populated, the hardcoded dict becomes dead code but must be kept as fallback. Future event type additions must update both or the derivation must always match.

## Upgrade & Migration

- **New config values**: `## Event Reactions` section with per-role `### <role>`, `- **emits**:`, `- **reacts-to**:`. Currently **absent** from `.squidsquad/config.md` (confirmed via grep). Populated by first compose that runs derivation.
- **New files**: `references/scripts/event_catalog.py` (NEW), `references/scripts/event_validator.py` (NEW), `references/sub-skills/common/event-reactions.md` (NEW per AC-6)
- **Template changes**: None — derivation reads CLAUDE.md (output), not source templates.
- **Upgrade steps**: N/A — no upgrade impact. When `## Event Reactions` section is absent: cycle_pre falls back to hardcoded `_ROLE_EVENT_TYPES` (existing behavior). First compose populates section automatically. Existing installs work without any action.
- **Graceful degradation**: When derivation fails (all roles return None): `derive_and_write_event_contracts()` returns True — no contracts written, validation skipped, compose continues. `cycle_pre.py` falls back to hardcoded defaults. When harness is unreachable: `event_bus_reader.query()` returns `[]` → no events to filter. When config.py import fails: falls back to hardcoded. All three degrade correctly.

## Open Questions

- **Q1**: Should derivation run on every compose or only when `agent-compose: yes`? — **Why**: CONTEXT.md says "always derive," but PHASE2-PREP.md recommended option C (first-time only, validate thereafter). Current implementation follows "always derive" but conflicts with `agent-compose: yes` gate used by `agent_compose()`. **Consequence**: If derivation always runs but `agent-compose` is `no`, Claude is called on every deploy while the coherence polish is skipped — inconsistency.

- **Q2**: Should `derive_and_write_event_contracts()` merge with existing contracts or replace entirely? — **Why**: Full-replace means any failed role derivation silently deletes existing contracts for that role. If operator runs `deploy skill` and PM contract derivation fails, PM's contract is deleted from config.md. **Consequence**: Partial-output corruption risk is high; merge semantics prevent data loss.

- **Q3**: Should empty `reacts_to` in config mean "no events" or "use hardcoded defaults"? — **Why**: Current implementation returns `None` for empty lists, triggering hardcoded fallback — indistinguishable from "section absent." If user explicitly writes `- **reacts-to**: ` (empty), they likely intend "no events." **Consequence**: Users cannot configure a role to opt out of all events via config.

- **Q4**: Should the cycle check exclude infrastructure-emitted events (`EMITTED` tier) from role `emits` comparison? — **Why**: Without this exclusion, any LLM-derived config that puts `status-transition` in role `emits` lists produces cycle errors for every role pair. Since `status-transition` is emitted by `tracker.py` (infrastructure), not by roles, roles listing it in `emits` is already a config error — but one that should be caught by a separate, clearer check rather than buried in cycle detection noise. **Consequence**: Flood of false-positive cycle errors makes validation output unusable.

## Recommendation

**Needs rethinking before merge.** The architecture (three-tier catalog → config-driven filters → deterministic validation → LLM derivation) is sound. The config-driven filter in cycle_pre.py (AC5) appears correctly implemented as a minimal, fallback-preserving change. However, several blocking and near-blocking issues must be addressed:

1. **CRITICAL — Fix the missing imports** in `derive_event_contract()` (add `import subprocess` and `import json` at module level in compose.py)
2. **CRITICAL — Switch to merge semantics** in `derive_and_write_event_contracts()` — read existing contracts, update only successfully-derived roles, preserve the rest
3. **CRITICAL — Fix cycle-detection false-positive** from `status-transition` in event_validator.py — exclude infrastructure-emitted events from role `emits` comparison
4. **IMPORTANT — Add hallucination visibility** — log warnings when event types are filtered out
5. **IMPORTANT — Implement the fix loop or make validation blocking** — currently validation warns but deployment proceeds; contradicts TC-9
6. **IMPORTANT — Add test coverage** — zero tests exist for event_catalog, event_validator, or derivation functions
7. **MINOR — Add idempotency** — sort/normalize event type arrays before writing to config.md; add "be deterministic" instruction to prompt
8. **MINOR — Re-examine "always derive on every compose"** against PHASE2-PREP.md's recommended option C, especially given 4-minute cost on single-role deploys

## Vault Candidates

- **Type**: learning — "Local imports in one function don't satisfy another function's needs" — **Why**: The `subprocess`/`json` import bug is a classic Python scoping mistake: imports in `agent_compose()`'s local scope (lines 565-566) don't make those names available to `derive_event_contract()`. Worth preserving as a warning pattern for any future work where functions share dependencies but imports are scoped locally.

- **Type**: pattern — "Three-tier event catalog as validation ground truth" — **Why**: `event_catalog.py` defines `EMITTED` (scripts), `RECOGNIZED` (planned), and unknown (error) tiers. This is the foundational pattern enabling deterministic validation of LLM-derived contracts against hardcoded truth. Applicable to any future system where LLMs propose structured data that must be validated against code-level ground truth.

- **Type**: learning — "Cycle detection must exclude infrastructure-emitted events from role emit comparison" — **Why**: The `status-transition` false-positive risk is a specific instance of a general problem: when infrastructure (scripts) emits events on behalf of roles, those events should not be treated as role-emitted for cycle detection. This distinction between "emitted by role" and "emitted by script for role" is worth preserving as a design rule.

- **Type**: learning — "Standalone validators with zero callers are integration debt" — **Why**: `event_validator.py` and `write_event_reactions()`/`get_event_filters_for_role()` in config.py are implemented but have no callers. The pattern of implementing functions before their callers creates a risk that interfaces don't match when integration happens. All such functions should have at least one caller (even in tests) before being considered "done."

- **Type**: learning — "`_ROLE_EVENT_TYPES` + config-driven filters = dual-source-of-truth risk" — **Why**: Both the hardcoded dict (cycle_pre.py line 377) and the config section define which events agents see. When config is populated, the hardcoded dict becomes dead code but is preserved as fallback. Future event type additions must update both, or the config population must always match. The `task-start`/`task-end` dead-wire bug (#5856) was caused by this exact dual-maintenance failure.