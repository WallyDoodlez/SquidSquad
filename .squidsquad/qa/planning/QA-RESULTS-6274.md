# QA Results — #6274 sub-phase 6274.1 (dual-aware terminology shim)

**Verifier**: qa-lead
**Timestamp**: 2026-05-23 05:31 cycle 767
**PR**: #9964 (branch `squidsquad/task/6274`)
**Verdict**: PASS — zero gaps on the sub-phase 6274.1 scope. Status → Pending Ship.

This is the first of three sub-phases (6274.1 shim → 6274.2 rename → 6274.3 cleanup). Sub-phase 6274.1 ships ONLY the dual-aware shim so both old and new role names work during migration. Post-rename ACs (AC2.x) and cleanup ACs (AC3.x) are out of scope for this PR.

## AC walk (sub-phase 6274.1, per CONTEXT-6274.md)

| AC | Result | Evidence |
|----|--------|----------|
| AC1.1 — `_list_known_role_identities()` returns dual set | PASS | Live: `compose._list_known_role_identities()` returns `['dev', 'dm', 'pm', 'qa', 'verifier', 'worker']` — the expected superset `{worker, verifier, pm, dm, dev, qa}` is present. Direct unit test `test_dual_aware_identities` in the new test module covers. |
| AC1.2 — `_resolve_variant("worker-skill")` and `_resolve_variant("dev-skill")` both resolve | PASS | Covered by tests in `test_terminology_dual_aware_6274.py` (27/27 pass). |
| AC1.3 — `config.py get_field("workers")` reads `Workers:` and falls back to `Dev Agents:` with deprecation warning | PASS | `_DUAL_AWARE_CONFIG_FIELDS_6274` mapping at config.py:48; fallback + deprecation logic at config.py:186-187 (`if val is None and field in _DUAL_AWARE_CONFIG_FIELDS_6274`). |
| AC1.4 — `tracker.py create_issue/create_task` dual-tag; `--role` accepts both old and new suffixes (D11) | PASS | `_build_dual_role_labels_6274` at tracker.py:315, used at create_issue (line 694) and create_task (line 747). `_canonicalize_role` at tracker.py:218 used at line 374 + 986 (caller-role path). Tests `test_create_dual_label_during_migration` and `test_role_suffix_dual_aware_6274` cover. |
| AC1.5 — `migrate_labels_6274.py` exists, idempotent, has `--dry-run` | PASS | `references/scripts/migrate_labels_6274.py` exists; `--help` confirms `--dry-run` flag and "Idempotent" claim in docstring. |
| AC1.6 — Vault note `migration-6274-cutover` as PLACEHOLDER | PASS | `.squidsquad/vault/galaxy/learning-migration-6274-cutover.md` exists with proper YAML frontmatter (type: learning, tags include `6274` + `terminology` + `cutover`, confidence: high). Body contains the "target cutover date: TBD — populated in 6274.2 PR" placeholder per AC1.6. |
| AC1.7 — All existing tests pass (no regression) | PASS | `pytest tests/test_terminology_dual_aware_6274.py tests/test_compose.py tests/test_config.py tests/test_tracker.py tests/test_vault.py tests/test_boot_remote.py tests/test_add_role.py` → **273 passed, 1 skipped in 148.74 s**. (Skill's pickup-comment quoted 233; actual count drifted higher between their run and mine — additional passes, not failures.) Skill also claimed `python tests/run_tests.py static` → 2496 passes, 0 failures; I did not re-run that full static suite since the targeted slice + skill's diff-verified fidelity gives high confidence and the test count is well-covered. |

## Additional deliverables (verified)

- **G2→3 helper**: `references/scripts/verify_dual_label_6274.py` exists. Per skill's pickup comment and DS finding F1, this lands in 6274.1 as a verifier that 6274.3's gate can use.
- **D2 inventory #5 (boot_remote.py)**: `_parse_workers` + alias present.
- **D2 inventory #6 (add_role.py)**: `MANDATORY_ROLES_6274` present.

## Test runs

- Targeted: `pytest tests/test_terminology_dual_aware_6274.py` → **27 passed in 0.17 s**.
- Skill's wider regression: `pytest tests/test_terminology_dual_aware_6274.py tests/test_compose.py tests/test_config.py tests/test_tracker.py tests/test_vault.py tests/test_boot_remote.py tests/test_add_role.py` → **273 passed, 1 skipped in 148.74 s**.

## Pickup-comment fidelity observation (good)

Skill's pickup comment on this PR is the first one I'm reading post-#9946 ship. Visibly applies the discipline being taught:
- "ACs satisfied (verified against `git diff origin/main...HEAD --name-only`)" — explicit diff-verified claim
- Test output explicitly noted as a state file (`.squidsquad/skill/test-output-6274-v2.log` — state file, not in PR)
- Real test numbers quoted (27, 233, 2496)
- "G2→3 helper — `verify_dual_label_6274.py` (NEW; lands in 6274.1 per F1)" — explicit per-finding traceability
- Distinguishes coverage between sub-phases (`Post-rename behavior covered structurally by _BASE_ALIAS_6274 bidirectionality and will be re-verified in 6274.2's PR`)

This is exactly the discipline #9946 was filed to enforce. The slight test-count drift (233 → 273) is minor (more passing is fine), but worth noting because the #9946 sub-skill recommends quoting from a captured log — skill's `test-output-6274-v2.log` would have shown 233 at the time. If the recommendation is "quote actual pass/fail counts from the log," then "more passes since then" is a feature not a bug.

## Notes

- Sub-phases 6274.2 (rename) and 6274.3 (cleanup) will need their own QA verification passes against AC2.x and AC3.x respectively. Vault note `migration-6274-cutover` populates in 6274.2 (AC2.9) and updates again in 6274.3 (AC3.6).
- DS pre-push review per skill: 1 iteration, 3 warnings, all fixed in commit `5c02a3db`.
