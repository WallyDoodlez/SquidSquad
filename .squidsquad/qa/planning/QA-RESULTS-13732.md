# QA-RESULTS-13732

## Summary
FAIL — back to In Progress. Skill's own investigation concluded this is flaky/resource-contention with "no code change needed." That conclusion is incorrect. This is the same test failure already root-caused in QA-RESULTS-13728.md (same branch, same underlying regression) — independently re-confirmed 100% deterministic here, not flaky.

## AC Walk
| AC | Result | Evidence |
|----|--------|----------|
| Skill's claim: flaky/resource-contention, no code defect | **FAIL (incorrect diagnosis)** | Ran the exact standalone repro skill used (`pytest tests/test_git_ops.py::TestPostMergeHookWiring13556::test_bare_merge_fires_hook_end_to_end`) 3x in a row with zero concurrent load: 3/3 failures, ~1s each, byte-identical `AssertionError`. This directly contradicts skill's "passed clean every time" standalone result. Root cause (already identified in #13728's rejection, posted before skill's #13732 investigation comments): `main()`'s new unconditional `harden_stdio()` import crashes with `ModuleNotFoundError` when `cli_stdio.py` isn't co-located with `git_ops.py` — exactly the isolated-copy scenario this test deliberately constructs. Not timing, not test ordering, not resource contention. |

## Zero-gap check
1 gap: an incorrect root-cause conclusion that would have shipped with the underlying #13556 safety-net regression (from #13728) still live and mischaracterized as environmental noise.

## Verdict
FAIL → In Progress. Same underlying fix as #13728 resolves this — see QA-RESULTS-13728.md. No separate action needed once #13728's harden_stdio import is fixed to fail open.
