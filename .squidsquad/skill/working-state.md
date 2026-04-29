# Working State

- **Task**: #3465
- **Status**: in-progress
- **Started**: 2026-04-28 22:02

## Remaining Steps
- Remove references/roles/general/ (concept eliminated per human)
- Update compose.py: generalize inheritance, base_role+additional_includes schema
- Create 20 preset variant directories
- Create variant-specific sub-skills
- Rework SOUL assembly (L1 + role SOUL, no general role)
- Update tests, run full suite

## Key Decisions
- Layer 2 = existing roles, Layer 3 = variant customization
- Layer 3 SOUL.md = full file (replaces L2 SOUL, not overlay)
- <base>-<variant> naming convention
