# Working State

- **Task**: #6274 — sub-phase 6274.1 (terminology dual-aware shim)
- **Status**: in-progress
- **Branch**: squidsquad/task/6274 (pushed; no PR yet)
- **Started**: 2026-05-23 03:08
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## Completed (sub-phase 6274.1)

- [x] **AC1.1** (commit `e4d21b37`) — `compose._list_known_role_identities()` dual set.
- [x] **AC1.2** (commit `eef5b49b`) — `compose._resolve_variant` + `_get_entry_file_for_role` dual-aware via `_BASE_ALIAS_6274`.
- [x] **AC1.3** (commit `eef5b49b`) — `config.get_field("workers")` with `Dev Agents:` fallback + deprecation warning.
- [x] **AC1.4** (commit `f110e564`) — tracker dual-tag (`_build_dual_role_labels_6274`) + `--role` suffix shim per D11. New form (`verifier-lead`/`worker-lead`) accepted silently; old form (`qa-lead`/`dev-lead`) accepted with deprecation warning. Untouched: `pm-lead`, `dm-lead`, `skill-lead`, `ios-lead`, etc.

Regression: 275 tests pass.

## Remaining

- [ ] **AC1.5** — `references/scripts/migrate_labels_6274.py` (one-shot, idempotent, `--dry-run`). Walks OPEN issues with `role:dev`/`role:qa`, adds the new label alongside.
- [ ] **AC1.6** — Vault placeholder note `.squidsquad/vault/galaxy/migration-6274-cutover.md`.
- [ ] **AC1.7** — Full `python tests/run_tests.py` exit 0.
- [ ] G2→3 script `references/scripts/verify_dual_label_6274.py`.
- [ ] Self-verify + pickup-comment fidelity check + external review.
- [ ] Open PR for sub-phase 6274.1.
- [ ] Transition in-progress → pending-test.

## Next-cycle plan

AC1.5 (migrate script) + AC1.6 (vault note) + verify_dual_label_6274.py — all small. Then AC1.7 (full regression) + external review + PR + transition.

## Key Decisions

- **D11 suffix shim is bidirectional but asymmetric in warning**: new forms silent, old forms warn. Operators see migration pressure; scripted callers still work.
- **`_build_dual_role_labels_6274` produces comma-separated labels** — fits cleanly into the existing labels string passed to `gh issue create --label`.
- **Variant prefixes excluded from alias table** (skill, ios, android, fullstack, web) per Out-of-Scope.
