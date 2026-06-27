# TEST-PLAN-13264 — tombstone the unreachable v2 manifest loader

**Derived independently** from my filed finding (#13264).

## Expected behavior
`_load_manifest_v2` / `_load_manifest_v2_from_file` (unreachable dead code post-E6) must be clearly marked as intentionally-retained dead code with rationale, with a guard that prevents silent revival. Behavior of the retained functions (incl. the #13172 fail-closed guard) must be unchanged.

## ACs (independent)
- AC1 tombstone marker + rationale on both functions
- AC2 behavior preserved — functions + #13172 guard still work
- AC3 a guard prevents silent revival (re-wire forces a re-decision)
- AC4 no production caller (unreachability holds)

## Method
Run skill's tombstone tests + the #13172 behavior tests + full `tests/test_compose.py`. QA test (`tests/test_feat_13264_tombstone_guard_not_vacuous.py`) proves the enforcement guard is NOT vacuous by injecting a fake offender and confirming the scan detects it.
