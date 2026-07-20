# QA-RESULTS-13890

**Verdict: PASS → pending-ship**

## TC Results

| TC | Result | Evidence |
|----|--------|----------|
| TC1 — AC6 retirement | PASS | `grep -rn "absorbed from" references/` → 0 matches, repo-wide, not just the two asserted files. |
| TC2 — AC4 rewrite, live | PASS | Live-composed the `pm` role via `_v2_test_helpers.v2_compose_for`: contains "Your teammates run in parallel on their own clones" (new claim) and "What this role does" (surviving invariant); does NOT contain the old "## Your Teammates' Responsibilities" header. Matches the rewritten test's assertions exactly. |
| TC3 — AC11 replacement | PASS | `references/scripts/compose.py` has **zero diff** in this PR (confirmed via `git diff main...HEAD --stat`) — its `_inject_role_roster` docstring, already on main before this PR, genuinely reads "Marker absence is the correct steady state; return content unchanged without warning." The test rewrite follows already-documented production behavior, not a new contract invented to pass. |
| TC4 — superseded specs skip | PASS | `pytest tests/test_comprehension_2183.py tests/test_comprehension_2195.py`: 10/10 SKIPPED (was FAILED before this fix), each with a clear "spec superseded by #13890" reason. |
| TC5 — pre-existing convention confirmed | PASS | `grep -rln "superseded_by"` shows `references/scripts/comprehension_staleness.py` and its own dedicated `test_comprehension_spec_staleness_13575.py` already consumed the field — this PR closes the gap for the separate live-harness path (`comprehension_helpers.py`) specifically, not inventing the convention. |
| TC6 — reconciled files pass in full | PASS | `test_agent_boundaries.py` + `test_compose_author_comments_11142.py`: 102/102 — matches skill's own claimed count exactly. |
| TC7 — official static gate, fully green | PASS | `tests/run_tests.py static`: `KNOWN_FAILURES` is empty (confirmed via diff), both files run un-excluded — **`[static-gate] PASS — 6110 gated test(s) passed (0 failures, 0 errors)`**, matching skill's claimed "PASS 6110/0" exactly. This is the first time this session the OFFICIAL gate has been genuinely, fully green with zero quarantined files. |
| TC8 — integration suite | PASS | `run_tests.py harness` + `status_flow`: both OK. |

## Note

This item closes the loop on my own earlier #13890 filing — and on a correction I posted moments before discovering skill had already gone further: rather than just leaving the two files excluded (which my correction comment had suggested was defensible), skill traced every one of the 42 failing assertions to its specific root cause and either rewrote it against current reality or retired it with documented evidence, then re-included both files in the fail-closed gate. This is the more thorough, correct outcome — the static gate's signal is now fully restored rather than permanently degraded by a "known-red" carve-out.

## Conclusion

All 8 TCs pass, every claim independently re-derived (not trusted from the PR description) against live composed output, live pytest runs, and direct source reads of untouched production code. Zero gaps. → **pending-ship**.
