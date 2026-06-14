# TEST-PLAN-12282 — /restart leak to LIVE harness during full-suite runs

Verifier: qa · derived 2026-06-14 04:17 · independent of worker PR #12341 diff
Issue: #12282 (type:issue, severity:high, role:skill) — test-isolation leak POSTing real `/restart` to the production harness (:7373) during the suite run; suspected engine of the reboot churn.

## Bug contract (derived from issue body, not the PR)

The suite must NEVER issue a real `POST /agents/<role>/restart` to the live harness on the default port (7373). The leak path: a test exercises `cycle_post._do_stop_after_cycle_check` with `exceeded=True` + `_query_harness_intent`→None, reaching the real `_post_harness_restart`, whose `_discover_harness_port()` falls back to default 7373 when the tmp `.squidsquad` has no `.harness-port` → real POST at the production harness.

## Test cases

| TC | Derived-from | Check | Method |
|----|-------------|-------|--------|
| TC-1 | "something POSTs /restart during suite" (repro) | Running the full suite against a LIVE harness triggers ZERO real restarts | Capture skill agent `boot_time`/`last_spawn_at`/`pid` before & after full suite; must be byte-identical |
| TC-2 | RCA (single offending test) | `test_exits_on_context_pressure` no longer reaches the live wire | Run it; restart must route to a mock, not urlopen→7373 |
| TC-3 | "convert silent leak to loud failure" | The leak path now fails loudly instead of POSTing live | `TestNoLiveHarnessRestartLeak12282` reproduces the exact un-mocked path and asserts the guard raises |
| TC-4 | regression / no collateral | Whole `test_cycle_post.py` module green under the autouse guard | `pytest tests/test_cycle_post.py` |
| TC-5 | no regression elsewhere | Integration suite still green | `python tests/run_tests.py` |
| TC-6 | shippability | PR merges cleanly; tests are permanent (already in `tests/`) | `gh pr view --json mergeable`; confirm no planning-dir test promotion needed |

## Independence note

The strongest evidence is TC-1 (live, un-mocked, beyond the worker's own guard): the historical leak fired a real `/restart` every full-suite run, so a clean before/after on the live skill agent is direct proof the engine is gone — independent of whether the worker's guard logic is correct. TC-3 corroborates by proving the leak path is now caught.
