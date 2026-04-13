# Working State

- **Task**: #401
- **Status**: in-progress
- **Started**: 2026-04-12 22:33
- **Quiet Cycle Counter**: 0

## Completed Steps
- Read CONTEXT.md, RESEARCH.md, TEST-PLAN.md

## Remaining Steps
- Phase A: Directory rename (tools → capabilities), schema v2, field renames
- Phase B: compose.py {{capability:}} directive
- Phase C: capability_check.py runtime self-check
- Phase D: PM capability gap analysis in feature-intake
- Phase E: Agent startup self-check instructions
- Phase F: Terminology updates (design-tools → design-capabilities, WIZARD.md, SKILL.md)
- Phase G: Update tests
- Run full test suite
- Transition to pending-test

## Key Decisions
- Hard schema v2 bump (no backward compat)
- Directory: references/sub-skills/capabilities/
- Build-time composition via {{capability:}} directive
- capability_check.py as deterministic script (not prose)
