# QA-RESULTS-13264 — tombstone the unreachable v2 manifest loader

**Verdict: PASS — zero gaps.** PR #13265 merged (squash). (verifier-filed dead-code finding; skill chose tombstone-over-remove — the conservative correct call, retaining the schema reader + #13172 guard in case the path is re-wired.)

## AC walk (independent — derived from my filed finding)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | tombstone marker + clear rationale on BOTH functions | PASS (`TOMBSTONE (#13264)` ×2) |
| AC2 | behavior preserved — functions still work, #13172 fail-closed guard intact | PASS (4 #13172 tests still green) |
| AC3 | a guard prevents silent revival of the dead code | PASS (guard test added) |
| AC4 | no production caller (unreachability holds) | PASS (grep-confirmed) |

## Evidence
- Code (compose.py:187,269): `.. note:: TOMBSTONE (#13264)` docstrings on `_load_manifest_v2` + `_load_manifest_v2_from_file` — rationale (unreachable post-E6, deploy routes via `emit_v2_linked`), retained-not-deleted, "remove with tests only after confirming retired; don't add new production callers without re-deciding."
- skill tests (test_compose.py `TestManifestV2TombstoneUnreachable13264`): `test_symbol_only_referenced_within_compose` (no production caller outside compose.py), `test_tombstone_marker_present`. Both PASS.
- **QA independent test** (`tests/test_feat_13264_tombstone_guard_not_vacuous.py`): proves the guard is **NOT vacuous** — an injected fake offender (`from compose import _load_manifest_v2` in a non-compose script) IS detected by the same scan logic, so the tombstone is genuinely enforced against a future re-wire (skill's test only proves the guard passes on the clean tree, not that it would fail on a violation). ALL PASS.
- Behavior preserved: the 4 `TestManifestV2AdditionalIncludesWrongType13172` tests still pass against the tombstoned (retained) functions.
- No-regression: full `tests/test_compose.py` = 91 passed, 0 failures.

## Notes
- Tombstone (retain) over delete is the right call: the schema reader + the #13172 fail-closed guard survive intact for a future re-wire; the enforcement guard makes the dead-code status self-policing. Resolution exceeds my suggested direction.

Status: pending-test → pending-ship.
