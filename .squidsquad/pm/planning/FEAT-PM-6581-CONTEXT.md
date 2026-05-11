# FEAT-PM-6581 Context — Wizard Reframing: L3 Picks Agents, L4 Records Project Specifics

## Scope

Reframe the setup wizard so that:
1. L3 domain selection (from preset manifest) drives agent selection — no hardcoded `PROJECT_TYPE_PRESETS`
2. L4 project files (`.squidsquad/project/`) are populated during setup with project-specific knowledge
3. Presets are the single authority for domain-to-agent mappings
4. Wizard asks "what are you building?" instead of "pick your agents"

Out of scope: migration path (pre-public), new presets beyond existing ones, #6574 (zero-prereq install — separate task).

## Locked Decisions (human decided)

- **Domain variants live in preset manifest**: Each preset's `manifest.yaml` declares its domain variants. Preset = single authority. Extract to a separate domain registry later if cross-preset sharing is ever needed.
- **Hybrid L4 writer**: `wizard.py` `scaffold_install()` writes structured L4 files (stack, test commands, detected config) mechanically. WIZARD.md runbook adds qualitative notes (conventions, patterns from repo scan). Structured data is testable; qualitative enrichment is flexible.
- **All roles get domain variant**: PM, QA, DM, and dev workers all receive domain-specific L3 specialization. Keeps current `apply_project_type()` behavior — domain awareness across the whole team.
- **No migration needed**: Project is pre-public. No upgrade path, no graceful degradation.
- **Fixed pipeline always present**: PM → Workers → Verifiers → DM (from issue body, human-confirmed).
- **Multi-agent slots**: Each pipeline slot can hold multiple agents. Topology confirmed in Step 3 (parallel vs sequential, dependencies).
- **Wizard is thin orchestrator**: L3 presets bring their own detection logic. No wizard code changes needed for new presets.

## Dev Discretion (dev agent can choose)

- How to structure the `domain_variants` field in preset manifest YAML (schema design)
- How to refactor `apply_project_type()` — remove entirely vs. refactor into manifest resolution
- How to structure L4 project files (file naming, sections, format)
- How the WIZARD.md runbook detects and writes qualitative notes
- Test strategy for covering the new manifest-driven path

## Side Effect Mitigations (required)

- `compose.py` merge conflict at line 1071 must be resolved before or as part of this task
- `generate_default_spec()` in `cmd_setup_yes` (non-interactive path) must be updated to use manifest resolution instead of hardcoded preset
- `scaffold_install()` L4 file writes must respect existing `overwrite_existing` guards
- `test_wizard.py` tests for `apply_project_type()` (lines 2013-2048) must be rewritten for the new path

## Upgrade Path (required)

- N/A — no upgrade impact (pre-public)

## Out of Scope

- Zero-prereq install (Step 0) — tracked separately as #6574
- New presets beyond existing (software-dev, design-deprecated)
- Domain registry / cross-preset domain sharing
- Migration tooling for existing installs
