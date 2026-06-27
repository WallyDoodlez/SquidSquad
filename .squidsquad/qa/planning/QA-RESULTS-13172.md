# QA-RESULTS-13172 — fail-closed on wrong-type additional_includes (compose v2 loader)

**Verdict: PASS — zero gaps.** PR #13257 merged (squash).

## AC walk (independent — derived from issue body)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | wrong-type `additional_includes` (bare string / dict / int) → `sys.exit(1)` with stderr ERROR naming role + type | PASS |
| AC2 | valid list → base + additional concatenated, composes normally | PASS |
| AC3 | null / absent → normalizes to `[]` (no exit) — `… or []` idiom preserved | PASS |

## Evidence
- Code (compose.py:293-311): wrong-type branch now `print(ERROR …, file=sys.stderr); sys.exit(1)` matching the same-branch siblings (base_role-missing, missing sub-skill file). Corrected inline comment (MEDIUM review) accurately notes the base-`includes` wrong-type path returns None (different branch/contract).
- skill unit tests (test_compose.py `TestManifestV2AdditionalIncludesWrongType13172`): 4 tests PASS (str→exit, dict→exit, valid-list→resolves, null→valid).
- **QA independent test** (`tests/test_feat_13172_additional_includes_failclosed.py`): asserts the diagnostic **names the role** (`worker-myrole` present in stderr — skill's tests don't check this) and covers an **int** type (skill covered str/dict). Sample stderr: `ERROR: includes.yml for worker-myrole: \`additional_includes\` is str, expected list`. ALL PASS.
- No-regression: full `tests/test_compose.py` = 89 passed, 0 failures.

## Notes
- Out-of-scope observation (skill-flagged on issue): `_load_manifest_v2`/`_load_manifest_v2_from_file` appear **unreachable from the production deploy path** post-E6 (#10685) — deploy/deploy-all/wizard route through `v2_link_stage.emit_v2_linked`. Retire/tombstone is a **separate triage decision**, correctly NOT folded here. The guard is correct + cheap if the path is re-wired, and deploy-all wraps each alias in `except SystemExit` so a bad manifest fails one alias, never the fleet. **Not a gap — not reblocking.**
- Deterministic code → no CQ required. No new manifest files.

Status: pending-test → pending-ship.
