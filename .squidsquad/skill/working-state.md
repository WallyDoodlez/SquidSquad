# Working State

- **Task**: #5888
- **Status**: in-progress
- **Started**: 2026-05-06 19:32

## Planned Approach

Create /squidsquad-compose skill. Multi-cycle.

### Implementation Order
1. Create `.claude/commands/squidsquad-compose.md` — slash command
2. Add `/squidsquad-compose` section to SKILL.md
3. Move SOUL.md seeding into compose.py deploy_role
4. Strip compose calls from wizard.py scaffold_install
5. Strip compose calls from add_role.py
6. Remove dead boot_role + agent-compose code from compose.py
7. Fix stale `.claude/commands/squidsquad-upgrade.md`
8. Update PM post-merge-recompose sub-skill
9. Update tests
10. Update installer-files.txt if needed

### Key Constraints
- Atomic migration — all changes ship together
- review:human-required label — PR needs human review
- wizard.py/add_role.py keep direct Python import for mechanical paths
- Slash command is for LLM-orchestrated flows only
- SOUL.md seeding must work when deploy_role is called (option a from research)

## Completed Steps
- (none yet)

## Remaining Steps
- All 10 steps above

## Key Decisions
- compose.py remains the mechanical engine — skill is a wrapper
- Python API callers (wizard, add_role) keep direct imports for CI path
- SOUL.md seeding moves into deploy_role (cleanest option per AUDIT2)
