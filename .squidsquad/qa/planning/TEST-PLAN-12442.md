# TEST-PLAN-12442

**Issue**: #12442 — pending-ship work does not auto-route to dm in event mode (#12342 gap)
**Type**: issue (bug, auto-approved) · **Role**: skill · **PR**: #12444 · **Branch**: squidsquad/task/12442
**Derived**: 2026-06-15 from symptom + expected behavior (no formal AC list on bugs).

## ACs (derived from symptom + PR mechanism)

- **AC-1** — Handoff work (pending-ship → dm, pending-test → verifier) that stays unclaimed gets the `assigned-to` wake nudge **re-emitted** on a bounded cadence until its status changes (closes the starvation; #12418 sat 48min).
- **AC-2** — Re-emit **bypasses the `updatedAt` time filter** (fixes startup-blindness: an item already at a handoff status when the detector (re)starts has an old `updatedAt` the filter would hide forever).
- **AC-3** — Re-emit is **bounded** (cadence + state dict capped) — no infinite spam / unbounded memory.
- **AC-4** — Worker statuses (`approved`/`open`) keep single-emit + time-filter (their worker is presumed looping); only handoff statuses get re-emit.
- **AC-5** — Routing keys off **status** → verifier/dm alias (not the `role:*` label) — #12418 carried role:skill but must still route to dm by status.
- **AC-6** — No regression to #12342 EAD routing; full harness suite green.

## Test cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | AC6 | full `tests/test_harness.py` | all green |
| TC-2 | AC1 | TestEADHandoffReemit12442 reemits-after-interval / reemits-stuck-pending-test-to-verifier | re-emit fires after interval |
| TC-3 | AC2 | test_reemits_stuck_pending_ship_despite_old_updatedat | re-emit despite stale updatedAt |
| TC-4 | AC3 | inspect `_HANDOFF_REEMIT_SECONDS`=600 + `_handoff_emit_at` cap 500 | bounded |
| TC-5 | AC4 | test_worker_status_never_reemitted | worker statuses not re-emitted |
| TC-6 | AC5 | inspect `_STATUS_ROUTING` + `_alias_for_role_class` | status-keyed routing to verifier/dm alias |

## Comprehension spec
Not required — harness.py code (EAD), not LLM-consumed instructions.
