# TEST-PLAN-13654

Derived independently from the issue body (`ISSUE: PR closing-keyword auto-close bypassing DM ship gate has recurred at scale post-#13371 (12 closed issues stranded)`). Severity: high — this defect closed 12 issues (3 of them mine: #13531/#13551/#13652) outside DM's ship gate this session. DM's remediation half (repair-status-labels + ship-counter reconciliation) is out of scope here; this plan covers skill's root-cause fix only.

## ACs derived from the issue

- **AC1**: `pr_merge()` calls a pre-merge neutralization checkpoint unconditionally, before the merge attempt, regardless of how the PR was created (covers the confirmed root cause: a bare `gh pr create` bypasses `pr_create()`'s own #13371 guard entirely).
- **AC2**: The checkpoint correctly detects and neutralizes closing keywords (Fixes/Closes/Resolves) in the *live* PR body by actually patching it on GitHub before merge — an already-clean body triggers no unnecessary edit.
- **AC3**: Fail-open: a `gh` hiccup at this checkpoint must never crash/block a merge that already passed every other gate — only warn.
- **AC4**: The checkpoint runs even on a PR later refused by another gate (state/scope-violation), so a keyword never survives to a human's manual retry.
- **AC5 (critical)**: This fix must actually reach — and work inside — the harness's canonical `/merge` endpoint path (the one every agent, including verifier, triggers via `POST /merge`), not just a standalone script invocation.
- **AC6**: No regressions — full static gate passes; existing `pr_merge` tests correctly updated for the new pre-merge `gh pr view` call.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC6 | Read the `pr_merge()` diff — confirm `_neutralize_pr_body_before_merge(pr_number)` is called unconditionally near the top, before the merge attempt |
| TC2 | AC2/AC3/AC4 | `tests/test_13654_pre_merge_body_neutralize.py` (8 cases) — mocked-plumbing coverage |
| TC3 | AC2 (live, not mocked) | Create a real, disposable scratch PR in the actual repo with a literal "Fixes #999999" body, checkout the fix branch, call the real (unmocked) `_neutralize_pr_body_before_merge(pr_number)` against it via `gh` — confirm the body is actually patched on GitHub |
| TC4 | AC5 | Read `harness.py`'s `POST /merge` handler (`_do_merge`) — confirm it calls `git_ops.pr_merge(pr_number)` directly, so the fix covers the exact path used every time an agent (including me) ships via the canonical harness merge |
| TC5 | AC6 | `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |

## Note
This is the exact merge path I use every single verification cycle (`POST /merge` → `git_ops.pr_merge`). TC3's live test is the load-bearing check — the mocked tests only prove the code *calls* `gh pr edit`, not that the call actually *succeeds* against real GitHub in this environment.
