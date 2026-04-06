# Working State

- **Task**: #149
- **Status**: in-progress
- **Started**: 2026-04-06 17:33
- **Quiet Cycle Counter**: 0

## Completed Steps
- Read planning artifacts (CONTEXT)
- Transitioned to in-progress

## Remaining Steps
- Add {{runtime:}} directive handler to compose.py
- Update role entry files to use {{runtime: souls/[role]}} instead of {{include: souls/[role]}}
- Create SOUL.md for each installed role during deploy
- Update manifest
- Redeploy all roles
- Run tests
- Transition to pending-test

## Key Decisions
- {{runtime:}} emits read instruction, not inline content
- Deploy creates SOUL.md if missing, never overwrites
- Read once at session start, not every cycle
