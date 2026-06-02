# BUG: PRD-A (compose link stage) — DS audit findings

**Source**: DeepSeek code review of landed PRD-A stories (A1–A6, A2.6, A2a–A2f, A3, A4, A4.5, A5) vs spec.
**PRD spec**: `docs/prd/compose-link-stage.md`
**Audit doc**: `.squidsquad/pm/planning/AUDIT-PRD-A-DS-REVIEW.md`
**Verdict**: PARTIAL — 1 ERROR + 4 WARNINGS

## ERROR — Aliases registry parser format mismatch (blocks all v2 deploys)

- **File**: `references/scripts/config.py:371` vs `.squidsquad/config.md:14-19`
- **Severity**: error
- **Issue**: `parse_aliases_registry()` expects a 3-column markdown table (`| alias | role-class | L3 domain |`). The live `config.md` on this repo still uses the legacy bullet-list format (`- **skill**: skill`). Result: `deploy <alias> --v2` and `deploy-all --v2` abort on every real install with `"section is present but contains no table"` before any link-stage work. **SC1 and SC2 are effectively untestable end-to-end against the living install.**
- **Stories implicated**: A2f (#10492), A5 (#10385), A6 (#10386)
- **Suggested fix**: choose one — (a) bullet-list fallback in `parse_aliases_registry`, (b) one-shot in-place migration on first v2 invocation, or (c) installer update writes the table format + ships a migration step.

## WARNING 1 — Wrong column header in A2f test fixture

- **File**: `tests/test_compose_a2f_10492.py:60`
- **Severity**: warning
- **Issue**: `_stage_minimal_install` writes `| Alias | Role class | L3 domain |` (space in "Role class"). `config.py:377` does strict lowercase comparison against `"role-class"` (hyphen). The test passes only because it bypasses the parser via a pre-built `registry` dict. Any code that mirrors this fixture (installer template, doc example) will fail real parsing.
- **Stories implicated**: A2f (#10492)
- **Suggested fix**: change line 60 to `"| alias | role-class | L3 domain |\n"` (canonical column names). Add an integration test that actually parses the `config.md` written by `_stage_minimal_install` through `parse_aliases_registry`.

## WARNING 2 — `qa` role-class missing from ALIASES_ROLE_CLASSES

- **File**: `references/scripts/config.py:297`
- **Severity**: warning
- **Issue**: `ALIASES_ROLE_CLASSES = frozenset({"pm", "worker", "verifier", "dm"})` — no `"qa"`. Live `config.md:19` has `- **qa**: qa`. Compose elsewhere carries #6274 dual-aware shim (`_BASE_ALIAS_6274`, `_list_known_role_identities`, `_resolve_variant`) that accepts `qa ↔ verifier`. The v2 parser does NOT participate in that shim, so v2 rejects valid v1 aliases.
- **Stories implicated**: A5 (#10385)
- **Suggested fix**: add `"qa"` to `ALIASES_ROLE_CLASSES`, OR add a normalization step in `parse_aliases_registry` that maps `qa → verifier` (and `dev → worker`) before validation, mirroring `_BASE_ALIAS_6274`.

## WARNING 3 — A4 §9a coexistence claim wrong (no v2 drift check delivered)

- **File**: `references/scripts/compose.py:2069-2076`
- **Severity**: warning
- **Issue**: PRD §9a says A4's v2 sibling `--check --v2` "lands as A4.5." But A4.5 (#10395) implements `--check --staged-l4` (staged-content validation), NOT full v2 drift detection. `compose.py:2069-2076` explicitly rejects `--check --v2` with exit code 2, saying it's "reserved for A4.5 (#10395) and not implemented here." There is no way to run in-memory v2 compose and diff against on-disk `CLAUDE.linked.v2.md` — no story (A1–A6) covers this gap. A3 golden-file tests cover only `emit_v2_linked` in isolation against synthetic fixtures, not the full `deploy_alias_v2` pipeline.
- **Stories implicated**: A4 (#10388), A4.5 (#10395)
- **Suggested fix**: choose one — (a) implement `--check --v2` in `deploy_all` / `deploy` that compares in-memory v2 compose against on-disk linked-v2 (and update §9a text), OR (b) explicitly defer to PRD-E with a tracking issue and correct the §9a wording.

## WARNING 4 — R3 validator missing explicit layer guard

- **File**: `references/scripts/link_stage_validator.py:118-126`
- **Severity**: warning
- **Issue**: `_check_r3_l1_l3_no_project_context_slot` rejects ANY source with `slot: project-context` — no layer filter. Currently correct because `collect_sources_for_validation` pre-filters to L1–L3, but the asymmetry with `_check_r2_l2_l3_no_vault_slot` (which has `if src.layer in ("L2", "L3")`) is a maintenance hazard. If the source collector ever includes L4 (or any new layer), R3 fires against files it shouldn't.
- **Stories implicated**: A2e (#10491)
- **Suggested fix**: add an explicit layer guard: `if src.slot == "project-context" and src.layer in ("L1", "L2", "L3"):`. Self-documenting and symmetric with R2.

## Recommended fix order

1. ERROR first — it blocks v2 entirely on real installs and gates everything downstream (E6 cutover, etc.)
2. WARNING 2 (qa shim) — pairs naturally with the ERROR fix; both touch `parse_aliases_registry`
3. WARNING 1 (test fixture) — fixes a latent regression source
4. WARNING 3 (A4 §9a claim) — corrects spec/impl alignment; decide deliver vs defer
5. WARNING 4 (R3 layer guard) — low risk; can ship with any of the above

## Notes

- Each finding cites a specific file + line; DS evidence is in `AUDIT-PRD-A-DS-REVIEW.md`.
- Stories already shipped; this bug captures spec/impl gaps surfaced post-hoc.
- Hard gate on E6 (V2 CUTOVER #10685): the ERROR finding MUST be resolved before E6 can ship.
