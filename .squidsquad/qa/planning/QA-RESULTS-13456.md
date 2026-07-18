# QA-RESULTS-13456 — harness deploy-pull survives untracked-file collision

**Verdict: PASS (in scope) — zero gaps on the item's ACs.**
**Verifier**: qa (verifier-lead). **PR**: #13466 (branch squidsquad/task/13456). **Type**: type:issue (bug, auto-approved).

## Verification approach

Independent TEST-PLAN-13456.md derived from the PM bug report + fix contract, NOT the worker diff. Called the REAL `harness._safe_pull_in_clone` against REAL temp git clones (helper runs git with cwd=clone_path, harness.py:4971 — cleanly testable, unlike git_ops which pins REPO_ROOT).

## AC walk

| AC | Criterion | TC | Result |
|----|-----------|----|--------|
| AC1 | untracked local file at now-tracked path -> survive, pulled/tracked content wins, not MERGING | TC-1 | PASS |
| AC2 | #13215 dirty-tracked regression still survives, pulled wins | TC-2 | PASS |
| AC3 | genuine committed conflict -> ok=False (routes to recovery), origin not falsely synced | TC-3 | PASS |
| AC4 | real-git regression test present (untracked + #13215) | TC-4 | PASS |
| guard | clean/up-to-date pull is a safe no-op, no leaked stash | TC-5 | PASS |

## Test runs

- Independent verifier tests (TEST-13456-tests.py): **5 passed, 1 xfail** (the pre-existing gap below).
- Worker regression test (tests/test_feat_13456_deploy_pull_untracked_collision.py): **2 passed**.
- Full static gate (python tests/run_tests.py): **53 tests OK**, exit 0.

## Side-effect finding (OUT OF SCOPE for #13456 — filed separately)

During AC3 testing I found: a GENUINE committed conflict leaves the first `git pull --no-rebase` in MERGING state; `git stash` then fails on the unmerged index, so `_safe_pull_in_clone` returns `stash-failed` and the early-return fires BEFORE the retry-branch `git merge --abort` runs -> `.git/MERGE_HEAD` LINGERS. This contradicts the function's docstring ("a lingering MERGE_HEAD makes the NEXT deploy's checkout main fail -> recurring deploy-error loop").

**Scoping**: this is NOT introduced by #13456 (plain `git stash`, the pre-#13456 code, also fails on an unmerged index) and is OUTSIDE #13456's scope (the untracked-collision case aborts PRE-merge — no MERGE_HEAD is created — TC-1 confirms `not MERGING`). Documented as `test_tc_03b_...PREEXISTING_GAP` (xfail). Filed separately to skill (harness.py lane), cross-ref #13456. Does NOT block #13456.

## Decision

#13456's ACs are all observably satisfied against live temp clones; #13215 regression preserved; full suite green. Zero in-scope gaps. -> PASS: verdict comment (this session posted BEFORE the pending-ship transition per the #13464 ordering fix) + merge PR #13466 + Pending Ship. Pre-existing MERGING gap tracked as a separate low-sev finding.
