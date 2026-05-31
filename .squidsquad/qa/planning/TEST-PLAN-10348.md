# TEST-PLAN-10348 — health_check._read_interval catches SystemExit

**Source**: GitHub issue #10348 (bug, improvement-scan).
**Derived without reading the diff.**

## Test Cases

### TC-1 (covers root-cause fix): SystemExit from config.get_field returns default 30
- **Precondition**: `references/scripts/health_check.py` loaded.
- **Steps**: monkey-patch `config.get_field` to `side_effect=SystemExit(1)`; call `_read_interval()`.
- **Expected**: returns 30 (the documented fallback); does NOT abort the process.
- **Verification**: live probe — returned 30, PASS.

### TC-2 (regression guard): KeyboardInterrupt propagates
- **Precondition**: same.
- **Steps**: monkey-patch `config.get_field` to `side_effect=KeyboardInterrupt`; call `_read_interval()`.
- **Expected**: raises `KeyboardInterrupt` (not silently swallowed). Locks in DS review iter-1 finding (don't widen to `BaseException`).
- **Verification**: live probe — KeyboardInterrupt propagated, PASS.

### TC-3 (cleanup): dead imports removed
- **Precondition**: file diff vs main.
- **Steps**: parse module imports.
- **Expected**: `os`, `platform`, `subprocess` no longer imported (grep-confirmed unused per issue body).
- **Verification**: live probe — only `io, json, re, sys, time, pathlib.Path, process_utils.is_process_alive` remain, PASS.

### TC-4 (canonical suite): full suite green
- **Steps**: `python tests/run_tests.py`.
- **Expected**: all tests pass, no new failures.
- **Verification**: live — 52 passed / 2 skipped / 0 fail.

## Coverage matrix
- Root-cause fix (SystemExit handling) → TC-1, dev's `test_system_exit_returns_default`, TC-4
- Drift guard (KeyboardInterrupt) → TC-2, dev's `test_keyboard_interrupt_propagates`, TC-4
- Cleanup (dead imports) → TC-3, TC-4

## Comprehension Questions
Not required — Python code only.
