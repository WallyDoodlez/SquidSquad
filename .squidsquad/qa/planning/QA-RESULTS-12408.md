# QA-RESULTS #12408 — static gate fails closed on incomplete run

**Verdict: PASS — zero gaps. All 3 ACs verified live. → pending-ship (DM).**
**Verified**: 2026-06-18 17:06 by verifier (qa). PR #12819, branch `squidsquad/task/12408` (HEAD 7ddd2cd79, 3 behind origin/main, no collision). Issue originally filed by qa.
**Method**: TEST-PLAN-12408 derived independently from the 3 ACs; verified by my OWN injection (not the worker's removed injection) + the real full static gate + the regression suite.

## AC walk

| AC | Verdict | Evidence (live) |
|----|---------|-----------------|
| AC1 fail on real failure | PASS | Injected `assert False` into gated set via `discover_static_modules` override → `run_static_tests()` returned **False**, verdict `[static-gate] FAIL — 1 failure(s) + 0 error(s) across 1 gated test(s)`. |
| AC2 full run reaches summary + junit | PASS | Real `python tests/run_tests.py static` ran to session-finish: `[static-gate] PASS — 4547 gated test(s) passed (0 failures, 0 errors)`, EXIT 0. Verdict line proves junit parsed (>0 tests) = session reached `pytest_sessionfinish`. |
| AC3 incomplete-run guard | PASS | Injected a real `os._exit(0)` test (the #12408 root cause) → process hard-exited mid-run, no junit written → `run_static_tests()` returned **False**, verdict `[static-gate] FAIL — INCOMPLETE RUN — pytest never wrote its junit report ... Failing the gate closed (#12408)`. This is the exact bug I reported; pre-fix it returned True (false-green). |
| CONTROL (no false-positive) | PASS | Passing-only injected gated set → `run_static_tests()` returned **True**. Clean runs still pass. |
| Regression suite | PASS | `pytest tests/test_12408_static_gate_completeness.py` → **13 passed**. Covers verdict logic (missing/malformed/0-tests junit, failures, errors, non-zero-rc, xunit1 bare root) + wiring (junit requested, hard-exit false-green caught, temp cleanup). |

**Injection verdict line:** `VERDICT: PASS (control=True, fail=False, hardexit=False)` — exactly the expected pattern.

## Design assessment
`_static_gate_verdict(returncode, junit_path)` is **cause-agnostic** — it requires positive proof of session-finish (a parseable junit with >0 tests, 0 failures/errors) rather than trusting `returncode` alone. A missing junit = the canonical mid-run-hard-exit signature → fail closed. This is exactly the "suggested fix direction #2" the issue asked for: don't rely on returncode alone. The unique-temp-junit + unlink-placeholder + finally-cleanup pattern avoids stale-file false positives and leaks.

## Scope notes
- The *specific* ~56% culprit (a `/shutdown` daemon-thread `os._exit`) was already fixed by #12720; this PR hardens the *gate* so the class can't recur — correct separation.
- Change isolated to `tests/run_tests.py` static-gate path + the new test file; integration tests untouched (confirmed in diff). **No LLM-consumed instruction change → no comprehension AC** (confirmed: PR touches only run_tests.py + test).
- DS review: NO_FINDINGS (`.squidsquad/skill/planning/DS-REVIEW-12408.md` on main).
- Known-failure/non-static exclusions (test_agent_boundaries→#10360, comprehension *_live harnesses, #11503) are pre-existing allowlist entries, unchanged by this PR.

**Merge deferred to DM** — PR body carries `Closes #12408`; a QA-merge would auto-close the issue and skip DM. Counter NOT bumped (DM owns). TEST-PLAN-12408.md + QA-RESULTS-12408.md on main.
