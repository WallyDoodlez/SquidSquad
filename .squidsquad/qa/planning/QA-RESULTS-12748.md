# QA-RESULTS-12748 — env-gated live tests SKIP (not FAIL) when keyless

**Verdict: PASS — zero gaps** → pending-ship (DM).
**Date:** 2026-06-20 02:32 · **Verifier:** qa · PR #12999 @ 94dc33075 · branch `squidsquad/task/12748`.

Bug (type:issue/medium, auto-approved), filed by skill. test-infra → no CQ.
Worktree `D:\Dev\Dev\sq-12748-verify`. Append-only.

## Fix summary
New shared `tests/comprehension_helpers.run_comprehension_or_skip` centralises the env-gate
that 10 call sites had copied + drifted. "No results.json" → SKIP (cache hit on exit 0;
claude absent/unusable on exit !0); valid results.json → returned for the per-question asserts;
malformed results.json → FAIL. The per-file `pytest.fail`-on-no-results (which reddened the
keyless suite, ~35 comprehension reds) is removed across the comprehension tests +
test_model_router_live.

## AC walk (derived; all PASS)
- **AC1 (SKIP not FAIL)** PASS — helper SKIPs on: claude CLI absent; present-but-unusable
  (keyless → no results.json, exit !0); content-hash cache hit (exit 0, no results.json).
  test_12748: skips_when_claude_absent / skips_on_cache_hit / skips_when_no_results_json_keyless.
- **AC2 (regression-detection preserved)** PASS — a valid results.json is returned and the
  per-question asserts still catch a real regression. Invariant (reviewed): a genuine
  comprehension regression ALWAYS yields a results.json with failing answers, so skipping the
  no-results.json case never masks a regression. test_returns_parsed_results_when_present.
- **AC3 (pipeline-garbage still fails)** PASS — a malformed-but-present results.json FAILs (not
  skip). test_fails_on_malformed_present_results.
- **AC4 (centralized, no per-file drift)** PASS — diff removes per-file `_claude_available` +
  fail-on-no-results from test_comprehension_{1428,2181,2183,2195,361,4792,9184}.py +
  test_model_router_live.py; all route through the one shared helper.
- **AC5 (helper test)** PASS — test_12748_comprehension_skip_helper.py, 7 cases, all branches → 7 passed.
- **No CQ** — test-infra only.

## No-regression
- test_12748_comprehension_skip_helper.py → 7 passed.
- Full static gate: `run_tests.py static` → **PASS — 4705 gated tests, 0 failures, 0 errors** (exit 0).
  The 9 converted test files collect cleanly; only the 2 allowlisted #10360 known-failures.

## Scope note (the distinct flaky-load mode, not this PR)
This PR fixes the issue's PRIMARY scope (absent-env/keyless ERROR→SKIP). The DISTINCT
"flaky-under-concurrent-gh-load false-red in the static gate" mode I flagged on #12748 earlier
this session (TestTriageLiveSmoke / integration test_status_flow) is NOT addressed here (different
root cause: present-env, concurrent load) and was raised as advisory — does not block this verdict.
A live note in this env: claude CLI is present, so the comprehension tests run/cache-skip rather
than exercise the absent path; the absent/keyless SKIP path is proven via the mocked helper test + code review.

## Disposition
pending-test → pending-ship (DM). No closing keyword on PR #12999, no review:human-required → merge
deferred to DM. Counter NOT bumped. TEST-PLAN-12748 + QA-RESULTS-12748 on main.
