# TEST-PLAN-13847

`cycle_pre.py`/`cycle_post.py`'s UTF-8 stdio guard runs at import time, violating `cli_stdio.py`'s documented CLI-entry-only contract (LOW, type:issue, auto-approved, my own filed idle-scan finding this session).

## TCs

- **TC1 — behavioral fix, live**: does importing `cycle_pre.py` as a library (not running `main()`) now leave `sys.stdout`'s encoding untouched, on a genuinely non-UTF-8 (cp1252) environment?
- **TC2 — crash protection preserved**: does the guard still fire correctly when the module IS run as a CLI entry (`main()`), preserving #13846's crash-proofing?
- **TC3 — both streams still guarded**: stdout AND stderr, matching the pre-fix behavior (cycle_pre/cycle_post guard both, unlike cycle.py's stdout-only).
- **TC4 — regression-proof against re-hoisting**: does the new AST-based placement test actually walk the AST (not just string-match), so a future accidental re-hoist to module scope would be caught?
- **TC5 — full relevant test files pass**: `test_cycle_pre.py`, `test_cycle_post.py`, `test_cycle.py`, `test_cli_stdio_13198.py`.
- **TC6 — ship gate**: no collateral regression.
