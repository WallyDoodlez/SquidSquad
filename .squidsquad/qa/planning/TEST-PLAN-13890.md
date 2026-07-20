# TEST-PLAN-13890

test_agent_boundaries.py AC6/AC7/AC8/AC11 + test_compose_author_comments_11142 reconciliation (MEDIUM, type:issue, auto-approved, my own filed finding).

## TCs

- **TC1 — AC6 retirement, independently confirmed**: is the lineage-tag convention (`<!-- absorbed from X -->`) genuinely, fully gone from `references/` (not just from the two test's asserted paths)?
- **TC2 — AC4 rewrite, live**: does the composed output for a real role genuinely carry the NEW claimed prose and NOT the old roster header, confirming the rewrite matches actual current behavior rather than being aspirational?
- **TC3 — AC11 replacement, independently confirmed**: does `compose._inject_role_roster`'s own (pre-existing, untouched-by-this-PR) docstring genuinely document marker-absence as intentional steady state — i.e. is the new assertion following documented reality, not inventing a new contract to make a test pass?
- **TC4 — superseded comprehension specs actually skip**: do 2183/2195 now cleanly SKIP (not FAIL) in a bare pytest run?
- **TC5 — superseded_by convention is genuinely pre-existing**: confirm `comprehension_staleness.py` already consumed `superseded_by` before this PR (this PR closes the gap for the LIVE harness specifically, not inventing the convention).
- **TC6 — the two reconciled files pass in full**: `test_agent_boundaries.py` + `test_compose_author_comments_11142.py`.
- **TC7 — the official static gate is genuinely, fully green**: `tests/run_tests.py static`, with `KNOWN_FAILURES` now empty — both files must be included and passing, not silently re-excluded.
- **TC8 — integration suite**: unaffected (test-only change, no production script touched except `run_tests.py`'s own registry dict and `comprehension_helpers.py`).
