Here is the complete research document:

---

# FEAT-SKILL-5868-AC3-REVIEW Research — LLM derivation in compose.py: `derive_event_contract` + `derive_and_write_event_contracts`

## Summary

AC-3 of #5868 implements two functions in `references/scripts/compose.py`: `derive_event_contract()` (line 550) calls Claude CLI to derive `{emits, reacts_to}` from a role's composed instructions, and `derive_and_write_event_contracts()` (line 642) orchestrates derivation for all roles, writes results to `config.md` via `config.write_event_reactions()`, then runs cross-agent validation via `event_validator.validate_and_print()`. Both functions are integrated into `main()` under the `deploy` (line 1141) and `deploy-all` (line 1164) CLI commands.

**There is one blocking bug**: `derive_event_contract()` uses `subprocess` and `json` without importing them. The only imports of these modules are local to `agent_compose()` (lines 720–721), a different function scope. At runtime, `derive_event_contract()` will crash with `NameError: name 'subprocess' is not defined` at line 586. The `except` clause at line 635 also references the now-undefined names `json.JSONDecodeError` and `subprocess.TimeoutExpired`, causing a secondary `NameError` during exception matching. This makes the entire derivation pipeline non-functional. Fix: add `import subprocess` and `import json` to the module-level imports (after line 17), or add them as local imports inside `derive_event_contract()`.

Beyond the import bug, three design-level issues exist: (1) `derive_and_write_event_contracts()` does a **full replacement** of the `## Event Reactions` section — if only 2 of 4 roles succeed in derivation, the other 2 roles' contracts are silently deleted from `config.md`. (2) No idempotency guarantees — event type arrays are not normalized/sorted, the prompt doesn't instruct deterministic output, and there's no comparison against existing config. (3) Hallucinated event types are silently filtered out (lines 628–631) with no user-facing warning, making systemic LLM misunderstandings invisible.

## Vault Context

- **BRIEFING.md priorities**: #5868 "Event consumption sub-skill — compose-time config" is active high priority. #5856 and #5622 (event bus) are shipped dependencies. #5888 (compose skill) is shipped.
- **Related decisions**: [[decision-sub-skill-architecture]] — Composition is build-time concatenation. Event derivation happens at compose time, not runtime. [[decision-local-config-priority]] — `.squidsquad/config.md` is the authoritative config source; Event Reactions lives there per the locked decision.
- **Related patterns**: [[pattern-deterministic-scripts-over-prose]] — The validation (`event_validator.py`) is deterministic; the LLM derivation is the creative step that feeds it. The design follows the "LLM proposes, deterministic script validates" pattern.
- **Human preferences**: "Prefers direct/mechanical checks over indirect state files" — the three-tier catalog (`EMITTED`/`RECOGNIZED`/unknown) as ground truth for hallucination filtering is the right approach. "Never ship with failed TCs" — zero tests exist for these two functions. "Context pressure threshold: 70%" — the derivation prompt sends up to 8000 chars of instruction text, plus catalog data, which is well under Claude context limits.
- **Related learnings**: [[learning-atomic-migration-strategy]] — The derivation + validation + config writing + cycle_pre refactoring must all work together. A partial deployment where derivation writes contracts but validation doesn't run (or vice versa) would leave agents in an inconsistent state.

## Impact Analysis

- **Files touched**:
  - `references/scripts/compose.py` — lines 550–703 (the two new functions), lines 1141–1145 (`deploy` integration), lines 1164–1168 (`deploy-all` integration)
  - `references/scripts/config.py` — lines 276–312 (`write_event_reactions` called by derivation)
  - `references/scripts/event_catalog.py` — lines 26–77 (imported for valid event type lists)
  - `references/scripts/event_validator.py` — lines 174–192 (`validate_and_print` called after write)
  - `.squidsquad/config.md` — receives the `## Event Reactions` section (currently absent)
  - `tests/test_compose.py` — **zero test coverage** for these functions

