# Working State

- **Task**: #6274 — sub-phase 6274.1 (terminology dual-aware shim)
- **Status**: in-progress
- **Branch**: squidsquad/task/6274 (pushed; no PR yet)
- **Started**: 2026-05-23 03:08
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## Completed (sub-phase 6274.1)

- [x] **AC1.1** (commit `e4d21b37`) — `compose._list_known_role_identities()` dual set via `_DUAL_AWARE_IDENTITIES_6274` frozenset.
- [x] **AC1.2** (commit `eef5b49b`) — `compose._resolve_variant` accepts `worker-skill`/`dev-skill` (and qa/verifier) via `_BASE_ALIAS_6274` bidirectional table. F3 contract: return tracks on-disk state. Also extended `_get_entry_file_for_role` with alias-to-disk normalization (necessary side fix — without it AC1.1's identity-widening broke pre-rename compose for `worker`).
- [x] **AC1.3** (commit `eef5b49b`) — `config.get_field("workers")` reads `Workers:` then falls back to `Dev Agents:` with stderr deprecation warning. New `_DUAL_AWARE_CONFIG_FIELDS_6274` table; both FIELD_MAP rows coexist during window.

Regression: 226 tests pass (test_terminology_dual_aware_6274 + test_compose + test_compose_9588 + test_config + test_config_schema).

## Remaining for sub-phase 6274.1

- [ ] **AC1.4** — `tracker.py.create_*` dual-tag (`role:worker` + `role:dev`); `--role` shim accepts both `qa-lead`/`verifier-lead` etc. (per D11). Tests.
- [ ] **AC1.5** — `references/scripts/migrate_labels_6274.py` (one-shot, idempotent, `--dry-run`).
- [ ] **AC1.6** — Vault note `migration-6274-cutover` placeholder.
- [ ] **AC1.7** — full regression suite green.
- [ ] G2→3 script `references/scripts/verify_dual_label_6274.py`.
- [ ] Self-verify + pickup-comment fidelity check + external review.
- [ ] Open PR for sub-phase 6274.1.
- [ ] Transition in-progress → pending-test.

## Next-cycle plan

AC1.4 is the biggest remaining piece (tracker.py touches both `create_*` and `--role` argparse). Estimate: AC1.4 alone next cycle. Then AC1.5 (script). Then AC1.6 + AC1.7 + verify_dual_label_6274.py + PR + review.

## Key Decisions

- **Hold PR until sub-phase fully complete.**
- **Bidirectional alias table** (`_BASE_ALIAS_6274`) — handles both pre-rename and post-rename in one lookup.
- **Test rewrites land in same commit as the implementation** (D10).
- **`_get_entry_file_for_role` shim was a discovered necessity** — AC1.1's identity widening made `worker` resolve to itself, but the on-disk template lives at `roles/dev/`. Without the alias-to-disk fallback in `_get_entry_file_for_role`, compose would fail for `worker` pre-rename. Documented in the commit message.
