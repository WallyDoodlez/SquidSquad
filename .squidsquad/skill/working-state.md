# Working State

- **Task**: #1426
- **Status**: in-progress
- **Started**: 2026-04-18 22:02
- **Quiet Cycles**: 0

## Completed Steps
- none

## Remaining Steps
- Create references/scripts/shared_fs.py — init, read_secret, write_secret, read_clones
- Update model_router.py — read API keys from ~/.squidsquad/secrets, fallback to env
- Update health_check.py — read clones from ~/.squidsquad/clones/ instead of .local-config
- Update wizard — create ~/.squidsquad/ during setup, guide secrets entry
- Write tests
- Run full test suite

## Key Decisions
- ~/.squidsquad/ location (human-locked)
- Plain text secrets with chmod 600 (human-locked)
- Fallback to env vars for backwards compat