- **Behavior changes**:
  1. Every `compose.py deploy <role>` now derives event contracts for ALL roles (not just the deployed one) and writes them to config.md, then runs cross-agent validation
  2. Every `compose.py deploy-all` does the same, plus passes the explicit roles list
  3. Config.md gains a `## Event Reactions` section with per-role `emits` and `reacts-to`
  4. Validation failures print WARNING but **do not block deployment** — the compose continues (lines 1143–1145)

- **Dependencies**:
  - `claude` CLI must be available on PATH (already always the case per CONTEXT.md lock: "Claude CLI is always available")
  - `event_catalog.py` — `EMITTED`, `RECOGNIZED` dicts
  - `config.py` — `write_event_reactions`
  - `event_validator.py` — `validate_and_print`
  - Uses `tempfile` (already imported at module level? No — imported locally in `compose_role()` line 358, but not needed by derivation functions)

## Side Effects

- **Risk 1: CRITICAL — Missing imports cause NameError at runtime** — Severity: **H** — `derive_event_contract()` uses `subprocess.run()` (line 586), `json.loads()` (line 612), `subprocess.TimeoutExpired` (line 635), and `json.JSONDecodeError` (line 635) without importing any of them. The only imports of `subprocess` and `json` are local to `agent_compose()` (lines 720–721), a separate function scope. At runtime, this produces `NameError: name 'subprocess' is not defined`, which is not caught by the `except` clause (since the except clause itself references undefined names). **Mitigation**: Add `import subprocess` and `import json` at module level (after line 17, alongside `import re`, `import sys`).

- **Risk 2: Full section replacement corrupts config on partial derivation** — Severity: **H** — `derive_and_write_event_contracts()` calls `config.write_event_reactions(contracts)` which does a full regex replace of the `## Event Reactions` section. If 2 of 4 roles fail derivation (line 678), only 2 are in `contracts`, and the other 2 are silently deleted from config.md. **Mitigation**: Either merge with existing contracts (read old section first, update only successfully-derived roles, keep the rest) or refuse to write if fewer contracts were derived than previously existed.

- **Risk 3: `deploy_role()` line 837 also uses `subprocess.run()` without module import** — Severity: **L** — The uncommitted-edits guard inside `deploy_role()` uses `subprocess.run()` at line 837. Since it's wrapped in `except Exception: pass`, the NameError is silently swallowed. The guard simply doesn't work. **Mitigation**: Same fix as Risk 1 — add `import subprocess` at module level.

- **Risk 4: Silent hallucination suppression masks systematic LLM errors** — Severity: **M** — Lines 628–631 silently drop any event types not in the catalog. If the LLM consistently invents or misnames event types (e.g., `pr-merges` vs `pr-merge`), the user gets no feedback that the LLM is hallucinating. The contract silently becomes empty or incomplete. **Mitigation**: Log a warning when event types are filtered out: `print(f"  WARNING: {role_name} derivation produced unknown event type '{e}', dropped", file=sys.stderr)`.

- **Risk 5: Validation runs even if no contracts derived — masks systemic failure** — Severity: **M** — `derive_and_write_event_contracts()` returns `True` (success) when `contracts` dict is empty (line 683: "No event contracts derived. Skipping validation."). If ALL roles fail derivation (e.g., Claude CLI is broken), compose proceeds with "WARNING: Event contract validation found errors" — which is misleading since no validation actually ran. **Mitigation**: Log a distinct message when zero contracts were derived vs. when validation found errors.

## Edge Cases

- **Text truncation at 8000 chars (line 583)**: `composed_text[:8000]` means large roles with extensive L3/L4 instructions lose their tail content. For a typical role with ~3000 lines of composed text (~100KB), this could cut off the entire project-specific L4 layer and variant-specific L3 layer. The LLM may miss critical event semantics buried in the truncated portion. **Handle by**: Either increase the limit, or better, reorder the composed text to put the most semantically rich content (role instructions, project sub-skills) first, or extract and prioritize headings/sections relevant to event behavior.

- **Claude returns valid JSON with extra/unexpected keys**: `contract.get("emits", [])` and `contract.get("reacts_to", [])` silently ignore unrecognized keys. This is correct and gated by the dict type check and list type checks. No issue.

