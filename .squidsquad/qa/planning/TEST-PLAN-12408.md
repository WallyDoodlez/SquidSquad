# TEST-PLAN #12408 — static gate fails closed on incomplete run

**Derived**: 2026-06-18 17:06 by verifier (qa), independently from the 3 ACs in the issue body (issue originally filed by qa). PR #12819, branch `squidsquad/task/12408`.
**Surface**: `tests/run_tests.py` (`run_static_tests()` + new `_static_gate_verdict()`) + `tests/test_12408_static_gate_completeness.py`. Change isolated to the static-gate path; integration untouched. No LLM-consumed instruction change → no comprehension AC.

## ACs (verbatim)
- **AC1**: static gate returns non-zero whenever any gated test fails (regression test injecting a deliberate failure asserts `run_tests.py` exits 1).
- **AC2**: no gated test hard-exits the pytest process; a full static run reaches its final summary and writes junit when requested.
- **AC3**: gate fails (non-zero) if the pytest session does not reach session-finish (incomplete-run guard).

## Test cases (live, independent of the worker's own injection)

- **TC1 (AC1):** inject a deliberate `assert False` test into the gated module set (via `discover_static_modules` override) → `run_static_tests()` must return `False` with a "failure(s)" verdict. Also: the 13-test regression file must pass.
- **TC2 (AC2):** run the REAL full `python tests/run_tests.py static` → must reach the `[static-gate]` verdict line (proving session-finish), parse a junit with >0 tests, and PASS (0 failures/errors), EXIT 0.
- **TC3 (AC3 — the original bug):** inject a real `os._exit(0)` test into the gated set → the process hard-exits mid-run, no junit is written → `run_static_tests()` must return `False` with an "INCOMPLETE RUN" verdict. (Pre-fix this returned `True` = false-green — the #12408 bug.)
- **TC4 (control):** a passing-only injected gated set → `run_static_tests()` returns `True` (no false-positive failing of clean runs).
- **TC5 (verdict-logic coverage):** regression suite covers every fail-closed branch — missing junit, malformed junit, 0-tests junit, recorded failures, recorded errors, non-zero rc with clean junit, xunit1 bare-`<testsuite>` root, temp-file cleanup, junit-requested wiring.

## Pass criteria
All 3 ACs observable: gate fails on a real failure (AC1), full run completes to junit-backed verdict (AC2), gate fails closed on a hard-exit / missing-junit / no-session-finish (AC3). No regression in the static gate's true-green path. DS review present.
