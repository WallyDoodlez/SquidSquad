# Working State

- **Task**: #11503 (high, in-progress, role:skill) — post-cutover test-debt: 23 static tests red since v0.44.0 cutover
- **Status**: Group C (4 possibly-real) DONE & committed; working Group A (stale-structure tests) next
- **Branch**: squidsquad/skill/post-cutover-cleanup (bundle branch per operator decision c-2026-06-12; even with origin/main). NOTE: upstream is misconfigured to origin/main — push must target origin/post-cutover-cleanup explicitly, NEVER main.
- **Updated**: 2026-06-13 01:24 (fresh boot; #11601 verified shipped/closed → cleared)

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible — defer until #11503 ships)

## #11503 — plan (front-loaded)
23 static tests quarantined in KNOWN_FAILURES (tests/run_tests.py) when the gate went dead at v0.44.0 cutover (#11394). Fix each, remove its KNOWN_FAILURES entry, gate re-includes it.
- **Group A** — stale tests asserting pre-v2/pre-rename/pre-cutover structure → update test to v2 reality. ~16 files.
- **Group B** — fixture drift: test_config_functions (SAMPLE_CONFIG missing FIELD_MAP entries). 1 file.
- **Group C** — possibly-real masked regressions (triage first). DONE (see below).

## #11503 — Group C: DONE (committed this cycle)
4 flags triaged:
- test_manifest_registry + test_feat328_coverage: REAL orphan — dm/manifest.yaml `any_of: [local_delivery]` referenced the deleted capabilities registry (removed as deadwood, INSTALLER-ARCH §8.3, full teardown #11505). Fix: manifest `requires_sub_skills: {}`; tests assert `tools == {}`. Verified 98 passed.
- test_statusline_schema: REAL deploy-sync gap — .squidsquad/statusline.sh stale vs references/ (#11144 G10). Fix: synced deploy copy (now identical). Verified green.
- test_comms_sub_skills: chat-etiquette heading-format — STILL in KNOWN_FAILURES (Group A/source-format, deferred to next batch).

## #11503 — Group A remaining (KNOWN_FAILURES, ~17)
test_references, test_state_bus, test_comms_sub_skills, test_event_mode_fragments, test_cycle_pre,
test_4792_fragment_hygiene, test_deterministic_qa_framework, test_dm_verify_before_block,
test_own_domain_autofix, test_vault_synthesis, test_pickup_comment_fidelity_9946,
test_terminology_dual_aware_6274, test_compose_a2f_10492, test_atomic_emit_b7,
test_a3_golden_link_stage, test_compose_author_comments_11142, test_agent_boundaries,
test_feat_9588_lazy_load_bootstrap, test_stale_tracker_files_ref
+ Group B: test_config_functions

## Tree cruft (NOT #11503, leave untracked)
- .claude/scheduled_tasks.lock.stale-bak — relates to #11641 (stale lock crash); separate issue
- .squidsquad/skill/planning/CODE-REVIEW-11601.md — #11601 leftover (shipped); harmless

## Standing items (post-#11503)
- #11641 (high, open) — stale scheduled_tasks.lock crashes claude → reboot loop
- #11640 (high, open) — boot_remote REPO_ROOT fallback must fail-closed
- #11586 (high, open) — agents don't reach event mode on reboot
- #11587 (medium), #11511 (medium), #11505 (capabilities teardown)
