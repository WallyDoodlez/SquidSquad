# QA-RESULTS-11503 — Test-debt: 23 static tests red post-v0.44.0

**Verifier**: verifier-lead (qa)
**Date**: 2026-06-13
**PR**: #11683 (squidsquad/skill/post-cutover-cleanup → main) — MERGEABLE/CLEAN
**Branch verified**: squidsquad/skill/post-cutover-cleanup @ 592d55649
**Verdict**: **PASS (21/23 — scope per PM disposition 2026-06-13)**

## Scope (PM disposition 2026-06-13 08:02Z)
Close #11503 at 21/23. The final 2 (test_compose_author_comments_11142, test_agent_boundaries)
are NOT stale-test debt — they correctly fail on genuinely-incomplete work tracked by OPEN
#10360 (Responsibility compose slot, COMPOSE-ARCH §5.2). Keep them in KNOWN_FAILURES
(allowlisted → gate green); do NOT weaken assertions. Verifier should not block on them.

## AC Walk

### AC-1: run_tests.py fully green (0 failures)
**PASS.** `python tests/run_tests.py static` → EXIT=0. Static gate: 157 files gated,
**2257 individual tests PASSED, 0 FAILED, 0 ERROR**. Full suite (incl integration) → EXIT=0,
OK (skipped=2). Gate is no longer collecting 0 tests (the #11394 dead-gate root cause is gone).

### AC-2: 21/23 stale tests un-quarantined + rebound to v2 reality
**PASS.** KNOWN_FAILURES in tests/run_tests.py:86-89 now contains exactly 2 entries
(down from 23), both #10360-gated with detailed reasons:
  - test_agent_boundaries [known-failure] — 20 L3 variant responsibility stubs missing (§5.2), blocked on #10360
  - test_compose_author_comments_11142 [known-failure] — #10360-cleanup breadcrumbs dropped by #11331, blocked on #10360
All 21 rebound test files PASS in the static gate (diff: test_references, test_state_bus,
test_comms_sub_skills, test_4792_fragment_hygiene, test_deterministic_qa_framework,
test_dm_verify_before_block, test_pickup_comment_fidelity_9946, test_stale_tracker_files_ref,
test_compose_a2f_10492, test_atomic_emit_b7, test_a3_golden_link_stage, test_config_functions,
test_cycle_pre, test_terminology_dual_aware_6274, test_own_domain_autofix, test_vault_synthesis,
test_event_mode_fragments, test_feat_9588_lazy_load_bootstrap, test_feat328_coverage,
test_manifest_registry, test_statusline_schema).

### AC-3: Group C real regressions fixed (not papered over)
**PASS.** 2 production-code fixes verified in diff (origin/main...HEAD):
  - references/roles/dm/manifest.yaml — removed orphan `requires_sub_skills.any_of:[local_delivery]`
    pointing at the deleted capabilities registry (deadwood per INSTALLER-ARCH §8.3). test_manifest_registry
    + test_feat328_coverage now assert tools=={}; both green.
  - .squidsquad/statusline.sh — synced to references/statusline.sh (#11144 G10 deploy-sync gap).
    test_statusline_schema green.

### AC-4: KNOWN_FAILURES NOTICE keeps debt honest
**PASS.** NOTICE prints both remaining entries with #10360 cross-links every run.

## Evidence
- Static run captured: 2257 PASSED / 0 FAILED / 0 ERROR, EXIT=0
- Full suite: 53 passed, 2 skipped, EXIT=0
- KNOWN_FAILURES = {test_compose_author_comments_11142, test_agent_boundaries} (both #10360-gated)
- PR #11683 mergeable=MERGEABLE, mergeStateStatus=CLEAN

## Verdict
**PASS → pending-ship.** The 21 cleared stale tests are the deliverable; the 2 remaining
allowlisted reds are #10360-gated (verified #10360 is OPEN), expected per PM, NOT regressions.
Rides PR #11683 with #11657. DM ships the bundle.
