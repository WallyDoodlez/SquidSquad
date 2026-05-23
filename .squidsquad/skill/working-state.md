# Working State

- **Task**: #6274 — sub-phase 6274.1 (terminology dual-aware shim)
- **Status**: in-progress
- **Branch**: squidsquad/task/6274 (pushed; no PR yet — sub-phase incomplete)
- **Started**: 2026-05-23 03:08
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## Context

25 ACs across 3 PR-merged sub-phases (D9). Multi-cycle task by design. This cycle committed AC1.1 only; 6 ACs + 2 helper scripts remain for sub-phase 6274.1.

CONTEXT-6274.md (229 lines, D1–D11 locks) is the contract — read in full. RESEARCH and DS-review deferred until needed.

## Completed Steps

- [x] **AC1.1** (commit `e4d21b37` on `squidsquad/task/6274`) — `compose._list_known_role_identities()` returns dual set `{worker, verifier, pm, dm, dev, qa}`. Added `_DUAL_AWARE_IDENTITIES_6274` frozenset, union with on-disk set. Updated `test_compose.py::test_missing_roles_dir`. New `tests/test_terminology_dual_aware_6274.py` (4 tests). Registered in `run_tests.py`. Regression: 94 tests pass.

## Remaining for sub-phase 6274.1

- [ ] **AC1.2** — `compose._resolve_variant` accepts both `worker-skill` and `dev-skill` (F3: input independent of disk state).
- [ ] **AC1.3** — `config.py.get_field("workers")` reads both `Workers:` and `Dev Agents:`; deprecation warning.
- [ ] **AC1.4** — `tracker.py.create_*` dual-tag + `--role` shim per D11.
- [ ] **AC1.5** — `references/scripts/migrate_labels_6274.py` (idempotent, `--dry-run`).
- [ ] **AC1.6** — Vault note `migration-6274-cutover` placeholder.
- [ ] **AC1.7** — `python tests/run_tests.py` exits 0.
- [ ] G2→3 script `references/scripts/verify_dual_label_6274.py` (lands in 6274.1 per F1 resolution).
- [ ] Self-verify + pickup-comment fidelity check + external review.
- [ ] Open PR for sub-phase 6274.1.
- [ ] Transition in-progress → pending-test.

## Cadence Estimate

- Next cycle: AC1.2 + AC1.3 + AC1.4 (all surgical Python edits in known files).
- Cycle after: AC1.5 + AC1.6 + verify_dual_label script.
- Cycle after that: full regression + external review + PR + transition.

## Key Decisions

- **Hold PR until sub-phase 6274.1 is fully complete.** Partial PRs would mislead QA. Branch is pushed for durability; PR creation deferred.
- **One AC per cycle for AC1.1 (heavy context overhead from reading CONTEXT-6274.md); 2–3 ACs per cycle for AC1.2+** since the context is now loaded.
- **Dual-aware constant as `frozenset`** — immutable cross-cycle invariant.
