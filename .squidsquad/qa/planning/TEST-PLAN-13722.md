# TEST-PLAN-13722

Derived independently from the issue body (`type:issue` — Observation/Location/Impact/Suggested-fix bug report). Not read from the PR diff before writing this plan.

## ACs (from issue body)

- **AC1**: `read_state()`'s `armed` coercion no longer treats a hand-edited JSON string `"false"` as truthy. The exact reported repro (`{"armed": "false", "scan_count": 0, "last_run": null}`) must produce `armed: False` after `read_state()`.
- **AC2**: The mirror case — a string `"true"` — is also treated as type corruption (not a trusted signal), not just the `"false"` direction.
- **AC3**: The safe failure direction is `False` (a wrongly-disarmed driver just re-arms on the next idle wake; a wrongly-armed one keeps scanning against explicit operator intent) — confirm non-boolean/non-`True` values (numeric, other strings) all coerce to `False`, not `True`.
- **AC4**: The normal, non-corrupted round-trip (real JSON `true`/`false` written by `write_state()`) is unaffected — no regression to legitimate programmatic use.
- **AC5**: Regression tests exist covering the exact repro, the mirror case, a numeric variant, and the normal round-trip sanity check.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | Write the exact repro JSON (`{"armed": "false", ...}`) to a real state file, call `read_state()` against it, confirm `armed == False`. |
| TC2 | AC2 (live) | Write `{"armed": "true", ...}` (string), confirm `armed == False` (corruption, not trusted). |
| TC3 | AC3 (live) | Write `{"armed": 1}` (numeric) and `{"armed": []}` (other type), confirm both coerce to `False`. |
| TC4 | AC4 (live) | Round-trip: `write_state()` a real state with `armed: True`, then `read_state()` it back — confirm `armed == True` unchanged. Same for `armed: False`. |
| TC5 | AC5 | `python -m pytest tests/test_*.py -k subloop_driver` (or wherever skill placed the regression tests) — confirm all pass. |
| TC6 | (regression) | Full test suite / static gate. |
