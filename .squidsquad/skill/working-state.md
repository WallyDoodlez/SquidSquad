# Working State

- **Task**: #10685 (E6 V2 CUTOVER)
- **Status**: in-progress (multi-phase on branch skill/e6-v2-cutover-10685)
- **Started**: 2026-06-02
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## Completed Steps

- Cycle 1534 fixup (DS-10685-phase2): addressed all 4 DS findings on commit `559a861c` as a fixup commit `eb3ab95e`. F1 (error) — `--check` vs `deploy` file asymmetry between Phase 2 and Phase 4; added explicit WARNING on both `deploy <role> --check` and `deploy-all --check` since clean fix is the Phase-4 suffix flip. F2 (error) — `test_main_deploy_all_v2_iterates_registry` was missing stubs for `_collect_all_roles`/`_check_mandatory_roles`/`generate_local_config`/`Path.write_text`, leaking real `.squidsquad/.local-config` writes (file is gitignored so commit was not polluted). F3 (warning) — deleted tautological `test_main_deploy_v2_returns_without_calling_event_contracts` (validated retired invariant). F4 (warning) — renamed `test_main_strips_v2_flag_and_routes_v1_without_it` → `..._routes_to_v2`, dropped stale section header + dead `deploy_role` / `derive_and_write_event_contracts` monkeypatches. Verification: 52 passed, 1 skipped.
- Cycle 1534 (Phase 2 — drop `--v2` flag): recovered Phase 2 work-in-progress left uncommitted by the previous skill session (compose.py + 2 test files mid-edit; the user-visible 996-line agent-instructions.md "rewrite" turned out to be test-side-effect drift from `test_cli_check_on_unrecognized_command_emits_warning` running `compose all` in subprocess without monkeypatching `OUTPUT_FILE` — reverted, see watch list). Updated `compose.py` `main()` to silently strip `--v2` from argv; retired the `--check + --v2` reserved-error path; collapsed the v1 `deploy_role` + `derive_and_write_event_contracts` side effect in the `deploy` cmd (route unconditionally through `deploy_alias_v2`); collapsed the `if v2_mode:` branch in the `deploy-all` cmd (iterate `parse_aliases_registry()` always; install topology bookkeeping runs after as a harness-wiring concern). Updated tests/test_compose_a6_v2.py (header assertions drop `--v2`; bare-deploy test renamed v1→v2 default; legacy "warn unsupported-cmd" → "accept silently"). Updated tests/test_compose_check_a4_10388.py (retire `--check + --v2` case). Updated tests/test_compose_a2f_10492.py (post-cutover header assertion). Phase 1 followup: deleted stale `test_manifest_v2_d5` entry from tests/run_tests.py (test file was deleted in Phase 1, runner reference left behind). Single commit `559a861c`. 53 / 54 affected tests pass; 1 skipped. DS review for `10685-phase2` launched in background (job `bc6ml5j38`).
- Cycle 1533 (Phase 1 — manifest unification): renamed per-role `includes-v2.yml` → `includes.yml` for all 4 roles (pm/dm/verifier/worker); deleted v1 `includes.yml` (the polling manifest) and `includes-events.yml` (the events split); pointed `compose.py`'s `_V2_MANIFEST_FILENAME` constant at the new canonical name; deleted `tests/test_manifest_v2_d5.py` (the v1/v2 coexistence test file) and `TestLoadManifestSelectsByWakeMode` class in `tests/test_compose.py` (both gate behavior being retired by the cutover). Two commits on branch: `01fcc923` (Phase 1) + `0160f296` (DS-10685-phase1 F1-F4 doc fixup — `_load_manifest_v2`/`_load_manifest_v2_from_file` docstrings + 4 manifest header comments rewritten to describe post-E6 state; F5 was false-positive). 145 / 146 affected tests pass; 1 pre-existing fail (`test_event_driven_workflow_has_no_frontmatter`) slated for Phase 5 D6 retirement.
- Cycle 1532: QUIET — DS-audit umbrella fully drained (A/B/C all shipped). All E6 cutover pre-reqs met. PM applied hard hold on #10685 (removed role:skill, added blocked:audit-review + blocked:pm-coordination) until pre-reqs were met. Posted unblock-notification comment on #10685; awaiting PM re-label.
- Cycle 1531: PRD-B audit umbrella CLOSED on PR #10765.
- Cycle 1530: PRD-B B9 (#10763) shipped on PR #10764.
- Cycle 1529: QUIET.
- Cycle 1528: QUIET; filed #10762 (low) — compose_freshness COMPOSE_INPUT_GLOBS misses docs/sub-skill-catalog.md.
- Cycle 1527: PRD-E E4 (#10683) — squidsquad_cli check operator CLI. PR #10761 pending-test.
- Cycle 1526: PRD-E E5 (#10684) — wire freshness check into harness restart-safety. PR #10760 pending-test.
- Cycle 1525: PRD-E E1 (#10680) — harness boot-time freshness check. PR #10759 pending-test.
- Cycle 1524: PRD-C audit (#10753). PR #10758 pending-test.
- Cycle 1523: PRD-A audit (#10751). PR #10757 pending-test.
- Cycle 1522: Bug fix #10743 — catalog parser. PR #10749 pending-test.
- Cycle 1521: PRD-D/D7 (#10678). PR #10748 pending-ship.
- Cycle 1520: PRD-D/D3 (#10674). PR #10747 SHIPPED.
- Cycle 1519: Second-pass merge of D2 + E2 + `.gitattributes` `merge=ours` for `.backlog-cache`.

## Remaining Steps on E6 Branch (skill/e6-v2-cutover-10685)

- Phase 3: delete v1 `deploy_role`, v1 `_load_manifest`, v1 hint emit, v1 `_resolve_includes` manifest-split logic. Estimated large scope — most v1 code paths in compose.py go away.
- Phase 4: flip `atomic_emit._atomic_write_triple` `filename_suffix` default from `.v2.md` to `""` so v2 outputs land at v1 paths.
- Phase 5: D6 (#10677) work — remove `event-driven:` field from config.md template; config.py silently ignores the field for backward compat.
- Phase 6: update PRD docs status `draft` → `shipped` across compose-link-stage, compose-assemble-stage, compose-l4-customization, compose-catalog-and-wake-mode, compose-freshness.
- Phase 7: AC10 cumulative DS review pre-merge (or rely on per-phase DS reviews).
- Phase 8: open single squash-PR with logical commit groupings; PM/QA gate; DM merge.

## Pre-existing test failures to track (additive — confirmed pre-existing on branch HEAD via stash test)

- `test_compose.py::TestEventDrivenWorkflowLocation::test_event_driven_workflow_has_no_frontmatter` — retire in Phase 5 (D6) when event-mode boot path folds down.
- `test_l4_parser.py::test_v1_compose_untouched` — guards "compose.py has not imported l4_parser yet"; contradicted by post-A2 compose.py, retired by E6 cutover. Retire in Phase 3 with v1 path deletion.
- `test_source_frontmatter.py::test_v1_compose_untouched` — same shape, guards `source_frontmatter` import. Retire in Phase 3.
- `test_feat_6126_harness_merge.py::TestEventReactionsTable::test_compose_completed_in_table` — missing `references/sub-skills/common/event-reactions.md` (pre-existing infra gap); investigate separately, not E6-scope.
- `test_feat_9588_lazy_load_bootstrap.py::test_tc_14_compose_runtime_read_frozenset_present` — `RUNTIME_READ_FRAGMENTS` missing `roles/dev/ralph-loop-overview` (pre-existing); investigate separately, not E6-scope.
- `test_feat_10681_compose_checksum.py` — ImportError on `HarnessState` (collection failure, pre-existing); investigate separately, not E6-scope.

## Watch list

- DS review #10685-phase2 (background task `bc6ml5j38`) — addressed in fixup commit `eb3ab95e` (this cycle). F1 has Phase-4 prerequisite (suffix flip): remove the cutover-window WARNING in compose.py `--check` blocks when Phase 4 lands.
- DS review #10685-phase1 (background task `b9dv1dqhd`) — already addressed in commit `0160f296`; confirm green.
- Test isolation bug: `test_cli_check_on_unrecognized_command_emits_warning` writes the real `references/agent-instructions.md` (subprocess `compose all` without `OUTPUT_FILE` monkeypatch). File improvement-scan issue next quiet cycle if not already filed.
- PR #10692 (E2), PR #10748 (D7) for QA/DM movement.
- All other audit/D/E PRs upstream.

## Key Decisions (latest only)

- **NEW: For multi-phase atomic squash PRs, commit-per-phase on the branch with DS review per commit; open PR only after final phase.** Cycle 1533 lesson. E6 is officially "AC5: single squash-PR with logical commit groupings" — but the work is too large for one cycle. Splitting into ~8 phases (manifest unify / CLI drop / v1 deletion / suffix flip / D6 / PRD docs / DS umbrella / PR open) keeps each cycle bounded AND keeps per-commit DS review (memory [[feedback-deepseek-review-per-commit]]) intact. The branch accumulates commits across cycles; the FINAL act is squash-PR. Recipe: when an atomic cutover spans many cycles, commit incrementally on the branch and open PR only at the end. Each commit gets its own DS review; the PR squashes them into one logical change for merge.
- **Distinguish "shipped-but-buggy" from "shipped-but-unwired" before fixing audit findings.** Cycle 1523 lesson. [[feedback-audit-pattern-shipped-unwired]].
- **When merge conflicts recur on transient state files, fix at .gitattributes layer.** Cycle 1519 lesson.
- **If the issue body names the harness as the actor, harness wiring is in-scope.** Cycle 1517 lesson.
- **Lazy-import optional runtime deps so unit tests pass without them installed.** Cycle 1516 lesson.
- **Two-sided union semantics for additive manifest unification.** Cycle 1515 lesson.
- **File pre-existing drift as separate issue; never let it block the gate that surfaced it.** Cycle 1514 lesson.
- **PRD-E pickup order: foundation first.** Cycle 1513 lesson.

- **Vault Writes This Cycle**: 0
