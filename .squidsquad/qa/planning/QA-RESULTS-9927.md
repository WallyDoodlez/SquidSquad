# QA Results — #9927 (model_router.py setup_provider: platform.system() → sys.platform)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 11:01 cycle 730
**PR**: #9929 (branch `squidsquad/task/9927`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Acceptance Criteria

| # | AC | Evidence | Result |
|---|----|----------|--------|
| 1 | `import platform` removed from `model_router.py` | Diff at model_router.py:903-906 deletes `import platform as plat`. `grep -n "platform" references/scripts/model_router.py` returns only the explanatory comment (lines 906-907) and `sys.platform ==` branches (lines 910, 912). | PASS |
| 2 | `plat.system()` / `platform.system()` calls removed | Same diff replaces `system == "windows"/"darwin"` with `sys.platform == "win32"/"darwin"`. Zero live `.system()` calls on any platform alias remain. | PASS |
| 3 | Behavior preserved (Windows = `os.startfile`, macOS = `open`, else = `xdg-open`) | Diff retains the three branches and their bodies verbatim; only the platform-detection expression changed. | PASS |
| 4 | AST-based hygiene tests added | `TestNoPlatformSystem9927::test_no_platform_system_calls` walks the AST asserting (a) no `import platform [as <alias>]` and (b) no `.system()` calls on any platform alias. `test_setup_provider_uses_sys_platform` uses `inspect.getsource` to lock the `sys.platform == "win32"` branch in `setup_provider`. | PASS |
| 5 | Regression: full module test suite green | `pytest tests/test_model_router.py` → **85 passed in 0.28 s** (matches PR-body claim of 85; 83 + 2 new). | PASS |

## Test runs

- Targeted: `pytest tests/test_model_router.py -k 9927` → **2 passed in 0.16 s**.
- Full module: `pytest tests/test_model_router.py` → **85 passed in 0.28 s**.

## Notes

- This is the seventh and final file in the `e7a47737` sweep family (six were swept in the original commit; `model_router.py` was the miss). The fix pattern is identical: `sys.platform` compile-time constant replaces the runtime WMI-triggering `platform.system()`.
- Per the PR body, `setup_provider` is gated behind a user-invoked CLI subcommand, so this was never a routine-path blocker. Closure is hygiene + future-proofing.
- The new `test_no_platform_system_calls` is module-scoped (only `model_router.py`). My #9928 (filed cycle 729) proposes a repo-wide AST scan across `references/scripts/` — that remains additive and still warranted even after #9927 ships, since a single-module check still allows the next file added to the directory to drift in undetected.

`mergeable: MERGEABLE, mergeStateStatus: CLEAN, isDraft: false`.
