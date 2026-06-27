# QA-RESULTS-13185 — tracker.py work-assign cp1252 UnicodeEncodeError

**Verifier**: qa
**Date**: 2026-06-21 19:55
**Verdict**: PASS — zero gaps. Status → Pending Ship.
**Change under test**: PR #13199, branch `squidsquad/task/13185` (tracker.py + tests).

## AC walk (implicit from issue body)

| AC | Result |
|----|--------|
| AC-1 success print no longer crashes on cp1252 | PASS |
| AC-2 successful work-assign exits 0 (no false-failure → double-emit) | PASS |
| AC-3 regression reproduces pre-fix + guards reintroduction | PASS |

## Test Cases (isolated worktree of the branch)

### TC-1 (AC-1, AC-3) — cp1252 crash reproduced pre-fix, gone after — **PASS**
`test_regression_cp1252_arrow_crashes_without_hardening` (literal `→` raises UnicodeEncodeError on
strict cp1252 — the exact reported crash), `test_hardening_makes_cp1252_unencodable_char_not_raise`,
`test_harden_stdio_sets_backslashreplace`, `test_harden_stdio_safe_when_stream_not_reconfigurable`
all PASS.

### TC-2 (AC-1) — crash site now ASCII — **PASS**
`test_work_assign_success_line_is_ascii` PASS. Pre-fix proof: `origin/main:1732` still had
`print(f"work-assign → {target_alias} ...")` (the real crash site); fix replaces with `->`
(both the success print and the ERROR print on L1687).

### TC-3 (AC-2) — CLI hardening at main() entry — **PASS**
`_harden_stdio()` called at `main()` (CLI-only, never at import — tracker.py is also imported as a
library; reconfiguring a consumer's global stdio would be wrong), `errors="backslashreplace"`
(keeps the console encoding, escapes unencodable chars), best-effort with `(AttributeError,
ValueError, OSError)` guard for non-reconfigurable streams.

### TC-4 (no regression) — full gate — **PASS**
`tests/run_tests.py`: `4905 passed, 17 skipped, 12 subtests passed`; static-gate verdict
`PASS — 4934 gated test(s) passed (0 failures, 0 errors)`.

## Coverage matrix
- AC-1 → TC-1, TC-2 ; AC-2 → TC-3 ; AC-3 → TC-1, TC-2 ; guard → TC-4 ✓

## Notes
Deterministic script code — no CQ. Tests ship under `tests/` (preserved). No HUMAN-REQUIRED TCs.
Defense-in-depth (ASCII at the crash site + global stdio hardening) addresses both the specific
glyph and any future non-cp1252 char in tracker.py CLI output.
