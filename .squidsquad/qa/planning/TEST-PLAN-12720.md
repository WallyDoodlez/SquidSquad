# TEST-PLAN #12720 — `pytest tests/` false-green / hard-exit at ~58%

**Derived from my own cy291 filing.** The bug I filed has two defects; this PR scopes to **defect A**
(the masker) + a preventive guard, and triages defect B. ACs reflect that scope. Code-only (test
infra) → no comprehension gate.

## ACs
- **AC1 (defect A fixed — suite completes honestly)**: a full `python -m pytest tests/` reaches
  `sessionfinish` — prints a summary line, writes `--junitxml`, and the exit code reflects real
  outcomes (no more exit-0/no-summary truncation at ~58%).
- **AC2 (root cause fixed)**: `test_post_shutdown_returns_202` no longer arms a delayed real
  `os._exit(0)` from the `shutdown` daemon thread; it joins the thread inside the os._exit/time.sleep
  patch window so the MOCK fires. Test passes.
- **AC3 (regression guard, per my filed recommendation)**: a conftest guard fails loudly when a test
  leaves a live non-daemon thread OR the dangerous `shutdown` daemon thread alive after teardown.
  Guard classification is locked by self-tests AND produces zero false-positives on the real suite.
- **AC4 (no new failures / honest unmasking)**: the fix (test-side only) introduces no new failures;
  the failures the suite now surfaces are all pre-existing (were masked by defect A), not #12720
  regressions.

## Test Cases
| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | AC1 | full `pytest tests/ --junitxml=<abs>` | reaches summary; junitxml written + parses; exit 1 (honest) |
| TC2 | AC2 | run `test_post_shutdown_returns_202` | passes; daemon `shutdown` thread joined in patch window |
| TC3 | AC3 | run `test_12720_thread_leak_guard.py`; inspect guard for the `shutdown`-daemon case; count guard-induced failures in the full run | 6 pass incl. dangerous-daemon catch; 0 false-positives across 4788 tests |
| TC4 | AC4 | group full-run failures by file; classify each cluster | all pre-existing: 39 test_agent_boundaries (#10360), 1 test_compose, 1 test_vault (main-data), ~53 env-dependent live tests (claude CLI / API keys); 0 #12720-caused |

## Scope notes
- **Defect B triaged, not fully closed here** (legitimate, per skill): test_vault fix lands on main
  data (not this PR's code — so it still shows on the bare branch); 39 test_agent_boundaries blocked on
  #10360; ~53 comprehension/model_router_live/wake_mode failures are environment-dependent (need live
  LLM/CLI). None are in #12720's code scope.
- Verified on the bare task branch (without main merged) — so test_vault's 1 failure is expected here.
