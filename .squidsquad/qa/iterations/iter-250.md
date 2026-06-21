# Iteration 250 — 2026-06-16 (POLLING) — IMPROVEMENT SCAN

**Pull**: up to date. **Pickup**: canonical PT scan → **0 items**.

**Improvement scan (QA test-surface, extended-idle window):** investigated the cy223 test-collection collision.

**Finding → filed #12509 (skill, medium):** a bare `python -m pytest tests/` FAILS at collection (2 errors) — `tests/integration/harness.py` (integration test-helper) shadows `references/scripts/harness.py` (agent supervisor, defines `HarnessState`) because they share basename `harness`, there's no pytest `importmode`/config, and the test dirs aren't packages. Under default `prepend` import mode, collecting both integration helpers + unit tests registers the wrong `harness` in sys.modules → unit tests' `from harness import HarnessState` fail. Each affected test passes in isolation (test_12460 → 24/24 alone), so it's a misleading collection artifact, not a real failure. Repro + candidate fixes (importmode=importlib / rename / package-ize) in the issue. QA files, worker fixes.

**Dedup**: no existing issue (searched). **No vault write** — well-known pytest duplicate-basename gotcha, low team-reuse value.

**Pickup**: nothing pending-test. Pipeline still held upstream (#12493/#12492 gates, #12506 PM arch). #12419/#12420/#12450/#12451 approved.

**Outcome**: productive (filed #12509). Quiet-cycle counter → 0. Watch: #12493, #12492, #12509 (now skill's).
