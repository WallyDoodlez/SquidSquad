# TEST-PLAN-10348 — `health_check._read_interval` SystemExit handling

**Source**: GitHub issue #10348 body (Recommendation + "Out of scope but observed" cleanup).
**Derived without reading the worker's diff** — TCs are written against the issue's bug description and recommendation only.

## Acceptance criteria (extracted from issue body)

- **AC-1**: `_read_interval()` must return the documented 30-minute default when `config.get_field` raises `SystemExit` (the core bug — the function's documented fallback never fired because the previous catch list missed `BaseException` subclasses).
- **AC-2**: `_read_interval()` must continue to return 30 on the previously-caught `ImportError` / `ValueError` / `TypeError` (no regression of existing behaviour).
- **AC-3**: `_read_interval()` must NOT swallow `KeyboardInterrupt` — the issue's recommendation explicitly steers between two patterns (`BaseException` vs. a narrow tuple); a widening that catches `KeyboardInterrupt` would defeat Ctrl+C and is a forbidden drift.
- **AC-4** (out-of-scope cleanup the issue body says "drop in the same patch if it's quick"): the dead imports `os`, `platform`, `subprocess` are removed from `references/scripts/health_check.py`.

## Test Cases

### TC-1 (covers AC-1): SystemExit from config.get_field returns 30
- **Precondition**: import `health_check` from `references/scripts/`.
- **Steps**: patch `config.get_field` with `side_effect=SystemExit(1)`; call `health_check._read_interval()`.
- **Expected**: returns integer `30`.
- **Verification command**: `python -m pytest .squidsquad/qa/planning/TEST-10348-tests.py::test_tc_01_system_exit_returns_default -v`

### TC-2 (covers AC-1): live-system reproduction — running `python references/scripts/health_check.py` on a config.md missing the interval field exits cleanly, not 1
- **Precondition**: temp dir with a `.squidsquad/config.md` that has no `Iteration Interval > Minutes` field; run `health_check.py` against that cwd.
- **Steps**: `subprocess.run([sys.executable, "references/scripts/health_check.py"], cwd=tmp, ...)`.
- **Expected**: process exits with a documented code (0=healthy / 2=unknown), NOT with code 1 carrying the pre-fix `ERROR: Field 'interval' not found` line on stderr. AC-1's whole point is that the bug previously caused exit 1 here.
- **Verification command**: `python -m pytest .squidsquad/qa/planning/TEST-10348-tests.py::test_tc_02_live_no_exit_1_on_missing_interval -v`

### TC-3 (covers AC-2): ValueError still returns 30
- **Steps**: patch `config.get_field` to raise `ValueError`; expect `_read_interval() == 30`.
- **Verification command**: `python -m pytest .squidsquad/qa/planning/TEST-10348-tests.py::test_tc_03_value_error_still_returns_default -v`

### TC-4 (covers AC-3): KeyboardInterrupt propagates (drift guard)
- **Steps**: patch `config.get_field` with `side_effect=KeyboardInterrupt`; assert the interrupt re-raises through `_read_interval()`.
- **Verification command**: `python -m pytest .squidsquad/qa/planning/TEST-10348-tests.py::test_tc_04_keyboard_interrupt_propagates -v`

### TC-5 (covers AC-4): dead imports dropped
- **Steps**: read `references/scripts/health_check.py` as text; assert none of `^import os$`, `^import platform$`, `^import subprocess$` appear at module top level. AST-walk the module and confirm neither `os`, `platform`, nor `subprocess` is in its top-level imports.
- **Verification command**: `python -m pytest .squidsquad/qa/planning/TEST-10348-tests.py::test_tc_05_dead_imports_dropped -v`

### TC-6 (worker regression suite sanity): `tests/test_health_check.py` runs green
- **Steps**: `subprocess.run([sys.executable, "-m", "pytest", "tests/test_health_check.py", "-v"])`.
- **Expected**: exit 0; the two regression tests worker named (`test_system_exit_returns_default`, `test_keyboard_interrupt_propagates`) are present and pass.
- **Verification command**: `python -m pytest .squidsquad/qa/planning/TEST-10348-tests.py::test_tc_06_worker_regression_suite_passes -v`

## Coverage matrix

- AC-1 → TC-1, TC-2
- AC-2 → TC-3
- AC-3 → TC-4
- AC-4 → TC-5
- worker-test sanity → TC-6 (cross-validates AC-1 and AC-3 from the unit-test side)

Every AC appears in the matrix.

## Comprehension Questions

N/A — task changes a Python function and its tests only. No LLM-consumed instruction files modified.
