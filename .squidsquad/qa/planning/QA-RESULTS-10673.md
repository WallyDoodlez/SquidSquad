# QA-RESULTS-10673 — PRD-D / Story D2: v2 link-stage emits → run sub-skill references (not bodies)

**Verified**: 2026-06-02 02:30
**Branch**: `squidsquad/task/10673` @ `a5c7b23f` (feature + main-merge + review-fix)
**PR**: #10691
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

- `references/scripts/v2_link_stage.py` (+49) — `_SUB_SKILLS_PATH_PREFIX` + `_is_sub_skill_body_in_instructions(slot, posix_path)` helper. Filter applied symmetrically in `_parse_all_applicable_sources` (emission) + `collect_sources_for_validation` (validator), so they see identical record sets.
- `tests/test_d2_link_stage_references.py` (+223 new) — 17 tests across three layers: synthetic fixture parity, live-tree invariants (no `<!-- sub-skill: -->` markers + refs present + Boot block not inlined), size invariants (per-role + average).
- `tests/run_tests.py` (+1) — STATIC_TEST_MODULES registration.

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | v2 link-stage emits `→ run sub-skill: <name>` (TRD §6.2 grammar) instead of inlining `<!-- sub-skill: <name> -->` bodies | `test_subskill_instructions_body_is_filtered_from_v2_output` + `test_live_v2_emits_sub_skill_references` (per-role parametrize). Live live-tree per-role check: pm=16, dm=14, verifier=12, worker=13 refs present. | PASS |
| 2 | Zero inlined sub-skill bodies in v2 composed `CLAUDE.md`; Boot block extracted | `test_live_v2_has_no_inlined_sub_skill_markers` (parametrized per mandatory role). Live confirm: 0 `<!-- sub-skill:` markers across all 4 roles. `test_live_v2_boot_block_not_inlined_when_role_uses_boot_bootstrap` confirms `## Boot — Mode Detection` not inlined for any role; boot-bootstrap is referenced. | PASS |
| 3 | Avg v2 composed `CLAUDE.md` ≤ 30% the byte size of v1 | `test_v2_size_is_at_most_30pct_of_v1` (per-role parametrize) + `test_v2_average_size_at_most_30pct_of_v1`. **Live measure on a5c7b23f**: pm=22.3%, dm=28.5%, verifier=26.2%, worker=22.7% → **avg 24.9%** (well below 30% target; PRD §10 criterion 10 met). | PASS |
| 4 | v1 compose path untouched — `compose.py deploy <alias>` produces byte-identical v1 output | §9a regression gate: `pytest tests/test_v1_byte_stability_9a.py -q` → **5/5 passed** on `a5c7b23f`. Diff inspection of `compose.py`: only `v2_link_stage.py` modified; v1 code path (`compose.deploy_role` / `_resolve_includes`) untouched. | PASS |
| 5 | v2 output written to distinct path (`CLAUDE.v2.md`) per §9a coexistence | `deploy_alias_v2` continues to write `CLAUDE.linked.v2.md` (unchanged from prior PRD-A). No v1 output path collision. | PASS |
| 6 | A3 golden-file tests re-run against v2 output assert byte-stability | `pytest tests/test_a3_golden_link_stage.py -q` → **all green** on `a5c7b23f`. Goldens for pm + worker-fe re-built and matched. | PASS |

## Defense-in-Depth

- **Filter symmetry between emitter and validator** (`_is_sub_skill_body_in_instructions` called in both paths) — prevents drift where the validator sees one record set and the emitter sees another. Locked by `test_collect_sources_for_validation_drops_sub_skill_instructions`.
- **Slot-keyed filter, not path-keyed** — predicate is `(slot == "instructions") AND path-under-sub-skills/`. `test_subskill_filter_applies_only_to_instructions_slot` guards against an over-broad future tightening that would drop ALL sub-skill paths regardless of slot (today the live tree has zero non-instructions-slot files under `references/sub-skills/`, but the filter remains future-safe).
- **`_NO_L4` sentinel** (`__d2_no_l4_sentinel__/nonexistent.md`) added by review-fix commit `a5c7b23f` — eliminates a per-install L4 confounder in size measurements. v1 side compared against `target_root=tempdir` so both measure the same "no L4 applied" baseline. Comparison is symmetric.
- **Live-repo invariants parametrized across all mandatory role-classes** — single broken role-class fails its own test rather than slipping through an averaging artifact.

## v1 Coexistence

§9a byte-stability gate **5/5 passed** on `a5c7b23f`. v1 compose code path (`compose.deploy_role`, `_resolve_includes`) verified untouched in the diff. Per PRD AC: "v1 compose path untouched" — confirmed.

## External Code Review

Skill ran parallel DeepSeek + Claude Sonnet review (per `feedback_ds_review_per_change` — D2 is high-risk for v1 coexistence). 6 findings: 3 fixed in `a5c7b23f` (docstring + `_NO_L4` sentinel), 3 justified-ignore. Dispositions documented on PR.

## Test Execution

- `pytest tests/test_d2_link_stage_references.py tests/test_v1_byte_stability_9a.py tests/test_a3_golden_link_stage.py tests/test_catalog_parser_d1.py -q` → **56 passed + 1 xfailed** on `a5c7b23f`.
- `python tests/run_tests.py static` (canonical CI gate using STATIC_TEST_MODULES) → **exit 0** on `a5c7b23f`. Matches skill's "2585 passing, 0 failures" claim.
- Live v2 compose ratios match skill's claim exactly (pm=22.3% / dm=28.5% / verifier=26.2% / worker=22.7% / avg=24.9%).

## Outcome

All 6 ACs covered with exhaustive defense-in-depth (filter symmetry, slot-keyed predicate, parametrized live-tree invariants, `_NO_L4` sentinel for symmetric measurement). Skill correctly applied `feedback_ds_review_per_change` for this high-risk story. D2 — the biggest pivot in PRD-D — lands cleanly with zero v1 coexistence regression. **Transitioning #10673: pending-test → pending-ship.**
