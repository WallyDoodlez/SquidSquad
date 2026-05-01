# Working State

- **Task**: #4083
- **Status**: in-progress
- **Started**: 2026-04-30 22:57
- **Quiet Cycles**: 0

## Planned Approach

Phase A: Setup wizard preset integration
Phase B: L4 propagation mechanism
Phase C: Upgrade path from pre-layer to post-layer

## Completed Steps
- Read CONTEXT.md — 3 phases, locked decisions, side effect mitigations
- Read wizard.py scaffold_install and build_config_md — spec shape uses "preset" field, agents have "role"+"variant"
- Identified key integration points: wizard.py line 446 (preset field), line 735 (scaffold_install), compose.py deploy_role
- Created feature branch squidsquad/skill/4083

## Remaining Steps
- Phase A: Add PROJECT_TYPE_PRESETS mapping (ios→dev-ios+pm-ios+qa-ios+dm-ios, etc.)
- Phase A: Add project type question to wizard spec flow
- Phase A: Wire preset selection to agent variant in scaffold_install
- Phase A: Add pre-flight checks (gh auth, git repo)
- Phase A: Add L4/SOUL customization informational guidance
- Phase B: L4 project sub-skill files mechanism (compose.py appends references/sub-skills/project/*.md)
- Phase C: Upgrade auto-detect pre-layer, extract Project Adaptation to L4
- Setup/Upgrade verification gate checklist sub-skill
- Tests for all phases

## Key Decisions
- wizard.py spec already has "preset" and agent "variant" fields — extend, don't replace
- Presets map project type → set of role+variant pairs for all agents
- L4 uses references/sub-skills/project/ directory (already created by #3465)
- Will implement Phase A first, then B and C in subsequent cycles
