# QA Results — #9939 (migrate_state_branch ignores commit_and_push return value)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 16:01 cycle 740
**PR**: #9940 (branch `squidsquad/task/9939`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Acceptance Criteria

| # | AC | Evidence | Result |
|---|----|----------|--------|
| 1 | Capture `commit_and_push` return value | `pushed = state_bus.commit_and_push(...)` at migrate_state_branch.py:133-136. Previously the return was discarded. | PASS |
| 2 | On False: print explicit "NOT durable" diagnostic to stderr | migrate_state_branch.py:138-141 — 3-line stderr block: "Migrated X/Y files LOCALLY, but commit_and_push failed — migration is NOT durable." | PASS |
| 3 | Diagnostic notes files are local only, not at origin | migrate_state_branch.py:142-146 — "Files exist in .squidsquad-state/ on this machine but have NOT reached origin/<state-branch>." | PASS |
| 4 | Diagnostic warns NOT to delete working-branch originals | migrate_state_branch.py:147-151 — "Investigate BEFORE deleting originals from the working branch." Locked by test `test_diagnostic_warns_against_deleting_originals` which asserts `"deleting originals"` (case-insensitive) in stderr. | PASS |
| 5 | Diagnostic references #9930 (the most likely root cause) | Same block: "Common cause: #9930 credential-helper wedge." | PASS |
| 6 | Returns 1 (not 0) on failure | `return 1` at migrate_state_branch.py:152. Asserted by `test_returns_one_when_push_fails`. | PASS |
| 7 | Happy path unchanged | If `pushed` is True, falls through to original "Migrated X/Y files to state branch." message and the existing exit-0 path. Asserted by `test_returns_zero_when_push_succeeds`. | PASS |
| 8 | Tests added | `TestMigratePushFailure9939` (3 cases) — all use real `tmp_path` + mocked `state_bus` so the actual `migrate()` function is exercised, not just the return-handling helper. | PASS |

## Test runs

- Targeted: `pytest tests/test_migrate_state_branch.py -k 9939` → **3 passed in 0.10 s**.
- Full module: `pytest tests/test_migrate_state_branch.py` → **30 passed in 0.10 s** (27 baseline + 3 new). All original state-pattern + main-flag tests still pass.

## Notes

- Skill skipped DS pre-push review for this PR: ~15-line diff implementing a single behavioral change (capture-and-act-on-return). I agree — the change is small, the pattern is standard (don't ignore boolean returns from network ops), and the test coverage exercises both branches via real `migrate()` invocation with mocked `state_bus`.
- This issue is in the same family as #9930 / #9934 (silent push failures in state-branch operations). The fix here is operator-facing — it makes the failure VISIBLE rather than fixing the failure itself; #9930's credential override + #9934's diagnostic do the actual prevention. This PR closes the "you didn't notice" gap.
- `migrate_state_branch.py` is a one-shot migration tool, so I did not run a live E2E. The unit tests' real-`migrate()` invocation with mocked `state_bus` covers the invariant correctly.
