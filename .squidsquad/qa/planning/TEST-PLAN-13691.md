# TEST-PLAN-13691

Derived independently from the issue body (`type:issue`, no separate CONTEXT.md — bug report with Description/Steps-to-Reproduce/Expected/Actual/Suggested-fix). Not read from the PR diff before writing this plan.

## ACs (from issue body)

- **AC1**: `pr_merge()`'s squash call always passes an EXPLICIT `--subject`/`--body` built from the (already-neutralized) PR title+body, so GitHub's implicit default-selection (PR body for multi-commit PRs, the sole commit's own message for single-commit PRs) is never reached.
- **AC2**: This closes the gap regardless of commit count — specifically the single-commit-PR case, where GitHub's default previously used the raw commit message (which can carry an unneutralized "Closes #N" a worker wrote in `git commit -m`, bypassing #13654's PR-body-only guard).
- **AC3**: The resulting squash commit that lands on the base branch must NOT contain a live closing keyword, even when the PR's sole commit message contains one and the PR body does not.
- **AC4**: Fail-open — if the pre-merge title/body fetch fails, the merge proceeds via the prior implicit-default behavior rather than being blocked.
- **AC5**: Scoped to `squash` strategy only (the project's locked merge strategy per `pr-protocol.md`) — no regression to the `merge` strategy path.
- **AC6**: Regression tests exist for the single-commit-PR case specifically; full suite and static gate pass.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC3 (live) | Real disposable single-commit PR against a scratch base branch (not `main`): PR body clean ("Addresses #<fake>"), the PR's sole commit message carries a raw "Closes #<fake>". Call the real unmocked `pr_merge()` (not mocked) and inspect the actual resulting squash commit on the scratch base branch. |
| TC2 | AC2 | Same live PR as TC1 is single-commit by construction — confirms the specific reported gap (single-commit default-selection) is closed, not just the already-covered multi-commit case. |
| TC3 | AC4 | Code read + existing unit tests (`test_13691_squash_merge_explicit_body.py`) — fetch-failure fail-open path; not independently live-reproduced (would require simulating a `gh` failure mid-merge, out of proportion to the risk — sanity-checked via code read: `if strategy == "squash" and neutralized_title is not None` guards the explicit-args branch, `(None, None)` on any fetch/parse failure falls through unchanged). |
| TC4 | AC5 | Code read: `if strategy == "squash"` gate on the new explicit-args block — a `merge`-strategy call never reaches it, unchanged from pre-fix behavior. Confirmed this repo's `pr-protocol.md` locks squash as the only strategy in use, so this is not a live gap. |
| TC5 | AC6 | `python -m pytest tests/test_13691_squash_merge_explicit_body.py -v` (9 cases, sanity check only) + full suite + canonical static gate. |

## Note

TC1/TC2 is the real gate — this is the exact bug class that has already bitten two real shipments this session (#13683, #13564), and #13654's own round-1 verification failure (a mocked test that missed a broken `gh` CLI call) is the precedent for why a live merge test is required here, not just the unit suite.