- **Claude returns valid JSON but empty arrays**: `{"emits": [], "reacts_to": []}` is accepted and written to config.md. The validation will produce orphaned-emit warnings for the empty-emits situation. Acceptable.

- **Claude returns markdown-fenced JSON with leading/trailing text**: Lines 606–609 strip ``` fences, but only the outermost ones. If Claude outputs `Some text\n```json\n{...}\n```\nMore text`, the fence-stripping logic misses it — it only checks `clean.startswith("```")` and `clean.endswith("```")`. The subsequent `json.loads(clean)` would fail with JSONDecodeError. **Handle by**: Use a regex to extract the first JSON object: `re.search(r'\{.*\}', raw, re.DOTALL)`.

- **Role with no CLAUDE.md on disk (deploy-all with some failures)**: `derive_and_write_event_contracts()` at line 669 checks `claude_md.exists()` and skips. But as noted in Risk 2, skipping a role removes it from config.md. This happens silently.

- **Claude CLI timeout (60s)**: Caught by `subprocess.TimeoutExpired` in the except clause (once imports are fixed). Returns None. Caller prints warning and continues. Good.

- **Claude CLI not found on PATH**: Caught by `FileNotFoundError` in the except clause. Returns None. Good.

- **Config.md doesn't exist yet (first compose on fresh install)**: `config._read_config()` at config.py line 219 returns `""`, `_parse_sections` returns `{}`, `write_event_reactions` appends the section to end. The path `CONFIG_PATH` is `REPO_ROOT / ".squidsquad" / "config.md"` — if this directory doesn't exist, `tmp.write_text()` fails with `FileNotFoundError`. The error propagates to `derive_and_write_event_contracts`'s `except Exception` at line 690, which prints a warning and returns True. Graceful but silent.

## Integration Risks

- **Claude CLI output format flag**: The command uses `["claude", "-p", "--output-format", "text"]` (line 587). The `-p` flag means "print mode" (non-interactive). The `--output-format text` flag may not exist in all Claude CLI versions. If this flag is rejected, derivation fails. Current Claude Code (the SquidSquad runtime) does support this. No fallback if the flag changes.

- **Derivation runs for ALL roles on single-role deploy**: In `main()` line 1142, after `deploy_role(role_name)`, the code calls `derive_and_write_event_contracts()` **without arguments**, which discovers all deployed roles (line 656–659). This means deploying a single role re-derives contracts for ALL roles, calling Claude once per role. For a 4-role system with 60s timeout each, this could add 4 minutes to every single deploy. The CONTEXT.md lock says "LLM derivation runs on every compose" but the PHASE2-PREP.md recommended option C (first-time only during setup, validate-only thereafter). **Current implementation follows the "always derive" path, not the recommended option C.**

- **Validation runs but never blocks deployment**: Lines 1143–1145 print a WARNING when validation fails but do NOT `sys.exit(1)`. The compose succeeds even with validation errors. This contradicts TC-9's expected behavior ("compose exits non-zero OR human fix-loop prompt appears") and the fix loop design in PHASE2-PREP.md. The fix loop itself is not implemented — no interactive prompt exists.

- **No agent-compose gate**: The CONTEXT.md and PHASE2-PREP.md both contemplated gating derivation behind `agent-compose: yes`. The current implementation runs derivation unconditionally. Since `agent-compose: yes` is currently `no` (config.md line 87-88), but the derivation bypasses this gate entirely, it would run Claude on every deploy regardless — if the imports worked.

## Upgrade & Migration

- **New config values**: `## Event Reactions` section with `### role`, `- **emits**:`, `- **reacts-to**:` per role. Currently absent from `.squidsquad/config.md`. Populated by first compose that runs derivation.

- **New files**: None — all supporting files already exist (`event_catalog.py`, `event_validator.py`, `config.py` functions).

- **Template changes**: None — derivation reads CLAUDE.md (output), not source templates.

