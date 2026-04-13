# FEAT-SKILL-195 Context — Extract Ralph Loop Steps as Modular Sub-Skills

## Scope

Make the Ralph Loop modular: each step is a sub-skill that can be included or excluded per role via YAML manifests. Reduces token consumption (~22% for non-PM roles) and makes roles composable. Three phases: engine (A), slim variants (B), PM extraction (C).

## Locked Decisions (human decided)

- **Slim variants as new files**: vault-protocol-slim.md, improvement-scan-slim.md as separate files. No conditional sections within existing files.
- **YAML manifests**: includes.yml per role directory. Machine-parseable, matches manifest.yaml pattern.
- **Engine first**: Phase A (manifests + compose.py) → Phase B (slim variants) → Phase C (PM inline extraction).
- **Custom dev variants inherit**: be, fe, etc. inherit from dev's manifest, override specific includes only.
- **Worth it**: 16% reduction + composability justifies the work. Enables #347 (separate QA).

## Dev Discretion (dev agent can choose)

- YAML manifest structure (flat list vs categorized)
- How compose.py resolves inheritance (merge strategy)
- Which PM inline steps to extract first in Phase C
- Naming convention for slim variants

## Side Effect Mitigations (required)

- All existing composed CLAUDE.md must be identical before/after Phase A (engine only, no behavioral change)
- Run full test suite after each phase
- Diff composed output before/after to verify no content loss
- Update manifest.md to document new composition model

## Upgrade Path (required)

- Phase A: compose.py gains manifest reading. Old {{include:}} still works. No breaking change.
- Phase B: Roles get slim variants. Composed output shrinks but behavior unchanged.
- Phase C: PM inline steps extracted. PM CLAUDE.md shrinks significantly.
- Existing installs: squidsquad-upgrade recomposes with new manifests automatically.

## Out of Scope

- Runtime conditional loading (sub-skills always composed at build time)
- Token budgeting (compose.py doesn't enforce a max token count)
- Graphify integration (#532)
