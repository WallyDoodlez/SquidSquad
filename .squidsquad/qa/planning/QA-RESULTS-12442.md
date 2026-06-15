# QA-RESULTS-12442

**Issue**: #12442 — pending-ship work does not auto-route to dm in event mode (#12342 gap)
**Verified**: 2026-06-15 09:11 (qa cycle 191, POLLING) · **Branch**: squidsquad/task/12442 (HEAD `cabe11edf`) · **PR**: #12444
**Verdict**: ✅ **PASS → pending-ship.** All 6 derived ACs met with unit-test + code-inspection evidence. Zero gaps.

## AC walk

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC-1 | AC6 | ✅ PASS | `tests/test_harness.py` = **230 passed**. #12342 time-filter test retargeted to a worker status (handoff now intentionally exempt — legitimate behavior-change test update, not masking). |
| TC-2 | AC1 | ✅ PASS | `reemit_due` branch in `_check_for_changes`: `is_handoff and _handoff_due(...)` re-emits `assigned-to` until status changes. Tests: test_reemits_after_interval_elapses, test_reemits_stuck_pending_test_to_verifier. |
| TC-3 | AC2 | ✅ PASS | `reemit_due` deliberately does NOT consult `updated_recently` (code comment is explicit). test_reemits_stuck_pending_ship_despite_old_updatedat green — fixes startup-blindness. |
| TC-4 | AC3 | ✅ PASS | `_HANDOFF_REEMIT_SECONDS=600`; `_handoff_emit_at` lock-guarded, LRU-evicted at cap 500. test_no_reemit_within_interval + test_fresh_transition_seeds_timer_no_immediate_double. |
| TC-5 | AC4 | ✅ PASS | `is_handoff` true only for verifier/dm role_class routes; approved/open keep single-emit + time-filter. test_worker_status_never_reemitted green. |
| TC-6 | AC5 | ✅ PASS | `_STATUS_ROUTING` maps `status:pending-ship`→dm, `status:pending-test`→verifier by STATUS (not `role:*`); `_alias_for_role_class` resolves the install's verifier/dm alias (handles #11600 alias class). Addresses the RCA lead — #12418 carried role:skill yet must route to dm. |

11 #12442-specific tests pass (7 TestEADHandoffReemit12442 + retargeted TestEADStatusRouting12342). Code logic reviewed: branching, time-filter-bypass, idempotency (assigned-to is a wake nudge), bound, thread-safety (lock-guarded) all correct.

## Bootstrap note (flagged for PM/DM — NOT a blocker)
This fix is itself a `pending-ship` item — and the bug it fixes is exactly "DM doesn't auto-pick-up pending-ship." Until PR #12444 merges, the auto-route is NOT live, so **DM will need PM's existing manual `assigned-to(target=dm)` nudge to ship #12442 itself** (the documented interim workaround, already active per BRIEFING). Once shipped, recommend confirming the NEXT pending-ship auto-routes to DM with no manual nudge (closes the loop / proves the fix live).

## Comprehension spec
Not required — harness.py EAD code, not LLM-consumed instructions.

## Decision
- All 6 ACs PASS. Transitioned `pending-test → pending-ship`.
- **Merge deferred to DM** (consistent with cy180/#12418): PR #12444 carries `Fixes #12442` → QA-merge would auto-close + skip DM's ship ceremony. DM merges + ships. Ship counter NOT bumped (DM owns).
