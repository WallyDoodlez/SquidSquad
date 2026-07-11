# TEST-PLAN-13185 — tracker.py work-assign cp1252 UnicodeEncodeError

**Source**: GitHub issue #13185 (Observed/Impact/Reproduction — no explicit AC block).
**Derived without reading the diff.**

Deterministic script (`tracker.py` CLI stdout). Implicit ACs from the report:

- **AC-1** — The work-assign success print no longer crashes on a cp1252 console
  (no `UnicodeEncodeError` from a decorative non-ASCII glyph).
- **AC-2** — A successful work-assign exits 0 (not 1+traceback) — the side effect (wake emit)
  already landed, so the CLI must report success, eliminating the false-failure → double-emit retry.
- **AC-3** — Regression test that reproduces the cp1252 crash pre-fix and guards against
  reintroduction of a decorative non-ASCII char in the crash-site print.

## Test Cases

### TC-1 (AC-1, AC-3): cp1252 crash reproduced pre-fix; not after
- **Expected**: writing the original `→` success line to a strict cp1252 stream raises
  `UnicodeEncodeError` (baseline); after `_harden_stdio` (`errors="backslashreplace"`) the
  same char does not raise.
- **Verification**: pytest `test_regression_cp1252_arrow_crashes_without_hardening`,
  `test_hardening_makes_cp1252_unencodable_char_not_raise`, `test_harden_stdio_sets_backslashreplace`,
  `test_harden_stdio_safe_when_stream_not_reconfigurable`.

### TC-2 (AC-1): success-line crash site is now ASCII
- **Expected**: `work_assign` success print uses `->` (ASCII), no `→`. Confirmed at the real
  crash site (origin/main:1732 had `→`; fixed to `->`).
- **Verification**: pytest `test_work_assign_success_line_is_ascii` + `git show origin/main` diff.

### TC-3 (AC-2): CLI hardening at main() entry
- **Expected**: `_harden_stdio()` is called at CLI `main()` (CLI-only, not at import — tracker.py
  is also imported as a library), best-effort, leaves non-reconfigurable streams as-is.
- **Verification**: read the diff; pytest harden tests above.

### TC-4 (no regression): full gate green
- **Expected**: `tests/test_tracker.py` green; full `tests/run_tests.py` green.

## Coverage matrix
- AC-1 → TC-1, TC-2 ; AC-2 → TC-3 ; AC-3 → TC-1, TC-2 ; guard → TC-4

## Comprehension Questions
N/A — deterministic script code, not LLM-consumed instruction. No CQ spec.
