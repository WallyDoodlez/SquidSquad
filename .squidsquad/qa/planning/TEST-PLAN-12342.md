# TEST-PLAN-12342 — EAD routes pending-test/pending-ship to QA/DM (event-mode delivery)

Verifier: qa · derived 2026-06-14 05:37 · independent of worker PR #12364 diff
Issue: #12342 (type:issue, severity:high, role:skill) — in event mode the EAD only emits `assigned-to` for approved/open, so QA (pending-test) and DM (pending-ship) starve; no verification/delivery work routes to them. HIGH blast-radius (harness.py EAD loop = all-agent work delivery).

## Contract (from issue Asks + DS-REVIEW findings)

- AC-A: EAD emits `assigned-to` for `pending-test` → the install's **verifier** alias, and `pending-ship` → the **dm** alias — including agent-made transitions.
- AC-B: approved/open still route to the issue's worker `role:*` alias (no regression).
- AC-C (DS Finding 1): a reject loop `pending-test → in-progress → pending-test` MUST re-emit each re-entry (no permanent suppression / QA re-verification starvation).
- AC-D: dedup — same status + comment-bumped updatedAt does NOT re-emit; a status change does.
- AC-E: target alias resolved from the install's `## Aliases` registry, not hardcoded (and **for THIS install, verifier→qa**, dm→dm).
- AC-F: decorated-role transition emit (`'skill (skill)'`) uses the bare alias (tracker.py).
- AC-G: tests + full suite + integration green; no regression (high blast-radius).

## Test cases

| TC | AC | Check | Method |
|----|----|-------|--------|
| TC-1 | A,E | **LIVE install-specific**: `_alias_for_role_class('verifier')`→`qa`, `('dm')`→`dm`; registry maps qa→verifier | run against real config in this clone |
| TC-2 | A | pending-test emits target_alias=verifier; pending-ship→dm | `test_pending_test_routes_to_verifier`, `test_pending_ship_routes_to_dm` |
| TC-3 | B | approved→worker label; open→worker label | `test_approved_routes_to_worker_label`, `test_open_routes_to_worker_label` |
| TC-4 | C | reject loop pending-test→in-progress→pending-test re-emits | `test_back_transition_reemits_to_verifier` |
| TC-5 | D | same status + updatedAt bump → no re-emit; transition → emit | `test_comment_bump_same_status_does_not_reemit`, `test_dedup_per_issue_status_across_transitions` |
| TC-6 | — | in-progress/planned (unmapped) emit nothing but ARE recorded | `test_in_progress_emits_nothing` (+ back-transition proves recording) |
| TC-7 | E | registry resolution honors non-default alias; unreadable-config fallback to class name | `test_alias_for_role_class_resolves_from_registry`, `..._falls_back_to_class_name` |
| TC-8 | — | broken `_is_agent_update` removed (it matched every issue → EAD emitted nothing) | `test_is_agent_update_removed` |
| TC-9 | — | eviction cap = 500 issues | `test_external_detector_eviction_bounds_at_500` |
| TC-10 | G | full harness suite + integration + changed-file consumers green | pytest test_harness.py; run_tests.py; cycle_pre/post/tracker_authority |
| TC-11 | — | PR merges clean; prod tests permanent in tests/ | gh mergeable |

## Independence note

TC-1 is the install-specific check the unit tests cannot give: the suite asserts routing against a controlled mock registry (`verifier`), which would pass even if THIS install's registry were misconfigured. Resolving the alias against the *real* config in this clone (verifier→qa) is what proves pending-test work will actually wake *me*. Meta-confirmation: this very issue reached me only via a PM **manual** nudge (assigned-to from pm), never via EAD — consistent with the pre-fix bug; post-ship harness restart on new code is the operator's end-to-end confirmation (chicken-and-egg, per skill).
