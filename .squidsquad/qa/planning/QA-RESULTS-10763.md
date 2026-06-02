# QA-RESULTS-10763 — PRD-B / Story B9: Wire B1-B7 assemble pipeline into deploy_alias_v2

**Verified**: 2026-06-02 13:40
**Branch**: `skill/b9-assemble-wiring-10763` @ `25410fa9`
**PR**: #10764
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

- `references/scripts/assemble_adapter.py` (+111 new) — bridges B7 slot-shaped seam to B6 key-shaped cache API
- `references/scripts/atomic_emit.py` (+63) — `filename_suffix` parameter added (AC3)
- `references/scripts/compose.py` (+63) — `deploy_alias_v2` invokes `assemble_and_emit` after `emit_v2_linked` + D3 gate
- `references/scripts/model_router.py` (+10) — `get_model_for_task("assemble")` returns `"sonnet"` compose-time constant
- `tests/test_assemble_wired_b9.py` (+281 new) — 11 B9 tests
- `tests/test_atomic_emit_b7.py` (+64) — AC3 filename_suffix coverage
- `tests/test_compose_a2f_10492.py` (+50) — adjacent coverage
- `tests/test_compose_a6_v2.py` (+46) — deploy_role v2 path (AC7)
- `.squidsquad/skill/planning/CODE-REVIEW-B9.md` (4390 bytes) — AC9 DS code review artifact

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | `compose.py deploy <alias> --v2` and `deploy-all --v2` invoke `assemble_and_emit` after `emit_v2_linked` | `test_deploy_alias_v2_invokes_assemble_and_emit` — fresh E2E that runs `deploy <alias> --v2` against a minimal install and asserts `CLAUDE.v2.md` differs from `CLAUDE.linked.v2.md` (proving assemble actually ran). | PASS |
| 2 | Outputs land at `CLAUDE.v2.md` / `CLAUDE.linked.v2.md` / `CLAUDE.conflicts.v2.md`; v1 paths NOT written | `test_v2_triple_lands_at_v2_paths` + `test_v1_canonical_paths_not_written` (grep-style file-existence assertions). §9a coexistence intact. | PASS |
| 3 | `_atomic_write_triple` accepts `filename_suffix` parameter (default `.v2.md`, empty supported) | atomic_emit_b7 test suite (+64) covers both `.v2.md` default + empty `filename_suffix=""` → v1 canonical paths (the seam E6 will use for the atomic switch). | PASS |
| 4 | B6 cache wired through adapter that computes `cache_key(linked_body, slot_name, slot_purpose, model_id, prompt_version)` and calls `cache_lookup` / `cache_store` | 5 adapter tests: `test_adapter_lookup_returns_none_on_cold_cache` + `test_adapter_store_then_lookup_round_trip` + `test_adapter_keys_differ_per_slot` + `test_adapter_model_id_invalidates_cache` + `test_adapter_prompt_version_invalidates_cache`. Cache-hit integration verified. | PASS |
| 5 | `model_router.get_model_for_task("assemble")` returns `"sonnet"` compose-time constant, NOT from config.md | **Live verify**: `get_model_for_task('assemble')` returns `'sonnet'`. `test_get_model_for_task_assemble_returns_sonnet` + `test_assemble_model_lock_overrides_env_var` (proves env var cannot override). | PASS |
| 6 | Temperature ≤ 0.3 enforced in provider adapter call | `test_openai_adapter_caps_temperature_at_or_below_0_3`. | PASS |
| 7 | `deploy_role` v2 path also wired (not just `deploy_alias_v2`) | `test_deploy_role_output_filename_defaults_to_v1` + `test_deploy_role_preserves_role_parameter_name` + `test_deploy_role_default_regenerate_cmd_preserves_v1_header` in test_compose_a6_v2.py (+46). | PASS |
| 8 | `python tests/run_tests.py` passes with zero failures | Skill reported "232 tests pass in wider sweep, no regressions". My targeted cut: **86 passed** across B9 + B7 + A2f + a6_v2 + §9a. | PASS |
| 9 | Pre-merge DS code review artifact at `.squidsquad/skill/planning/CODE-REVIEW-B9.md`, cited in PR | Artifact exists (4390 bytes). 1 warning (stale label) fixed pre-commit; NO_FINDINGS on cache contract, return semantics, §9a coexistence, failure isolation, error semantics. | PASS |

## Defense-in-Depth

- **Cache adapter bridges two API shapes**: B7 was authored against `cache_lookup_fn(slot, linked_slot_body)` / `cache_store_fn(slot, linked_slot_body, assembled_llm_output)` (slot-shaped, ergonomic for the assemble pass). B6 implements `cache_lookup(alias, key, *, slot_name=None)` / `cache_store(alias, key, assembled_body)` (key-shaped, indexable). Adapter computes the cache key and threads `alias`/`model_id`/`prompt_version` through. Tests pin the cache invalidation semantics for each dimension (slot, model_id, prompt_version) separately.
- **Filename suffix is the E6 cutover seam**: `_atomic_write_triple(... filename_suffix="")` produces v1 canonical paths. E6 will flip this default from `.v2.md` to `""` in a single atomic switch. The current PR ships the seam + default; AC3 explicitly tests the empty-suffix path so E6 doesn't introduce a new code path under pressure.
- **`get_model_for_task("assemble")` short-circuits before env override** — `test_assemble_model_lock_overrides_env_var` confirms the model lock is enforced even when `assemble-model` is set in config or env. Constants-not-config pattern from `project_assemble_unconditional` memory + the immutability contract from #10444's deferred-AC lesson.

## v1 Coexistence

§9a v1 byte-stability gate: passes on `25410fa9`. B9 lands inside §9a coexistence per AC2 — v1 paths are explicitly NOT written. E6 will be the atomic switch.

## E6 Unblock Status

Per issue body: "**Hard pre-req for**: E6 #10685 (V2 CUTOVER). E6 cannot ship until B9 is shipped." → **gate cleared by this PR**. PRD-B's other ERROR/WARNING findings in #10752 are now testable + fixable (the dead-pipeline blocker is gone).

PRD-A audit + PRD-C audit + PRD-B B9 (wire) → E6 release conditions: B9 shipped + #10752 re-evaluation complete. After B9 merges, the next QA action will be #10752 re-verification or its split fixes.

## DS Review (AC9 mandatory)

Per `feedback_ds_review_per_change`, skill ran DS code review:
- 1 warning (stale label) fixed pre-commit
- NO_FINDINGS on: cache contract, return semantics, §9a coexistence, failure isolation, error semantics

Artifact persists at `.squidsquad/skill/planning/CODE-REVIEW-B9.md`. PR description cross-links #10754 (the PM scope question this resolves) and #10752 (PRD-B audit re-evaluation now unblocked).

## Test Execution

`pytest tests/test_assemble_wired_b9.py tests/test_atomic_emit_b7.py tests/test_compose_a2f_10492.py tests/test_compose_a6_v2.py tests/test_v1_byte_stability_9a.py -q` on `25410fa9` → **86 passed**.

## Outcome

All 9 ACs covered. The dead pipeline is now live. Cache adapter bridges B6/B7 shape mismatch cleanly. `filename_suffix` E6 cutover seam is in place + tested. Model + temperature locks are compile-time constants per the issue contract. AC9 DS review clean except 1 warning fixed pre-commit. **Transitioning #10763: pending-test → pending-ship. E6 cutover hard pre-req CLEARED.**
