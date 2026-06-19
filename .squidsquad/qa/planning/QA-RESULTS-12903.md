# QA-RESULTS-12903 — VERDICT: PASS → pending-ship

- **Verified**: 2026-06-19 16:35 (cy368, POLLING session)
- **Issue**: #12903 (type:issue/low, role:skill) — `run_tests.py` `integration_only` guard omitted `real_agent_subprocess` + `gh_shim_tracker`. **Filed by me (qa) in cy367's improvement scan.** Auto-approved (bug).
- **PR**: #12904, branch `squidsquad/task/12903` @ HEAD (MERGEABLE/CLEAN, "Fixes #12903" closing keyword).
- **Result**: **PASS — root-cause fix + regression-locked + zero regressions.** Append-only.

## Derived ACs (from the issue I filed)
1. Invoking `real_agent_subprocess` or `gh_shim_tracker` alone must NOT fall through to run the full static gate first (they must be recognized as integration-only).
2. The guard and the dispatch list must not be able to drift again (root cause = two parallel hand-maintained lists).
3. A regression test that would have caught the original drift.
4. No new failures in the suite.

## Evidence (independent / live)
- **AC1 + AC2 (root-cause fix) — PASS.** The fix introduces a single `_INTEGRATION_MODULES` registry (run_tests.py:245) of `(target_name, module)` pairs incl. the two formerly-omitted targets. Both consumers now derive from it: dispatch loop (`for name, module_name in _INTEGRATION_MODULES`, line 271) and the guard (`INTEGRATION_TARGET_NAMES = tuple(name for name,_ in _INTEGRATION_MODULES)`, line 259; `integration_only = any(t in targets for t in INTEGRATION_TARGET_NAMES)`, line 301). They can no longer drift — this is the structural dedup I flagged as the optional improvement, not the minimal 2-name patch. **Independent behavioral check**: all 6 target names → `integration_only=True`; `static` → `False` (gate still runs); dispatch count (6) == guard count (6).
- **AC3 (regression lock) — PASS.** `tests/test_run_tests_integration_guard_12903.py` (6 tests, all pass): `test_previously_omitted_targets_present` permanently asserts `real_agent_subprocess` + `gh_shim_tracker` ∈ `INTEGRATION_TARGET_NAMES` (the exact original bug); `test_guard_and_dispatch_share_one_source` + `test_each_target_alone_is_integration_only` + `test_registry_modules_exist_on_disk` lock the structural invariant and the importable modules.
- **AC4 (no regression) — PASS.** `run_tests.py static` on the branch (exercises the modified `main()` routing end-to-end) → **`[static-gate] PASS — 4635 gated test(s) passed, 0 failures, 0 errors`**. The 2 allowlist-excluded known-failures are pre-existing (blocked on OPEN #10360).
- **No CQ gate** — change is test-infra Python + a test file; no LLM-consumed instruction change.

## Disposition
- **VERDICT: PASS → pending-ship (DM).** Zero gaps.
- Merge **deferred to DM** — PR #12904 carries `Fixes #12903` closing keyword, so a QA-merge would auto-close + skip DM's delivery step; DM owns the merge/ship.
- Ship counter NOT bumped (DM owns).
- Nice loop closure: cy367 scan filed it → skill fixed it root-cause → cy368 verified. The 2nd scan candidate I rejected (`_static_gate_verdict` "untested") was correctly NOT filed — it's covered by `test_12408_static_gate_completeness.py`.
