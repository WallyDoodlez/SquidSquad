# TEST-PLAN-12748 — env-gated live tests ERROR/FAIL instead of cleanly SKIP

Bug (type:issue/medium, auto-approved), filed by skill (improvement). PR #12999,
branch `squidsquad/task/12748`, role:skill. No explicit AC list → ACs derived from
the issue's root-cause + suggested direction. test-infra → **no CQ**. Worktree
`D:\Dev\Dev\sq-12748-verify`.

Note: I earlier commented on #12748 flagging a DISTINCT flaky-under-concurrent-gh-load
mode. This PR addresses the issue's PRIMARY scope (absent-env/keyless SKIP); the
flaky-load mode is a separate follow-up I raised as advisory ("split if you prefer") —
not in this PR's scope, does not block this verdict.

## Derived ACs
- **AC1 (SKIP not FAIL):** env-gated comprehension/live tests SKIP (never ERROR/FAIL) when
  the claude CLI is absent, present-but-unusable (keyless/unauthenticated → no results.json),
  or a content-hash cache hit.
- **AC2 (regression-detection preserved):** a genuine comprehension regression — a results.json
  whose answers fail — still FAILs via the per-question asserts.
- **AC3 (pipeline-garbage still fails):** a malformed-but-present results.json FAILs (not skip).
- **AC4 (centralized, no per-file drift):** a shared helper (`comprehension_helpers.run_comprehension_or_skip`)
  replaces the per-file copied gating across the 10 call sites.
- **AC5 (helper test):** test_12748 exercises every branch of the gate.
- **No CQ** — test-infra only.

## Test cases / evidence
- **TC1 (AC1/AC2/AC3 — helper logic)** — test_12748_comprehension_skip_helper.py (7 cases):
  skips_when_claude_absent; skips_on_cache_hit (exit 0, no results.json); skips_when_no_results_json_keyless
  (exit !0); returns_parsed_results_when_present (regression path); strips_code_fences;
  fails_on_malformed_present_results. → 7 passed. Non-vacuous.
- **TC2 (AC4)** — diff: per-file `_claude_available` + `pytest.fail`-on-no-results removed from
  test_comprehension_{1428,2181,2183,2195,361,4792,9184}.py + test_model_router_live.py; all now
  call the shared helper. Single gate, can't drift.
- **TC3 (helper invariant review)** — read comprehension_helpers.py: "no results.json" → SKIP
  (cache hit on exit 0; claude unusable on exit !0); valid results.json → return (per-question
  asserts still catch regressions); malformed → fail. Sound — a real regression always yields a
  results.json with failing answers, so skip-on-absent never masks a regression.
- **TC4 (no-reg)** — full run_tests.py static, incl. collection of all 9 converted test files (pending — see QA-RESULTS).

Live note: in this env the claude CLI IS present, so the comprehension tests would run (or cache-skip)
rather than exercise the absent-CLI path; the absent/keyless SKIP path is proven deterministically by
the mocked helper test (TC1) + code review (TC3), not run live (avoids an expensive real model pipeline).
