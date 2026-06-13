# QA-RESULTS-11587 — ProactorEventLoop ConnectionReset recurs (uvicorn loop=auto defeats #9562)

**Verifier**: verifier-lead (qa)
**Date**: 2026-06-13
**PR**: #11722 (squidsquad/task/11587 → main)
**Branch verified**: squidsquad/task/11587 @ 744163552
**Verdict**: **PASS**

## Root cause / fix
#9562 set WindowsSelectorEventLoopPolicy on the main thread, but uvicorn ran with default
`loop="auto"` in a daemon thread → on Windows that resolves to asyncio_loop_factory which
HARD-CODES a ProactorEventLoop, bypassing the policy → the running server loop was Proactor
→ ConnectionReset (WinError 10054) recurred. Fix: `loop="none"` in `_build_uvicorn_config`
(harness.py:3099-3104) → uvicorn passes `loop_factory=None` to asyncio.run → the policy
governs → SelectorEventLoop (no ConnectionReset bug).

## AC Walk (behavior-mapped)

### AC: harness server loop is a SelectorEventLoop, not Proactor (the ConnectionReset cause)
**PASS — verified live against the installed uvicorn (0.41.0):**
  - `Config(loop="none").get_loop_factory()` → **None** (policy governs → Selector)
  - `Config(loop="auto").get_loop_factory()` → **ProactorEventLoop** (the bug)
This is the exact mechanism in the issue; the fix flips it on the real installed version.

### Regression tests
**PASS.** tests/test_11587_uvicorn_selector_loop.py — 6/6:
  - test_default_auto_loop_would_be_proactor_on_win32 — pins the bug
  - test_harness_config_loop_is_none / test_harness_config_loop_factory_is_none — pins the fix
  - test_none_factory_under_policy_yields_selector_on_win32 — THE KEY: None factory + policy
    yields SelectorEventLoop (proves the running loop is no longer Proactor)
  - test_helper_sets_loop_none + test_main_uses_build_uvicorn_config_helper — main() wires the helper
  - #9562 policy tests (3) still green — the main-thread policy set is intact and precedes the server.

## Test Execution
- `pytest test_9562_... test_11587_uvicorn_selector_loop.py` → **9 passed**, EXIT=0.
- `python tests/run_tests.py static` → EXIT=0, 2264 passed / 0 failed.
- skill full suite green; DS review NO_FINDINGS (cross-platform safe: Linux policy default is
  already Selector, so loop="none" is a no-op there).

## Note
The original symptom is "cosmetic today, latent wedge" — not deterministically reproducible as a
crash, so verification is mechanism-based: I confirmed on the real uvicorn that the server loop is
now Selector (the documented cause of the ConnectionReset is removed) and that main() wires it.

## Verdict
**PASS → pending-ship.** DM ships PR #11722.
