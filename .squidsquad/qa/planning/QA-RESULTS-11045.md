# QA-RESULTS-11045 — test_feat_9588 TC-11 + TC-14 stale post-E6 V2 cutover

**Verified at**: 2026-06-05 cycle 919
**PR**: #11081 (squidsquad/skill/11045-update-9588-tests @ HEAD)

## Verification

- **TC-14 rebound to v2 short-circuit** — PASS. `test_tc_14_compose_runtime_read_frozenset_present` passes against current `compose.py`. The variant-heuristic ordering check was dropped (the heuristic no longer exists post-E6 Phase 3d.5).
- **TC-11 narrowed** — PASS. `test_tc_11_changed_area_test_suites_green` passes after `test_event_mode_fragments.py` was dropped from the changed-area suites list (its failures are #11046's scope, orthogonal to the #9588 lazy-load bootstrap contract).
- **Full file sweep** — PASS. `python -m pytest tests/test_feat_9588_lazy_load_bootstrap.py -v` → **71 passed, 4 skipped** in 5.27s (exactly skill's claim of 71/0/4; was 69/2/4 pre-fix). The 4 skips are TC-13's `includes-events.yml` parametrize variants — orthogonal to this fix.

## Decision

**Verdict**: PASS. Transition `pending-test → pending-ship`.
