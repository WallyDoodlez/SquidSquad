# Working State

- **Task**: #3465
- **Status**: in-progress
- **Started**: 2026-04-28 19:02

## Planned Approach

1. Create Layer 1 base SOUL (`references/roles/base/SOUL.md`)
2. Create Layer 2 general-role SOULs (`references/roles/general/{developer,coordinator,verifier,delivery}/SOUL.md`)
3. Create Layer 2 CLAUDE content as sub-skills (`references/sub-skills/general-{developer,coordinator,verifier,delivery}/`)
4. Extract shared content from existing role SOULs into L1/L2
5. Add `general_role` field to role manifests
6. Update compose.py: SOUL assembly from 3 layers, `upgrade_soul()`, atomic writes
7. Migrate all 5 roles atomically
8. Run tests, verify smoke tests

## Completed Steps

(none yet)

## Remaining Steps

- All of the above

## Key Decisions

- Directory layout: `references/roles/base/` for L1, `references/roles/general/<category>/` for L2
- SOUL layers concatenated at deploy time → single flat file
- CLAUDE layers: L2 encoded as sub-skills in `general-<category>/` namespace, included via includes.yml
- `general_role` field in manifest.yaml drives L2 resolution
- PM: dual `general_role: [coordinator, verifier]`
- Dev variants inherit `general_role` from parent manifest (existing fallback)
