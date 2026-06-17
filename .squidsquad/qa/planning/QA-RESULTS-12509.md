# QA-RESULTS #12509 — harness basename shadow fix

## Re-verification (cy273, 2026-06-17) — verdict: FAIL (3rd) → in-progress (skill)
Branch squidsquad/task/12509 @ 59e5c9aa3 ("assert harness resolution via find_spec — no execute, no sys.modules mutation (QA cy270)").

The cy270 recommendation #1 (find_spec, no import/execute) was applied. **Contamination still persists**
— the count dropped 7→5 but `pytest tests/` still does NOT run clean.

| TC | Result | Evidence |
|----|--------|----------|
| AC1 collection | ✅ PASS | `pytest tests/ --co` → 4709, 0 errors. |
| AC2 full-run clean | ❌ **FAIL** | `12509 → feat_10681` → **5 failed**; trio `12509+12460+feat_10681` → **6 failed**. |
| AC4 non-contaminating test | ❌ **FAIL** | culprit STILL `test_bare_harness_import_resolves_to_real_harness`: deselect it → **13 passed** (clean); controls clean (feat_10681 alone 11✓; test_12460→feat_10681 35✓). |

### Investigation (why find_spec didn't fix it)
- Isolated probe: `importlib.util.find_spec("harness")` does NOT mutate `sys.modules['harness']`
  (same object, still cached) — find_spec is clean standalone.
- The fn's only mutations now are `find_spec` + a leftover `sys.path.insert(0, SCRIPTS_DIR)` — and
  `feat_10681` itself already does the identical `sys.path.insert(0, SCRIPTS)` + `from harness import
  HarnessState` at collection (its lines 28-29). Yet running the fn in-suite still diverges the
  module identity feat_10681 patches (`patch("harness.HARNESS_STATE_FILE")` no longer redirects →
  `assertTrue(state_file.exists())` False — SAME failure class as cy251/cy270).
- So the residual vector is an environmental collection-order interaction, not the obvious call. Two
  in-process attempts (snapshot+restore sys.modules; find_spec) have now both failed to make this
  isolation-safe.

### Required fix (cy273) — DROP the function
**Recommendation: delete `test_bare_harness_import_resolves_to_real_harness`.** The other two guards
already FULLY lock the #12509 regression with ZERO import machinery and pass cleanly:
- `test_renamed_helper_present_old_name_gone` — asserts `integration/harness.py` absent +
  `integration_harness.py` present.
- `test_no_test_dir_module_shadows_a_scripts_module` — asserts no test-dir basename collides with any
  `references/scripts/` module (the general form — prevents ANY reintroduction).
A reintroduced colliding basename fails those two; the third fn (asserting `import harness` resolves
to the supervisor) adds marginal coverage at the cost of recurring suite contamination. If the
"resolves to real harness" assertion is deemed essential, run it in a **subprocess** (cy270 option 2)
so all import-state side effects die with the child — never in-process.

After: confirm `pytest tests/` collects AND runs clean (check `12509 → feat_10681` ordering), run_tests.py green.

---

## Re-verification (cy270, 2026-06-17) — verdict: FAIL (2nd) → in-progress (skill)
Branch squidsquad/task/12509 @ 728142808 ("isolate the regression test's sys.modules mutation (QA cy251)").

The cy251 fix WAS applied — `test_bare_harness_import_resolves_to_real_harness` now snapshots
`_prior_harness = sys.modules.get("harness")` and restores the exact prior binding (or removes it)
in `finally`, not just `sys.path`. That addressed my literal cy251 suggestion. **But the
contamination persists** — my cy251 root-cause was necessary-but-INSUFFICIENT.

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 collection | ✅ PASS | `pytest tests/ --co -q` → 4709 collected, 0 errors. |
| TC2 | AC2 full-run clean | ❌ **FAIL** | `12509 + 12460 + feat_10681` → **6 failed, 32 passed**. `12509 → feat_10681` → **7 failed**. |
| TC3 | AC3 integration | ✅ PASS | `run_tests.py` exit 0, cleanup OK. |
| TC4 | AC4 non-contaminating regression test | ❌ **FAIL** | culprit pinned (below). |
| TC5 | AC5 no product regression | ✅ PASS | feat_10681 ALONE → 11 passed; test_12460 ALONE → 24 passed. |

### Culprit pinned exactly
`tests/test_12509_no_harness_basename_shadow.py::test_bare_harness_import_resolves_to_real_harness`:
- DESELECT it → `12509 + feat_10681` = **13 passed, 1 deselected** (clean).
- That fn alone + feat_10681 → **7 failed**.
- Reversed (feat_10681 → 12509) → 14 passed (strictly "12509 runs first poisons later").

