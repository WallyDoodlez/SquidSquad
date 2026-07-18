# TEST-PLAN-13669

Derived independently from the issue body (`ISSUE: l4_conflict_preempt.preempt_conflict() crashes with raw IndexError/AttributeError on empty/None op_type, violating its own typed-exception contract`). Filed by skill-lead (improvement-scan), with an empirically-reproduced (unmocked) repro already in the issue body.

## ACs derived from the issue

- **AC1**: Empty-string and `None` `op_type` both raise `PreemptInvalidOpTypeError` (a `ConflictPreemptError` subclass) — not the raw `IndexError`/`AttributeError` from the issue's own reproduction.
- **AC2**: The guard fires before any `model_router` dispatch — a malformed `op_type` must never reach the (potentially expensive/LLM-backed) dispatch path.
- **AC3**: Legal `op_type` shapes (`"replace"`, `"replace step:cycle/file-bug"`) are unaffected — no over-tightening regression.
- **AC4**: No regressions — new + updated regression tests pass; full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live, not mocked) | Called the real `l4_conflict_preempt.preempt_conflict()` directly with `op_type=""` and `op_type=None` — confirmed both raise `PreemptInvalidOpTypeError` with a clear diagnostic message naming the bad value, reproducing the exact scenario from the issue but now correctly typed |
| TC2 | AC1 | Live: `issubclass(PreemptInvalidOpTypeError, ConflictPreemptError)` → `True` |
| TC3 | AC2 | `tests/test_13669_preempt_invalid_op_type.py::test_never_reaches_model_router_dispatch` — a poisoned `model_router` stub that raises on any attribute access proves the dispatch path is never reached for an invalid `op_type` |
| TC4 | AC3 (live) | Called the real function with `op_type="replace"` and `op_type="replace step:cycle/file-bug"` — both still return `result.decision == "skip"` as before, confirming no regression to legal shapes |
| TC5 | AC4 | `tests/test_13669_preempt_invalid_op_type.py` (7 cases) + `tests/test_l4_conflict_preempt_c8.py` (updated exception-hierarchy test) — 33/33 pass. `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |
