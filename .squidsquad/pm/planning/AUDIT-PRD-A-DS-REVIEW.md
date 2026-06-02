Here are my findings:

---

### Finding 1

- **File**: `references/scripts/config.py` (lines 337-433) vs `.squidsquad/config.md` (lines 14-19)
- **Line**: config.py:371, config.md:14-19
- **Severity**: error
- **Issue**: `parse_aliases_registry()` expects a 3-column markdown table (`| alias | role-class | L3 domain |`) in the `## Aliases` section. The actual `.squidsquad/config.md` in this repo uses the legacy bullet-list format:
  ```
  ## Aliases
  - **skill**: skill
  - **pm**: pm
  ```
  This means `deploy <alias> --v2` and `deploy-all --v2` are unreachable on real installs — they abort with `"section is present but contains no table"` before any link-stage work begins. Success criteria 1 and 2 are effectively untestable end-to-end against the living install.
- **Evidence**: PRD §3 success criterion 1 requires `compose.py deploy <alias>` to produce `.squidsquad/<alias>/CLAUDE.md` (v2: `CLAUDE.linked.v2.md`). SC2 requires `deploy-all` to iterate the `## Aliases` registry. Neither path can execute against the actual config.md. The PRD §6 dependency table lists the `## Aliases` registry as "already shipped via installer," but the installed config.md hasn't been migrated to table format.
- **Suggested fix**: Either (a) add a bullet-list fallback path in `parse_aliases_registry` that reads the legacy `- **alias**: value` format when no table is found, or (b) implement a one-shot migration that rewrites `## Aliases` to table format on first v2 invocation, or (c) ship an installer update that writes the table format and include a migration in the installer.

---

### Finding 2

- **File**: `tests/test_compose_a2f_10492.py` (line 60)
- **Line**: 60
- **Severity**: warning
- **Issue**: The `_stage_minimal_install` helper writes config.md with column names `| Alias | Role class | L3 domain |`. But `config.py` line 377 compares lowercased column names against the expected tuple `("alias", "role-class", "L3 domain")`. `"Role class".lower()` is `"role class"`, which does **not** equal `"role-class"` (space vs hyphen). A real config.md written with these column names would be rejected. The test passes only because it bypasses the parser by passing a pre-built `registry` dict directly to `deploy_alias_v2`. If the installer or any other code generator copies this column format from the test, v2 deployment will fail.
- **Evidence**: The header name comparison at `config.py:377-378` does strict `lower()` matching. `"Role class".lower() → "role class"` ≠ expected `"role-class"`. The A2f test fixture is the only place in the codebase that shows a complete example config.md with the `## Aliases` table — it serves as an implicit spec for the installer.
- **Suggested fix**: Change line 60 to `"| alias | role-class | L3 domain |\n"` (matching the canonical column names in `_ALIASES_HEADER_COLUMNS`). Also add an integration test that actually parses the config.md written by `_stage_minimal_install` through `parse_aliases_registry` to catch format mismatches.

---

### Finding 3

- **File**: `references/scripts/config.py` (line 297)
- **Line**: 297
- **Severity**: warning
- **Issue**: `ALIASES_ROLE_CLASSES = frozenset({"pm", "worker", "verifier", "dm"})` does not include `"qa"`. The actual `.squidsquad/config.md` line 19 has `- **qa**: qa`. The rest of the codebase carries extensive #6274 dual-aware shim logic (`_BASE_ALIAS_6274` at line 1754-1758, `_list_known_role_identities` at line 899, `_resolve_variant` at lines 1729-1732) that accepts `qa` ↔ `verifier` interchangeably. If a config `## Aliases` table includes `| qa | qa | — |`, `parse_aliases_registry` would reject it with "unknown role-class 'qa'" even though the v1 code path and every other subsystem accept `qa`. This creates an inconsistency where `deploy <alias> --v2` rejects valid v1 aliases.
- **Evidence**: `ALIASES_ROLE_CLASSES` at config.py:297 is a strict frozenset without `qa`. The #6274 migration renamed `qa` → `verifier` but the dual-aware shim everywhere else in compose.py supports both names during the transition window. The parser doesn't participate in this shim, so installs that haven't been fully migrated (which is the current state — config.md still says `qa`) break on the v2 code path.
- **Suggested fix**: Add `"qa"` to `ALIASES_ROLE_CLASSES` or add a normalization step in `parse_aliases_registry` that maps `qa` → `verifier` (and `dev` → `worker`) before validation, mirroring `_BASE_ALIAS_6274`.

---

### Finding 4

- **File**: `references/scripts/compose.py` (lines 2069-2076)
- **Line**: 2069-2076
- **Severity**: warning
- **Issue**: The PRD §9a coexistence section states that A4's v2 sibling `--check --v2` "lands as A4.5." But A4.5 (#10395) implements staged-content validation (`--check --staged-l4`), not full v2 drift detection. The code at lines 2069-2076 explicitly rejects `--check --v2` with exit code 2, saying it's "reserved for A4.5 (#10395) and not implemented here." There is no way to run an in-memory v2 compose and diff it against the on-disk `CLAUDE.linked.v2.md` — no story covers this gap. The A3 golden-file tests verify byte-stability only for `emit_v2_linked` in isolation (not the full `deploy_alias_v2` pipeline including headers), and only against synthetic fixtures (not the real install).
- **Evidence**: SC7 requires "byte-stable across re-runs given unchanged inputs." A3 covers this at the unit level but there's no integration-level v2 drift check. The `check_role` function at line 1388-1410 operates on v1 paths only (`CLAUDE.md`). The PRD §9a says the v2 sibling lands as A4.5 but A4.5's scope is staged-content validation, not drift detection. No story (A1-A6) or follow-on tracks delivery of v2 drift-check.
- **Suggested fix**: Either (a) add `--check --v2` support in `deploy_all` and `deploy` that compares in-memory v2 compose against `CLAUDE.linked.v2.md`, or (b) explicitly document this as deferred to PRD-E with a tracking issue number, and update the §9a text to not claim it already landed.

---

### Finding 5

- **File**: `references/scripts/link_stage_validator.py` (lines 118-126)
- **Line**: 118-126
- **Severity**: warning
- **Issue**: The function `_check_r3_l1_l3_no_project_context_slot` does not filter by layer — it rejects ANY source with `slot: project-context`. The function name implies it only checks L1 and L3 sources, but the implementation checks all sources. This happens to be correct today because `collect_sources_for_validation` only collects L1-L3 sources and L4 is never in the list. But the asymmetry with `_check_r2_l2_l3_no_vault_slot` (which correctly filters to L2+L3 only, matching its name and the spec) is a maintenance hazard.
- **Evidence**: Compare `_check_r2_l2_l3_no_vault_slot` at line 107-115 which has `if src.layer in ("L2", "L3")` vs `_check_r3_l1_l3_no_project_context_slot` at line 118-126 which has no layer guard. If `collect_sources_for_validation` changes to include additional source types, R3 could fire against files it shouldn't (e.g., a future L4 inclusion). The PRD success criterion 6 item 3 specifies "L1-L3 source file" — the code happens to match only because the source list is pre-filtered, not because it verifies the constraint.
- **Evidence**: PRD §3 success criterion 6 item 3: "L1-L3 source file with `slot: project-context` frontmatter → abort."
- **Suggested fix**: Add an explicit layer guard: `if src.slot == "project-context" and src.layer in ("L1", "L2", "L3")`. This makes the check self-documenting and symmetric with R2.