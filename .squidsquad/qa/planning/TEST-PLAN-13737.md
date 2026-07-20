# TEST-PLAN-13737

Derived independently from the issue body (`type:issue` — Observation/Reproduced-live/Impact/Location/Suggested-fix bug report). Not read from the PR diff before writing this plan. This is my own filed finding; verifying it to the same bar as any other item.

## ACs (from issue body)

- **AC1**: `_discover_files()` correctly resolves the current `TEST-PLAN-<N>.md`/`QA-RESULTS-<N>.md` convention — no longer returns `(None, None)` for real, existing files.
- **AC2**: The legacy `*-<N>-TEST-PLAN.md` shape (pre-#9184 in-flight tasks) still resolves correctly — the fix must not break backward compatibility for anything still using the old naming.
- **AC3**: The QA/verifier planning directory is preferred appropriately, matching #9184's ownership model (verifier owns TEST-PLAN/QA-RESULTS under the #9184 convention).
- **AC4**: Once `_discover_files()` resolves real files, the downstream `check_coverage()` gate in `tracker.py`'s `transition()` actually fires (not just the discovery step) — i.e., the full pending-test → pending-ship path now genuinely enforces TC coverage.
- **AC5**: My own QA-RESULTS files (now including a TC-results table per #13738's resolution) pass the gate cleanly — confirming #13737 + #13738 together restore full, correct enforcement without a regression that blocks legitimate ships.
- **AC6**: Regression tests exist (skill's comment: 5 new tests).

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 (live) | `_discover_files(13735)` and `_discover_files(13731)` — confirm both resolve to real, existing paths (not `(None, None)`). |
| TC2 | AC2 (live) | Construct a real disposable legacy-named file pair (`*-<N>-TEST-PLAN.md` shape) and confirm `_discover_files()` still finds it. |
| TC3 | AC3 | Confirm the qa/verifier planning dir is checked/preferred per the fix's logic. |
| TC4 | AC4 (live, the real gate) | Run a real `tracker.py transition <N> pending-test pending-ship` end-to-end (using a disposable/already-shipped issue number for a dry check, or trace the code path) and confirm `check_coverage()` actually executes and its exit code is honored — not just that discovery succeeds. |
| TC5 | AC5 (live) | Run `check_coverage()` against my own `TEST-PLAN-13738.md`... (N/A, no PR) — use `TEST-PLAN-13735.md` / `QA-RESULTS-13735.md` and confirm a real coverage computation now happens (not 0/0 or an error) — full TC-to-result mapping resolves correctly. |
| TC6 | AC6 | Run skill's new regression tests. |
| TC7 | (regression) | Full test suite / static gate. |
