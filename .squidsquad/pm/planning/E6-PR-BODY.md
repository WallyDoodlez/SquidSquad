## Summary

E6 V2 CUTOVER per #10685. Atomic switch from v1 (single-stage `compose_role`) to v2 (two-stage: `emit_v2_linked` + `assemble_and_emit` with LLM polish). All v1 paths retired. v2 is now the default and only path.

**Net: 72 files changed, +2,669 / −12,716 = −10,047 lines.**

Closes #10685
Closes #10677 (D6 bundled — `event-driven:` config field cleanup + `_get_wake_mode` retirement)
Closes #10981 (deploy_alias_v2 token-leak fix bundled — 3 leak classes resolved)
Closes #10987 (l4_parser H3 sub-heading + R4 implicit-append exemption bundled)

Related: #10998 fixed separately on `main` (commit `853187b6`) — pm.md restructured to use prose H3 sub-headings under Instructions, unblocking `compose.py deploy-all pm` post-cutover.

## Phase ledger

- **Phase 1** — manifest unification (`includes-v2.yml` → `includes.yml`)
- **Phase 2** — drop `--v2` CLI flag; v2 default
- **Phase 3a/3b/3b.2** — retire v1 coexistence test gates
- **Phase 3c step A** — `deploy_role_v2` wedge
- **Phase 3c step B** — wizard.py migrated to `deploy_role_v2`
- **Phase 3c.5** — retire `compose.py all` + `agent-instructions.md`
- **Phase 3c.6** — 5 product-invariant test files migrated/retired
- **Phase 3d.1-3d.5** — pure-deletion arc: `compose_all`, retire-marked test bodies, `deploy --check` chain, `deploy_role`, `compose_role` chain
- **Phase 3e** — `catalog_drift.py` cleanup
- **Phase 4** — `filename_suffix` default flip to `""`
- **Phase 5 / D6** — `event-driven:` config field cleanup + `_get_wake_mode` retirement + `boot-bootstrap.md` doc refresh
- **Phase 6** — PRD docs status `draft → shipped`
- **Phase 7** — N/A per pure-deletion-skips-DS rule; per-commit DS done where applicable
- **Post-readiness fixes** — #10981 token-leak resolution (`_resolve_includes_v2` new + wire `_substitute_placeholders` + `_inject_role_roster` into both deploy paths); #10987 l4_parser fixes

## Verification

- **v1 symbol audit**: zero production-code or test-invocation references to retired symbols (`compose_role`, `deploy_role`, `_load_manifest`, `_resolve_includes`, `_resolve_includes_with_manifest`, `_assemble_claude`, `_resolve_capability`, `_resolve_runtime`, `_get_wake_mode` in compose, `check_role` in compose, `_compose_role_to_string`, `_diff_compose_output`). Remaining hits are doc-comment historical references — harmless.
- **Touched-area smoke**: 430+ pass across compose / atomic-emit / freshness / link-stage / v2-link / CLI-check / staged-l4 / wizard / cycle-post / statusline / 9745-canonical-helper / deploy_role_v2 / v2 helpers.
- **End-to-end deploy_alias_v2**: verified clean output across all 4 roles after #10981 fix (PM audit cycle 2121).
- **D6 (#10677) ACs**: all 5 covered.

## Post-squash actions

Operator follows the runbook at `.squidsquad/pm/planning/E6-POST-SQUASH-RUNBOOK.md` — pull main in 4 clones, `compose.py deploy-all`, restart agents, run `tests/run_tests.py`, surgical `.harness-state.json` repair (closes #10954), close out bookkeeping, document post-E6 queue.

## Test plan

- [x] Compose pipeline smoke (430+ tests pass)
- [x] v1 symbol audit (zero live refs)
- [x] End-to-end `deploy_alias_v2` empirical verification (PM cycle 2121)
- [x] QA verification on cutover branch (verifier cycle 638 for #10981)
- [ ] Post-merge: `python references/scripts/compose.py deploy-all` clean across all 4 roles
- [ ] Post-merge: `python tests/run_tests.py` clean
- [ ] Post-merge: agents restart and pick up new (smaller) composed CLAUDE.md
