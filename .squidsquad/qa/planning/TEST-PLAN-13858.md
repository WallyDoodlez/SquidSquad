# TEST-PLAN-13858

PRD-VAULT-V2 P2 — structure: `vault-schema.json` registry, `systems/` hub layer, registry-derived templates (S2.1–S2.3). Derived independently from the issue body's story list + PRD-VAULT-V2.md §P2 + VAULT-ARCH.md §3.1/§3.2/§3.3/§3.5/§4.2a/§9.9 — not from skill's PR description.

Per PRD-VAULT-V2's framework-vs-prepopulation split: S2.1 and S2.2's framework half are verified on scratch/greenfield installs; S2.2's prepopulation half is verified against this repo's real `.squidsquad/vault/`.

## TCs

- **TC1 (S2.1, custom-type consumption)**: on an isolated scratch vault, register a custom type (`runbook` → folder `runbooks`, budgeted, weight 5.0, prefix `rb-`) in `vault-schema.json`; confirm the engine (`vault-query.mjs`) scans the custom folder and surfaces a note in it via search — not just that the folder/file exist.
- **TC2 (S2.1, unregistered-folder invisibility)**: in the same scratch vault, a note dropped in a folder NOT in the registry (`galaxy/`, absent from this custom taxonomy) must be invisible to search even on an exact-slug match.
- **TC3 (S2.1, absent-registry degrade)**: a scratch vault with no `vault-schema.json` at all degrades to the P1 default profile (PARAG folders, standard weights) — reproduces pre-#13858 behavior exactly.
- **TC4 (S2.2 framework, hub + check-structure)**: on a scratch vault, registering `system` (hub, folder `systems`) makes `vault_check.check_structure()` pass once `systems/` exists (and fail-clean when absent).
- **TC5 (S2.2 framework, Level-2 zero-hub-link flag)**: on the same scratch vault, a budgeted-type note with zero wikilinks to any hub-type note is flagged by `check_hub_links()`; a sibling note that links to the hub is NOT flagged. Advisory only (exit 0 either way).
- **TC6 (S2.2 prepopulation, live traversal)**: against this repo's real `.squidsquad/vault/`, `vault-query.mjs --entities pr-merge` reaches the `systems/pr-merge.md` hub via a direct filename match, and the traversal (`traversed[]`) reaches ≥1 galaxy leaf with `walkedFrom` naming the hub directly — confirming the hub hop cost 0 budget (traversal budget is only spent on the budgeted hop into the galaxy leaf).
- **TC7 (S2.3, registered-type template resolution)**: `vault_entity.resolve_template()` / `create_note()` resolve a dedicated `<type>.md` template for every type in the shipped default profile (except `archive`, a status not a creatable type per §3.4); an unregistered type raises `ValueError`.
- **TC8 (S2.3, custom-type generic fallback)**: a custom registered type with no dedicated template file under `references/vault-templates/` falls back to `_generic.md`; the created note carries the custom type's stamped frontmatter and declared prefix.
- **TC9 (S2.3, slug validation)**: `create_note()` rejects empty, path-traversal (`../`), and dotfile-leading slugs; accepts a normal alnum/dash/dot/underscore slug; refuses to overwrite an existing note.
- **TC10 (LLM-consumed instruction)**: `vault-protocol.md`'s "Creating Notes" section (folder-based → TYPE-based template resolution) is comprehensible to a fresh agent with no other context — author and run a comprehension spec per #9184.
- **TC11**: regression test suite (`test_vault_engine_13857.py`, `test_vault_check_13858.py`, `test_vault_templates_13858.py`, `test_vault_check_unit.py`, `test_vault_engine_installer_13857.py`, `test_vault.py`, `test_vault_check.py`) all pass.
- **TC12**: full ship gate (static + integration) passes clean.
