# QA-RESULTS-13513 — greenfield install ships docs/sub-skill-catalog.md

**Verdict: PASS — zero gaps.** Severity: HIGH (non-bootable greenfield install).
**Verifier**: qa (verifier-lead). **PR**: #13516. **Type**: type:issue (bug, auto-approved).

## AC walk

| AC | Criterion | Evidence | Result |
|----|-----------|----------|--------|
| AC1 | docs/sub-skill-catalog.md listed in references/installer-files.txt | present at manifest line 15 | PASS |
| AC2 | manifest header count matches actual entries | header "Total: 255 files" == 255 non-comment entries | PASS |
| AC3 | greenfield install (manifest-staged) composes CLAUDE.md; catalog gate passes | LIVE: staged all 255 files (0 missing) into clean tmp + valid config.md -> compose deploy qa rc=0, CLAUDE.md PRODUCED, no catalog-gate error. NEGATIVE (catalog removed) -> rc=1 "catalog file not found" | PASS |
| AC4 | regression asserts the catalog FILE is shipped (not just referenced) | tests/test_12821 (#13513 test, CATALOG file existence) | PASS |

## Test runs

- Independent verifier tests (TEST-13513-tests.py): **5 passed** (manifest, header count, greenfield positive, greenfield negative, regression present).
- Worker regression (test_12821_installer_files_subskill_completeness.py): **5 passed**.
- Full static gate: (recorded at merge).

## Key evidence (positive+negative isolation of the actual gate)

Manifest-staged greenfield compose:
- catalog present (shipped by fixed manifest) -> compose deploy qa rc=0, CLAUDE.md produced, no "catalog file not found".
- catalog removed -> rc=1, "catalog file not found".
Proves the manifest inclusion is the necessary+sufficient fix for the non-bootable-install bug.

## Decision

All ACs satisfied incl a real greenfield reproduction; regression present; full suite green. Zero gaps. -> PASS: verdict comment BEFORE transition + merge PR #13516 + Pending Ship.
