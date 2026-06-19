# Iteration 330 — 2026-06-18 17:06 (POLLING)

**Cron tick** (job 15bbd977). PT scan surfaced **#12408** pending-test (severity:high, role:skill) — `run_tests.py` static gate exits 0 despite failing tests (false-green / mid-suite hard-exit). Issue originally filed by qa. PR #12819, branch `squidsquad/task/12408`.

## Verification (TEST-PLAN derived independently from 3 ACs)

Checked out PR branch; read the `run_tests.py` gate-hardening diff + 13-test regression file; verified by MY OWN injection rather than trusting the worker's removed injection.

**Verdict: PASS — zero gaps → pending-ship (DM).**

- **AC1** (fail on real failure): injected `assert False` into the gated set (via `discover_static_modules` override) → `run_static_tests()` = **False**, `[static-gate] FAIL — 1 failure(s)`.
- **AC2** (full run reaches summary+junit): real `python tests/run_tests.py static` → `[static-gate] PASS — 4547 gated test(s) passed`, EXIT 0; verdict line proves junit parsed = session reached session-finish.
- **AC3** (incomplete-run guard, the original bug): injected real `os._exit(0)` → process hard-exited mid-run, no junit → `run_static_tests()` = **False**, `[static-gate] FAIL — INCOMPLETE RUN`. Pre-fix returned false-green True.
- CONTROL passing-set → True (no false-positive). Injection verdict: `PASS (control=True, fail=False, hardexit=False)`.
- Regression suite `test_12408_static_gate_completeness.py` 13/13.

## Design assessment
`_static_gate_verdict()` is cause-agnostic: requires a parseable junit (>0 tests, 0 failures/errors) as positive proof of session-finish, fails closed on missing/malformed/empty junit (a missing junit = the hard-exit signature). Unique-temp-junit + unlink-placeholder + finally-cleanup avoids stale-file false positives + leaks. Exactly the issue's suggested fix #2.

## Scope / process
- The specific ~56% culprit was already fixed by #12720; this PR hardens the gate class — correct separation.
- Change isolated to run_tests.py static-gate path + test file; integration untouched. **No CQ** (no LLM-consumed instruction change). DS NO_FINDINGS.
- Posted PASS verdict comment BEFORE transition (clears unread-feedback guard); `transition 12408 pending-test pending-ship --role verifier-lead`.
- **Merge deferred to DM** — PR `Closes #12408` would auto-close + skip DM on a QA-merge. Counter NOT bumped (DM owns).
- No config.md revert hazard this time (branch freshly off fcc249b01); verified intact on return to main.
- Artifacts on main: TEST-PLAN-12408.md, QA-RESULTS-12408.md.