- **Upgrade steps**: N/A — no upgrade impact because:
  1. When `## Event Reactions` section is absent, `cycle_pre.py` falls back to hardcoded `_ROLE_EVENT_TYPES` (AC-5 already implemented this)
  2. First compose populates the section automatically
  3. Existing installs work without any action

- **Graceful degradation**: When derivation fails (all roles return None), `derive_and_write_event_contracts()` returns True — no contracts written, validation skipped, compose continues. `cycle_pre.py` falls back to hardcoded defaults. Zero behavioral change for agents.

## Open Questions

- **Q1**: Should derivation run on every compose or only when `agent-compose: yes`? — **Why**: The CONTEXT.md lock says "always derive," but PHASE2-PREP.md recommended option C (first-time only, validate thereafter). Current implementation follows "always derive" but this conflicts with the `agent-compose: yes` gate used by `agent_compose()` which currently defaults to `no`. If both derivation and `agent_compose()` are intended to run together, derivation should also respect the gate.

- **Q2**: Should `derive_and_write_event_contracts` merge with existing contracts or replace entirely? — **Why**: The current full-replace approach means any failed role derivation silently removes contracts for that role. If an operator runs `deploy skill` and the PM contract derivation fails for some reason, PM's contract is deleted from config.md. This is dangerous.

- **Q3**: Should the 8000-character truncation be dynamic (based on role size) or use a smarter content-extraction strategy? — **Why**: For roles with large L3/L4 content, truncation may systematically exclude the most role-specific event semantics (which live in L3/L4). A better approach might extract headings and key sections rather than raw truncation.

## Recommendation

**Needs rethinking — blocking bug must be fixed before this can function.** The critical missing-imports bug (`subprocess` and `json` undefined at runtime in `derive_event_contract()`) makes the entire derivation pipeline non-functional. Fixing this is a one-line change (add two imports at module level). Additionally, three design-level concerns should be addressed before shipping:

1. **Partial-output safety**: Switch from full-replace to merge semantics in `derive_and_write_event_contracts()` — read existing contracts first, only update successfully-derived roles, preserve the rest.
2. **Idempotency**: Add sorting/normalization of event type arrays before writing to config.md. Consider adding a "be deterministic — sort output, produce identical output for identical input" instruction to the prompt.
3. **Hallucination visibility**: Log a warning when event types are filtered out, so the user knows the LLM produced unknown types.

The integration with the deploy CLI commands is structurally correct — derivation runs after deploy, errors don't block the pipeline, and `cycle_pre.py`'s hardcoded fallback protects agents. However, the "always derive on every compose" behavior should be re-examined against PHASE2-PREP.md's recommended option C (derive once during setup, validate-only thereafter), especially given the 60-second-per-role Claude call cost on single-role deploys.

## Vault Candidates

- **Type**: learning — "Local imports in one function don't satisfy another function's needs" — **Why**: The `subprocess`/`json` import bug is a classic Python scoping mistake: imports in `agent_compose()`'s local scope don't make those names available to `derive_event_contract()`. This is worth preserving as a warning pattern for any future work where functions share dependencies but imports are scoped locally.

- **Type**: pattern — "LLM derivation + deterministic validation = safe config generation" — **Why**: The architecture of LLM-derives-contracts → writes-to-config → deterministic-validator-runs is a reusable pattern for any config that must be both context-aware (LLM) and correct (deterministic). The three-tier catalog provides ground truth. This pattern applies beyond events to any future LLM-derived structured config.

- **Type**: decision — "Derivation does full section replacement, not merge" — **Why**: The current design choice to fully replace the `## Event Reactions` section rather than merging has significant partial-output corruption risk. Whether this is ultimately kept or changed to merge semantics is a decision worth vaulting — it sets the precedent for how compose.py writes to config.md sections.

- **Type**: learning — "8K character truncation of composed instructions is fragile for event semantics" — **Why**: `composed_text[:8000]` assumes the most important event-relevant content is in the first 8000 characters. For roles with deep L3/L4 layers, the truncation may systematically exclude the content that most defines role-specific event behavior. A content-aware extraction strategy would be more robust.