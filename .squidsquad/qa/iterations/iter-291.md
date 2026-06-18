# Iteration 291 — 2026-06-17 11:09

**Mode**: POLLING. PT queue empty → improvement-scan task (productive work paused).

**Outcome**: **Filed #12720 (HIGH) — `pytest tests/` is a false green.** Major gate-integrity discovery.

## Trigger
Investigating a display anomaly noticed during #12509/#12574: full `pytest tests/` terminal summary +
junitxml swallowed at ~57-58%. QA skepticism — refused to dismiss it as cosmetic.

## Investigation (evidence chain)
1. Probe restoring fd1 after `pytest.main()` → my post-main prints NEVER ran → `pytest.main()` does not return; process dies mid-run.
2. `os._exit`/`sys.exit`-intercepting stack-dump shim → **shim never fired** → NOT os._exit/sys.exit via std `os` binding. Some harder/native exit yielding code 0.
3. `--ignore=tests/test_l4_file_watcher_e3.py` → still dies at ~58% → **position/time-based**, not that file (signature of a leftover thread/`threading.Timer`/uvicorn/watchdog from an earlier "live" test).
4. Clean uninstrumented run shows **real F/E** before the death: 1 F @16%, ~17E+~18F cluster @19%, 3F @45%.
5. `-x` halt → first failure = `test_agent_boundaries::test_ac4_composed_contains_l1_awareness_and_l2[pm]`; asserted string `"Know each other's responsibilities"` is in **no source** under `references/` → **stale test** (post-cutover drift, sibling to #11394).
6. Confirmed clean tree at origin/main HEAD (b02875ba6) → failures are on main, not my working copy.

## Disposition
- **#12720** filed (role:skill, severity:high, reporter qa) — full repro + ruled-out hypotheses + the two defects (A: truncation/false-green; B: masked stale/failing tests). Body set via `gh issue edit --body-file` (Write-tool /tmp ≠ bash /tmp — create-issue body came up empty first; fixed).
- **@pm flagged** on #12720 — whole-team gate concern.
- **Corrected #12509 QA-RESULTS** "4751 passed" overclaim (addendum): full-suite EXIT=0 was unreliable; verdict stands on collection + targeted + run_tests.py. #12574/#12525 verdicts unaffected (didn't rely on full-suite-green; #12574's no-regression run deselected the L4 killer).
- **Vault**: wrote `[[learning-suite-exit-code-not-proof-of-all-pass]]` (verifier-craft: exit 0 ≠ all-pass; require a positive completion signal — summary/junitxml/count).

**Quiet Cycle Counter**: 0 (productive — improvement filed).
