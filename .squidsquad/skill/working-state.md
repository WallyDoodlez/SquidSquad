# Working State

- **Task**: #328
- **Status**: in-progress
- **Started**: 2026-04-11 14:39
- **Quiet Cycle Counter**: 0

## Feature

FEAT-328 — Intent-driven setup wizard with role manifest registry.

This is a multi-cycle feature (~2000 lines of spec). I'm executing it in
discrete phases, each landing as its own atomic commit.

## Phase Plan

- [x] **Phase A — Role manifest files** (commit 1620094)
  - 5 YAML files under `references/roles/<role>/manifest.yaml`
  - Pure data, no code changes, no risk to existing flow
  - Domain-only language per Q-new14
  - Topology matches CONTEXT.md final inventory table (line 702)
- [x] **Phase A.1 — `always_installed` schema addition** (this cycle)
  - Anticipates #347 (Separate PM from QA) per PM's comment hint on #328
  - pm/dm: `always_installed: true`; designer/dev/qa: `false`
  - v1 invariant: `always_installed == !show_in_roster` (but both fields
    kept because they mean different things conceptually)
- [x] **Phase B — Tool registry** (this cycle)
  - `references/tools/{figma,google_stitch,local_html,local_delivery}/`
  - Each with `manifest.yaml`, `setup.md`, `sub-skill.md`
  - 3 designer tools + 1 DM tool
  - Cross-references validated: every role's `requires_tools` ID resolves
- [ ] **Phase C — Preset manifests**
  - `references/presets/{software-dev,design}/manifest.yaml`
  - Declares `role_install_order` (PM/DM implicit)
- [ ] **Phase D — Validator (`references/scripts/manifest.py`)**
  - Schema validation (fields, types, schema_version)
  - Cross-reference (routes_to targets exist; requires_tools IDs exist)
  - Cycle detection in routes_to graph
  - Domain-only linter for Q-new14 (rejects mentions of `config.md`,
    `.squidsquad/`, `CLAUDE.md`, `SOUL.md`, internal script paths)
  - `validate` CLI that exits non-zero with field-level errors
- [ ] **Phase E — Status label additions (additive only)**
  - Add `pending-human-approval`, `pending-human-review`, `pending-human-setup`
  - Update tracker.py LEGAL_TRANSITIONS + ROLE_AUTHORITY (both new)
  - Do NOT remove `pending` yet — additive phase first, migration later
- [ ] **Phase F — Wizard implementation**
  - LLM intent classifier (inside-Claude prompt)
  - Generic setup_requirements walker
  - Review screen (P/V/E/A)
  - Step 0 gh prerequisite check, Step 0b re-run detection
  - Installer agent lifecycle (ephemeral, exits on completion)
- [ ] **Phase G — compose.py + config.py manifest-aware refactor**
  - Replace hardcoded role maps with manifest lookups
  - Preserve backward compatibility for existing config.md files
- [ ] **Phase H — statusline.sh manifest-aware**
  - Read installed roles from manifest, not hardcoded list
- [ ] **Phase I — Migration script** (`migrate_status_labels.py`)
  - Rewrite `pending` → `pending-human-approval` on all issues
  - Transition window: both old and new accepted
  - After verification, drop `pending` from LEGAL_TRANSITIONS
- [ ] **Phase J — Tests**
  - Per TEST-PLAN.md — schema validation, resolver, wizard state, migration idempotency

## Completed Steps

- Read RESEARCH.md, CONTEXT.md (partial), TEST-PLAN.md (partial), PHASE2-PREP
- Picked up #328, transitioned to in-progress
- Wrote 5 role manifests (Phase A complete)
- Validated all 5 parse with PyYAML
- Ran full static test suite — 157 pass, no regressions

## Key Decisions (dev discretion, recorded for next-cycle context)

- **Manifest schema fields**: `schema_version`, `id`, `display_name`, `tagline`,
  `description`, `show_in_roster`, `iteration_mode`, `routes_to`,
  `requires_tools`, `setup_requirements`. All locked decisions honored.
- **Tool ID convention**: short name matching the tool folder (`figma` not
  `figma_mcp`). The `mcp_name` field inside the tool manifest maps to the
  actual MCP server — but role-level `requires_tools` uses the short form,
  per Q-new5's worked example.
- **Empty `requires_tools: {}` vs omission**: always present as a dict,
  possibly empty. Simpler for the validator than optional key.
- **`description` field added** (not strictly required by the spec but
  recommended by Q-new14's "public contract" framing). One sentence,
  domain-only. Makes the manifest self-documenting when browsed raw.

## Side Effects I MUST Mitigate (from CONTEXT §side-effect-mitigations)

1. PM CLAUDE.md hardcoded refs — Phase G
2. `compose.py` dispatch tables (lines 100-106, 166-167, 201-214) — Phase G
3. `config.py` FIELD_MAP + sync_agents — Phase G
4. `statusline.sh` agent loop — Phase H
5. Malformed manifest YAML → loud failure — Phase D
6. `routes_to` cycle detection — Phase D
7. Boot scripts (`start-role.sh/ps1`) must work for any new role — already
   parameterized per CONTEXT, no change needed

## References

- CONTEXT: `.squidsquad/skill/planning/FEAT-328-CONTEXT.md` (801 lines)
- TEST-PLAN: `.squidsquad/skill/planning/FEAT-328-TEST-PLAN.md` (307 lines)
- RESEARCH: `.squidsquad/skill/planning/FEAT-328-RESEARCH.md` (654 lines)
- Final inventory table: CONTEXT.md ~line 702
