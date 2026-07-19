# QA-RESULTS-13691

## Summary
VERIFIED — PASS. All 6 ACs confirmed. Fixed on `references/scripts/git_ops.py` (PR #13704, `squidsquad/task/13691`). This is a live production instance of the closing-keyword bypass class that already hit #13683 and #13564 this session — the highest-stakes item I've verified today, since it protects the ship gate itself.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | Code read confirms `pr_merge()` now unconditionally calls `_neutralize_pr_body_before_merge(pr_number)` and, for `strategy == "squash"` with a successful fetch, appends `--subject`/`--body` built from the neutralized title/body to `merge_args` before the `gh pr merge` call — bypassing GitHub's implicit default-selection entirely. |
| AC2 | PASS (live) | TC1/TC2 below is a genuinely single-commit PR — the reported gap case — and the fix closes it. |
| AC3 | PASS (live, on 3rd attempt — see Note) | Real disposable single-commit PR #13707 (base: scratch branch `qa-scratch-13691-base`, never `main`) with a clean body ("Addresses #999997...") and a sole commit message carrying a raw "Resolves #999997". Ran the actual unmocked `git_ops.pr_merge(13707, strategy='squash')` **from the fix branch** (confirmed via `git branch --show-current` + `git log -1 -- git_ops.py` immediately before the call). Resulting squash commit on the base branch: subject `"qa scratch: 13691 single-commit test 3 (fix branch, take 3) (#13707)"`, body `"Addresses #999997 -- disposable scratch PR, take 3."` — **zero trace of "Resolves" or any closing keyword**; the raw commit message did not leak through. |
| AC4 | PASS (code read + unit tests) | `TestSquashMergePassesExplicitSubjectBody13691::test_squash_call_omits_subject_body_on_fetch_failure` passes; code confirms `if strategy == "squash" and neutralized_title is not None` guards the explicit-args branch, and `_neutralize_pr_body_before_merge` returns `(None, None)` on any view/parse failure, falling through to the prior implicit-default `merge_args` unchanged. |
| AC5 | PASS (code read) | The explicit-args block is gated on `strategy == "squash"` only; a `merge`-strategy call never reaches it. Confirmed via `pr-protocol.md` that squash is this project's locked (only) strategy, so this is not a live gap. |
| AC6 | PASS | `tests/test_13691_squash_merge_explicit_body.py` — 9/9 pass. Full suite: 5759/5759 PASS, 16 skipped (pre-existing exclusions), 12 subtests passed. Canonical static gate: 5787/5787 PASS, 0 failures, 0 errors. No LLM-consumed instructions touched (pure code + tests) — no CQ spec required, consistent with the #13531/#13564 precedent. |

## Zero-gap check
No gaps in the fix itself. See Note below for a self-caught methodology error during verification (corrected within the same pass, does not affect the verdict).

## Note — self-caught verification methodology error (2 false failures, then a genuine PASS)
My first two live-merge attempts (scratch PRs #13705, #13706) both showed the raw closing keyword surviving unneutralized in the resulting squash commit — which looked like the fix was broken. Root-caused before concluding anything: both attempts ran `pr_merge()` while my **local clone's working-tree checkout** was on a scratch branch built off pre-fix `origin/main` (not the `squidsquad/task/13691` fix branch) — `import git_ops` reads whatever `git_ops.py` is on disk in the current checkout, which is entirely independent of which remote branches the PR-under-test targets. Attempt #1 (#13705) incidentally reproduced the *original* bug empirically against genuinely-unfixed code (useful corroboration, not evidence against the fix). Attempt #3 (#13707), run after explicitly re-checking out `squidsquad/task/13691` and confirming via `git log -1 -- git_ops.py` immediately before the call, passed cleanly — see AC3. This is the same root cause the vault already documents in [[learning-prove-regression-test-fails-pre-fix]] ("use a detached `git worktree` for in-clone comparisons, not branch surgery on the shared checkout") — I did exactly the branch-surgery anti-pattern that note warns against, just for a live-merge test rather than a pre/post-fix diff. No new vault entry needed; this is a fresh instance confirming the existing lesson generalizes beyond its original pre-fix-comparison framing to any live test that imports/executes a script directly.

## Cleanup
All scratch artifacts removed: 3 disposable PRs (#13705, #13706, #13707) merged into a throwaway base branch (never `main`) and left as closed historical records; scratch base branch `qa-scratch-13691-base` and all scratch head branches deleted from origin (confirmed via `git fetch --prune`); all local scratch branches deleted; no marker files remain in the working tree on any real branch. No real issue numbers were used (999997/999998/999999 fabricated, non-existent) — no real GitHub issue was touched by the scratch merges.

## Verdict
PASS → pending-ship.
