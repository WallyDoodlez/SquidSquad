# QA-RESULTS-12342 — VERDICT: PASS (zero gaps)

Verifier: qa · 2026-06-14 05:37 · PR #12364 (`squidsquad/task/12342`, HEAD 285eab7f5) · harness.py + tracker.py + 2 test files · base main CLEAN/MERGEABLE

## Result Summary

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC-1 | A,E | **PASS** | LIVE in this clone: `_alias_for_role_class('verifier')`→`'qa'`, `('dm')`→`'dm'`; `config.parse_aliases_registry()` = `{skill:(worker,skill), pm:(pm,None), dm:(dm,None), qa:(verifier,None)}`. pending-test will emit target_alias=`qa` → wakes me; pending-ship → `dm`. The install-specific correctness the unit tests can't assert. |
| TC-2 | A | **PASS** | `test_pending_test_routes_to_verifier`, `test_pending_ship_routes_to_dm` |
| TC-3 | B | **PASS** | `test_approved_routes_to_worker_label`, `test_open_routes_to_worker_label` (workers unaffected) |
| TC-4 | C | **PASS** | `test_back_transition_reemits_to_verifier` — faithfully exercises pending-test→in-progress→pending-test and asserts re-emit to verifier (DS Finding 1, the real regression DS caught) |
| TC-5 | D | **PASS** | `test_comment_bump_same_status_does_not_reemit`, `test_dedup_per_issue_status_across_transitions` |
| TC-6 | — | **PASS** | `test_in_progress_emits_nothing` + back-transition test proves unmapped statuses are recorded (not silently skipped) |
| TC-7 | E | **PASS** | `test_alias_for_role_class_resolves_from_registry` (non-default alias honored), `..._falls_back_to_class_name` (config-unreadable → class name) |
| TC-8 | — | **PASS** | `test_is_agent_update_removed` — confirms the heuristic that matched every issue (made EAD emit nothing) is gone; dedup now prevents re-trigger |
| TC-9 | — | **PASS** | `test_external_detector_eviction_bounds_at_500` (cap is 500 issues, not ~125) |
| TC-10 | G | **PASS** | `test_harness.py` 209 passed; `#12342`-targeted slice 74 passed; integration `run_tests.py` 53 OK (skipped=2); changed-file consumer sweep (tracker_authority + cycle_pre + cycle_post) 343 passed |
| TC-11 | — | **PASS** | PR #12364 `mergeable=MERGEABLE`, `mergeStateStatus=CLEAN`; no divergence on harness.py/tracker.py since branch point; tests permanent in `tests/` |

## Contract walk

- **AC-A/E met (live):** the starvation root cause — EAD routing only approved/open — is fixed; pending-test→verifier(qa)/pending-ship→dm routing resolves correctly against THIS install's real registry.
- **AC-B met:** worker routing (approved/open → role:* alias) preserved.
- **AC-C met:** the DS-caught back-transition regression (reject-loop re-verification starvation) is fixed and locked by a dedicated test. This was the highest-risk part of the change and is the one I scrutinized most — the dedup records last-status-per-issue and emits on change, so re-entry to pending-test after a reject re-wakes the verifier.
- **AC-F:** tracker.py strips the parenthetical alias from emit_role; documented #6274 dual-aware edge (role-class form during the qa/dev legacy window) is the SECONDARY path — the primary EAD assigned-to resolves the alias from the registry directly, so it is unaffected. Not a gap.

## Blast-radius

harness.py EAD drives work delivery for every agent. Verified: workers unaffected (approved/open unchanged), unmapped statuses are no-ops (in-progress/planned/pending/planning emit nothing), eviction bounded at 500 issues, full harness + integration + consumer suites green. Removing `_is_agent_update` is safe because per-(issue,status) dedup — not the broken title-prefix heuristic — now prevents comment-bump re-triggering (verified by TC-5).

## Note

This issue reached me only via a PM **manual** assigned-to nudge, never via EAD — itself consistent with the pre-fix bug. After this ships and the harness restarts on new code, the EAD should auto-route pending-test→qa / pending-ship→dm (operator's end-to-end confirmation; chicken-and-egg per skill's comment). Orphan claude/event_poll accumulation (Ask #3) was correctly split to #12363.

**VERDICT: PASS — zero gaps. PR #12364 approved + merged. Status → pending-ship.**
