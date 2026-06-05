# QA-RESULTS-11050 — Prune dead assemble pipeline + sonnet model_router branch

**Verified at**: 2026-06-05 cycle 914
**PR**: #11064 (squidsquad/skill/11050-prune-assemble-pipeline @ c5bc94a99)
**Scope**: 5 ACs as stated in issue body. Net delta -3757 LOC across 18 files (6 module deletions, 7 test-file deletions, 1 test rewrite, 3 in-place edits, 1 runner edit).

## AC walk

- **AC1 — `compose.py deploy-all` succeeds from clean shell** — PASS
  - `python references/scripts/compose.py deploy-all` exits 0 and emits sizes:
    `dm: 1568, pm: 2196, qa: 1789, skill: 1964, .local-config: 4 agents`. Byte-identical to skill's claim and #11011's measurement.
- **AC2 — no `from (assemble_pass|assemble_verifier|conflict_detector|conflict_resolver|assemble_adapter|assemble_cache) import` in `references/scripts/*.py`** — PASS
  - Grep returned zero matches.
- **AC3 — `model_router.get_model_for_task("assemble")` is no longer a special case** — PASS
  - `get_model_for_task("assemble")` returns `"claude"` (fallthrough to config-routing default-model, no `task_type == "assemble"` branch).
- **AC4 — non-assemble suites continue to pass** — PASS (with one orthogonal pre-existing failure)
  - 15-suite compose-area sweep (test_atomic_emit_b7, test_compose, test_compose_10981/_a2f/_a6/_capability/_check_a45/_deploy_role/_freshness/_strip_frontmatter, test_a3_golden_link_stage, test_d2_link_stage_references, test_l4_compose_dryrun_c5, test_link_stage_validator, test_v2_link_stage) → **254/255 PASS in 3.63s**.
  - Sole failure: `test_a3_golden_link_stage::test_corrupted_l4_aborts_with_parse_error` — pre-existing, filed by skill as **#11066** (stale post-#10987 prose-H3 change). Orthogonal to this prune.
  - Note: `test_installer_wiring::test_every_listed_file_exists_on_disk` also fails on this branch — but that is the **#11042** installer-files staleness being fixed in parallel on PR #11048 (verified to pending-ship in cycles 910/913). Not introduced by #11050.
- **AC5 — `atomic_emit.py` module docstring reflects verbatim-only contract** — PASS
  - Docstring opens with: `"""Atomic emit of the verbatim §4.6 triple (post-#11011 / #11050).` and explains the assemble pipeline retirement (`8da22e25` expanded `_VERBATIM_SLOTS`, #11050 pruned the dead modules).

## Carve-outs check (NOT in scope)

- `_VERBATIM_SLOTS` constant — still present in atomic_emit.py ✓
- Verbatim path in `assemble_and_emit` — still present ✓
- `_split_linked_into_slots`, `_build_claude_md`, `_atomic_write_triple` — still present ✓
- Catalog gate / D1 parser — untouched ✓

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.

All 5 ACs observably satisfied. No new test failures introduced by the prune; the two failures observed across the wider sweep are both pre-existing and tracked under separate issues (#11066, #11042). Carve-outs preserved as specified.
