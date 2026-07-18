# TEST-PLAN-13654 (round 2)

Round 1 rejected `_neutralize_pr_body_before_merge()`'s use of `gh pr edit` (broken in this environment — see QA-RESULTS-13654.md round-1 record below, preserved as history). Round 2 switches to `gh api -X PATCH .../pulls/<N>` per my own confirmed-working alternative. Independently re-verified — not trusting skill's own live test, even though they mirrored my methodology correctly.

## ACs (unchanged from round 1, restated)

- **AC1**: `pr_merge()` calls the neutralization checkpoint unconditionally, before the merge attempt.
- **AC2 (the one that failed round 1)**: The checkpoint actually patches the live PR body on GitHub — not just calls a command that appears to, but genuinely succeeds against the real API in this environment.
- **AC3**: Fail-open on a genuine `gh` hiccup.
- **AC4**: Runs even on a PR later refused by another gate.
- **AC5**: Reaches the harness's canonical `/merge` → `pr_merge()` path.
- **AC6**: No regressions; `gh pr edit` must never be called again (round-1's exact failure mode).

## Test cases (round 2 additions)

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC2 (live, independent) | Created my OWN fresh scratch PR (#13659, `zz-verifier-scratch-13654r2-livetest` → `main`, different closing keyword — "Closes" vs skill's "Fixes" — for extra coverage), not reusing skill's own #13658 test. Checked out the round-2 branch, ran the real unmocked `_neutralize_pr_body_before_merge(13659)` — confirmed via `gh pr view --json body` that `Closes #999998` became `Addresses #999998` on real GitHub |
| TC2 | AC2 (idempotency) | Re-ran the same function against the now-clean PR #13659 — confirmed silent no-op (no unnecessary `gh api` call, matching the "already-clean body" branch) |
| TC3 | AC6 | `tests/test_13654_pre_merge_body_neutralize.py::test_never_calls_gh_pr_edit` (new) + full re-run of all 3 affected test files: 28/28 pass |
| TC4 | AC1/AC3/AC4/AC5 | Unchanged from round 1 — re-confirmed via the same diff/handler reads |
| TC5 | round-2 regression | `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |

## Note
Scratch PR #13659 closed + branch deleted, never merged. My round-1 rejection is preserved in QA-RESULTS-13654.md as the historical record of what was wrong and why.
