# TEST-PLAN-13944

tc_coverage.py's TC-table regex requires an isolated "TC-N" cell (LOW, type:issue, auto-approved, my own filed idle-scan finding).

## TCs

- **TC1 — table-cell fix, live**: does the fixed `_TC_TABLE_RE` correctly parse the established merged-cell convention (`| TC1 — description | PASS |`)?
- **TC2 — bullet fix, live**: does the new `_TC_BULLET_RE` correctly parse TEST-PLAN's bold-bullet TC declarations (`- **TC1 — description**: ...`)?
- **TC3 — regression against my own real artifacts**: run `tc_coverage.py --issue N` against all 4 of my own real TEST-PLAN/QA-RESULTS pairs from this session (#13863/#13865/#13855/#13847) — every one should now compute full coverage, not just the 2 skill cited.
- **TC4 — adversarial negative control**: does the fix still correctly detect a genuinely missing TC (plan declares 3, results only has 2) and still correctly capture a genuine FAIL result within a merged cell — i.e. it isn't just permissively passing everything?
- **TC5 — description-word hazard avoided**: confirmed the merged-cell result search skips the TC cell itself (the #2469 hazard class — a description containing "deferred"/"N/A" must not register as the result).
- **TC6 — regression coverage**: full `test_tc_coverage.py` file passes.
- **TC7 — ship gate**: full static + integration, byte-exact diffed against this session's established pre-existing-failure baseline to isolate anything genuinely new.
