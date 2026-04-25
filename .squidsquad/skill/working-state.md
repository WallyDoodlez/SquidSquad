# Working State

- **Task**: #2724
- **Status**: in-progress
- **Started**: 2026-04-25 12:30

## Completed Steps
- Read CONTEXT.md, RESEARCH.md, TEST-PLAN.md

## Remaining Steps
- Remove Auto Boot Agents section from config.md
- Remove auto-boot from config.py FIELD_MAP
- Remove config guard from boot_remote.py main()
- Update cycle_pre.py: remove auto_boot_agents, add boot_results
- Update boot-remote-agents.md sub-skill
- Update agent-instructions.md
- Run compose.py deploy pm
- Create start-squad.ps1 and start-squad.sh
- Write unit tests
- Run full test suite
- Copy changed references to live

## Key Decisions
- Follow CONTEXT.md locked decisions exactly
- start-squad calls boot_remote.py --all (not individual start scripts)
- Static start-squad files (no compose target)