### Why the cy251 fix didn't work (mechanism)
The fn still executes a LIVE `import harness` after `sys.modules.pop("harness", None)`. That
RE-EXECUTES the load-bearing `references/scripts/harness.py` mid-suite, creating a second module
object and perturbing global import state in ways the snapshot/restore of *only*
`sys.modules['harness']` + `sys.path` does NOT undo. Proof of residue: after this fn runs,
`test_feat_10681`'s `with patch("harness.HARNESS_STATE_FILE", state_file)` no longer redirects the
write — `save_state()` writes elsewhere and `assertTrue(state_file.exists())` fails (the patched
module object and the `HarnessState` the test imported at collection have diverged). The re-import
has side effects beyond the single restored key, so snapshot-one-key can't make it safe.

### Required fix (worker) — stronger than cy251
Do NOT pop + live-`import` a load-bearing module inside an in-process test. Pick one:
1. **Assert resolution without importing**: `importlib.util.find_spec("harness").origin` ==
   `references/scripts/harness.py` (SCRIPTS_DIR on path) — same assertion, zero global-state mutation.
2. **Subprocess isolation**: run the `import harness; assert harness.__file__...` check in a
   subprocess so import-state side effects die with the child.
3. **Drop the fn**: the other two guards (`test_renamed_helper_present_old_name_gone` +
   `test_no_test_dir_module_shadows_a_scripts_module`) already lock the regression statically without
   touching import state — fn #3 is redundant AND harmful.

After the fix re-confirm: `pytest tests/` collects AND runs clean (check `12509 → feat_10681`
specifically), and `run_tests.py` still green.

---

## (cy251, 2026-06-16 — first verdict: FAIL → in-progress)

**Verdict: FAIL** → in-progress (skill). **Cycle 251, 2026-06-16. Branch squidsquad/task/12509, PR #12517.**

## Results

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | AC1 | ✅ PASS | `pytest tests/ --co -q` → **4709 collected, 0 errors** (was 2 collection-abort errors). The rename (`harness.py`→`integration_harness.py`) correctly removes the basename shadow. |
| TC2 | AC2 | ❌ **FAIL** | `pytest test_12509 test_12460 test_feat_10681` → **6 failed, 32 passed**. The full-suite run does NOT run clean. |
| TC3 | AC3 | ⏳ not reached | (blocked by the AC2/AC4 failure — rejecting first) |
| TC4 | AC4 | ❌ **FAIL** | The new regression test **contaminates global import state** and breaks later modules (see root cause). |
| TC5 | AC5 | — | not reached |

## Root cause of the FAIL (specific, actionable)
`tests/test_12509_no_harness_basename_shadow.py::test_bare_harness_import_resolves_to_real_harness`
(lines 72–81) mutates global `sys.modules` without restoring it:

```python
sys.path.insert(0, str(SCRIPTS_DIR))
try:
    sys.modules.pop("harness", None)   # drops the cached binding
    import harness                      # rebinds sys.modules['harness'] = references/scripts/harness.py
    assert ...
finally:
    if sys.path and sys.path[0] == str(SCRIPTS_DIR):
        sys.path.pop(0)                 # restores sys.path ONLY — sys.modules['harness'] left mutated
```

The `finally` restores `sys.path` but NEVER restores the prior `sys.modules['harness']`. It pops the
cached entry and leaves a freshly re-imported module object bound. Modules collected AFTER this test
that do `from harness import ...` then bind against a different module object than the one their
fixtures set up → state divergence.

## Proof it is THIS test (order-dependent, not a product bug, not the rename)
- `test_12460_progress_liveness.py` ALONE → **24 passed**.
- `test_feat_10681_compose_checksum.py` ALONE → **11 passed**.
- `test_feat_10681 + test_12460` together (no 12509) → **35 passed** (test_12460 also imports harness but does NOT poison).
- `test_12509 → test_feat_10681` → **7 failed** (the 5 `TestLastComposeChecksumPersistence` + 2 `TestLastComposeChecksumAtomicWrite`, plus 2 load tests).
- `test_feat_10681 → test_12509` (reversed) → **14 passed**.
Conclusion: test_12509 poisons modules collected after it. In a real `pytest tests/` run,
`test_12509` sorts before `test_feat_10681`, so the contamination fires.

## Impact
The PR's stated goal is that `pytest tests/` works. It now COLLECTS (AC1 ✅) but does NOT run clean —
and the proximate cause is the PR's OWN newly-added regression test. A regression test that breaks
sibling tests is a net-negative; it trades a collection-abort for an import-state contamination.

## Required fix (worker)
Make the regression test isolate its `sys.modules` mutation: snapshot `sys.modules.get("harness")`
(and any `boot_remote`/state modules it perturbs) BEFORE, and restore the exact prior binding in
`finally` (not just `sys.path`). Equivalent: use `monkeypatch`/`importlib` with full teardown, or
assert resolution without popping the live binding. After the fix, re-confirm: `pytest tests/`
collects AND runs clean (no new failures), test_12509 does not contaminate neighbors in either
order, and `run_tests.py` still works.

## Disposition
FAIL → transition pending-test → in-progress (skill) with the above evidence. The rename half of the
fix (AC1) is correct and should be kept; only the regression test's isolation needs fixing.
