# Working State

- **Task**: #11394 (close STATIC_TEST_MODULES gating delta) — IN PROGRESS
- **Status**: in-progress
- **Started**: 2026-06-12 15:31
- **Branch**: squidsquad/task/11394
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## ⚠️ Session note
Running PRE-v0.44.0 composed instructions (reboot pending per DM; operator/PM-initiated). Doing deterministic code work on #11394 — instruction staleness doesn't block it. Booted via /loop (polling mode); cron 0bdc0ae0 every 30m.

## DESIGN LOCKED (cycle ~1633) — auto-discovery + 3 exclusion layers
`run_static_tests()` will auto-discover `tests/test_*.py` (non-recursive → integration/ excluded) instead of hardcoded STATIC_TEST_MODULES. Closes BOTH drift modes (forgotten-adds + deleted-file collection-break — the regression I introduced via #11331 deleting test_l2_l3_op_anchoring_11227 while run_tests.py:148 still listed it → 0 collected).

Exclusion layers (all documented, NOTICE-printed every run):
1. **LIVE_SUFFIX** `_live` → 6 files (network/live-model). Category.
2. **KNOWN_NON_STATIC** (valid but can't run in fast offline static ctx): 7 CQ comprehension spawners (test_comprehension_1428/2181/2183/2195/361/4792/9184 — spawn live model via run_comprehension_test.py) + test_feat_6581_wizard_reframing (test_tc_10b recursively runs full run_tests.py).
3. **KNOWN_FAILURES** (currently-failing, NOT fixed here, issue-ref'd).

## EMPIRICAL MAP (authoritative, JUnit XML — dot-parsing was unreliable)
28 ungated non-CQ non-live files mapped (.squidsquad/skill/planning/11394-ungated.xml):
- **23 CLEAN → auto-gate** (incl 4 stale-commented known-fails that NOW PASS: test_feat_1328_blocked_skip, test_feat_2495_upgrade_rewrite, test_feat_3645_auto_merge, test_feat_3663_pr_conflict_check — proves drift; auto-discovery re-includes them).
- **5 BROKEN** (verified stale, fail in current arch everywhere — NOT clone-staleness):
  - test_config_functions (14f) — SAMPLE_CONFIG fixture missing new FIELD_MAP entries (code-review-model, effort-*, event-driven). Fixture drift.
  - test_agent_boundaries (39f) — asserts removed `responsibility.md` + "Know each other's responsibilities" phrase (gone from references/). Stale post-v2.
  - test_feat_9588_lazy_load_bootstrap (18f) — asserts removed `## Boot — Mode Detection (#9588)` heading (gone everywhere). Stale post-restructure (same class as shipped #11383).
  - test_stale_tracker_files_ref (4f) — FileNotFoundError on removed `roles/pm|dm/prohibitions.md`. Stale post-v2.
  - test_feat_6581_wizard_reframing (1f) — test_tc_10b runs run_tests.py asserting exit 0 (meta/recursive) → KNOWN_NON_STATIC not KNOWN_FAILURES.

## IN FLIGHT
Background bh9koj429 = per-file timeout map of GATED set (131 existing files) → finds gated active-failing (working-state prior flagged test_cycle_pre, test_event_mode_fragments) + the slow/hanging test at ~55%. Need this to COMPLETE KNOWN_FAILURES so `run_tests.py static` exits 0 post-refactor. Output: 11394-gated-perfile.json + 11394-GATEDDONE.txt.

## IMPLEMENTED (cycle ~1633) — DONE
- Umbrella **#11503** filed (high sev): "23 static tests red post-v0.44.0, gate dead since cutover". Full classification (A stale-test / B fixture-drift / C possibly-real-regression).
- run_tests.py: STATIC_TEST_MODULES → discover_static_modules() (globs existing tests/test_*.py) + LIVE_SUFFIX + KNOWN_NON_STATIC(8) + KNOWN_FAILURES(23, all #11503-ref'd) + NOTICE print. Counts: gated 136 / non_static 8 / failures 23 / live 6 = 173.
- tests/test_11394_static_discovery.py: 7 AC3 invariants (no silent ungating / disjoint / exclusions-exist / reasons / discovery-only-existing / live-never-gated / survives-deleted-file). ALL PASS.
- test_references.py TestRunTestsModuleList: repointed #5435 check from STATIC_TEST_MODULES to KNOWN_* dicts. Passes.

## STATUS (cycle ~1633): gate GREEN (RC=0), committed, surfaced
- Static gate green: 136 gated, 31 excluded + 6 live. Fixed cp1252 UnicodeEncodeError in NOTICE (UTF-8 stdout reconfigure).
- COMMITTED **3a6aed32c** (run_tests.py + test_11394_static_discovery.py + test_references.py). 3 files, +241/-132.
- Discussion posted on #11394 (gate-dead-since-cutover finding + #11503 + Group-C possibly-real regressions flagged for PM/operator).

## RESUME (tail — DS audit in flight)
- Background **b82u3ptka** = DS code-review (model_router) → .squidsquad/skill/planning/DS-REVIEW-11394.md. On model_router exit 1/2/3 → Sonnet subagent fallback for same review.
- THEN: (1) read DS review, address any real findings (re-commit if needed). (2) transition #11394 in-progress→pending-test (tracker.py). (3) PR off **main** (git_ops pr-create; check review:human-required label). (4) iteration log + vault-remember (learning: broken canonical gate masked 23 reds; auto-discovery > allowlist for drift-prone gates).
- NOTE: #11394 PR is code-only (3 test files). working-state + planning/*.log scratch are NOT part of the PR.

## Prior (v0.44.0 cutover — SHIPPED)
- Cutover reconciliation (#11331) shipped as v0.44.0 (cycles 1625-1629). On main via squash. Vault note `learning-bundle-branch-reconciliation.md`. See iter-441/442.
