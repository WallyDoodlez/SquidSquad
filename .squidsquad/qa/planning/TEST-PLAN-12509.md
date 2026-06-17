# TEST-PLAN #12509 — bare `pytest tests/` fails collection (harness basename shadow)

**Derived from the issue's success criterion** (my filed "Notes for fix": "confirm `pytest tests/`
collects + runs clean afterward, and that `run_tests.py` still works"). Test-only change → no
comprehension gate.

## ACs
- **AC1 (collection)**: a bare `python -m pytest tests/` collects with NO errors (the reported
  2-error collection abort is gone).
- **AC2 (runs clean)**: the previously-colliding modules execute and pass; a bare `pytest tests/`
  run does not introduce new failures.
- **AC3 (integration intact)**: `tests/run_tests.py` still works (renamed import wired through).
- **AC4 (regression guard)**: a regression test locks the fix (re-introducing a colliding basename
  fails) — AND the regression test must not itself break the suite (isolation).
- **AC5 (no regression)**: integration tests that imported the old `harness` helper still import +
  pass under the new name.

## Test Cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | `pytest tests/ --co -q` | clean collection, 0 errors |
| TC2 | AC2 | run previously-colliding modules together + full-run ordering | all pass, no new failures |
| TC3 | AC3 | `tests/run_tests.py` | integration green |
| TC4 | AC4 | inspect + run test_12509_no_harness_basename_shadow.py (alone AND with neighbors) | guards the basename AND does not contaminate other modules |
| TC5 | AC5 | run tests/integration importers under renamed helper | green |
