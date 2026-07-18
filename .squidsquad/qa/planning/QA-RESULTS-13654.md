# QA-RESULTS-13654

## Summary
REJECTED — FAIL. AC2/AC5 fail on live evidence. PR #13655's `_neutralize_pr_body_before_merge()` calls `gh pr edit --body <...>` to patch the live PR body, but `gh pr edit` (any field, not just `--body`) unconditionally fails in this environment with a GraphQL error, because the installed `gh` CLI (v2.34.0, 2023) still queries the now-removed `repository.pullRequest.projectCards` field. Every real invocation hits the fix's own fail-open branch — a stderr warning, merge proceeds anyway — meaning the pre-merge checkpoint provides **zero actual protection** against the exact defect #13654 reports. This is not a hypothetical: I reproduced it against a real, disposable PR in this repo.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | `pr_merge()` diff: `_neutralize_pr_body_before_merge(pr_number)` called unconditionally right after the draft self-heal, before the merge attempt |
| AC2 | **FAIL** | Live repro: created scratch PR #13656 (`zz-verifier-scratch-13654-livetest` → `main`) with body `"Fixes #999999\n..."`. Checked out the fix branch (`squidsquad/task/13654`) and ran the real, unmocked `git_ops._neutralize_pr_body_before_merge(13656)`. Output: `WARNING: PR #13656 body carries an unneutralized closing keyword and the pre-merge edit failed: GraphQL: Projects (classic) is being deprecated in favor of the new Projects experience... (repository.pullRequest.projectCards) -- merge proceeding anyway (#13654)`. Confirmed reproducible and NOT `--body`-specific: `gh pr edit 13656 --title "..."` (no `--body` at all) hit the identical GraphQL error. `gh --version` → `2.34.0 (2023-09-06)` |
| AC3 | PASS (as designed) | The fail-open behavior itself worked correctly — no crash, no hang, just the warning above. The problem is that "fail-open" here means "silently never actually fixes anything," not a code defect in the fail-open branch itself |
| AC4 | PASS | `TestNeutralizePrBodyBeforeMerge::test_neutralize_runs_before_state_scope_and_behind_guards` — confirmed by reading the test, consistent with AC1's placement in the diff |
| AC5 | **FAIL (by consequence of AC2)** | Confirmed `harness.py`'s `POST /merge` → `_do_merge()` calls `git_ops.pr_merge(pr_number)` directly (`harness.py` ~line 4754) — so this IS the exact path I trigger every cycle via `POST /merge`. Since AC2 fails, every real merge through this path silently fails to neutralize, reproducing #13654's own root defect through the very code meant to fix it |
| AC6 | PASS | `tests/test_13654_pre_merge_body_neutralize.py` 8/8, `test_feat_1074_auto_merge.py` + `test_13447_pr_merge_post_merge_sync.py` re-run clean (27/27 total). Canonical static gate not independently re-run given the AC2/AC5 rejection — no value in re-confirming a green gate when the live mechanism itself is proven broken; the mocked tests are why this shipped believing it worked

## Root cause of the miss
The regression tests (`tests/test_13654_pre_merge_body_neutralize.py`) mock `git_ops._run_list` entirely, so they prove `_neutralize_pr_body_before_merge` *calls* `gh pr edit` with the right arguments — they cannot catch that the real `gh` binary in this environment always rejects that call. A confirmed root cause (#13371 self-neutralization working) does not mean the *new* call site (`gh pr edit`, a different subcommand than `gh pr create`) behaves the same way.

## Suggested fix direction (for skill)
`gh api -X PATCH repos/<owner>/<repo>/pulls/<N> -f body=<neutralized_body>` succeeds where `gh pr edit --body` fails — confirmed live against the same scratch PR immediately after the `gh pr edit` failure, restoring its body via the REST endpoint directly. Recommend routing `_neutralize_pr_body_before_merge`'s edit call through `gh api -X PATCH .../pulls/<N>` (or equivalent REST call) instead of `gh pr edit`, and add a regression test that cannot pass via mocking alone — or at minimum, note this environment's `gh` version constraint and confirm the fix against it before re-submitting.

## Scratch test artifact cleanup
PR #13656 and branch `zz-verifier-scratch-13654-livetest` (remote + local-tracking) closed/deleted, not merged. No production data touched.

## Zero-gap check
FAIL — see AC2/AC5. Routing back to skill.

## Verdict (round 1)
FAIL → in-progress, with reproduction evidence and a confirmed-working alternative.

---

# Round 2 (post-fix re-verification)

## Summary
VERIFIED — PASS. Skill routed `_neutralize_pr_body_before_merge()`'s edit through `gh api -X PATCH repos/:owner/:repo/pulls/<N> -f body=<...>` (REST) instead of `gh pr edit` (GraphQL), per my round-1 finding. Independently re-tested — not reusing skill's own live test (#13658) — with my own fresh scratch PR.

## AC Walk (round 2)

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | Unchanged — `pr_merge()` still calls the checkpoint unconditionally before merge |
| AC2 | **PASS** | Created scratch PR #13659 (`zz-verifier-scratch-13654r2-livetest` → `main`) with body `"Closes #999998\n..."` (deliberately a different closing keyword than skill's own test, for extra coverage). Checked out `squidsquad/task/13654` (round 2), ran the real unmocked `git_ops._neutralize_pr_body_before_merge(13659)` — output: `PR #13659: neutralized closing keyword(s) in body before merge (#13654)` (no warning this time). Confirmed via `gh pr view --json body`: `Closes #999998` → `Addresses #999998` on real GitHub |
| AC3 | PASS | Fail-open branch unchanged; not exercised this round since the primary path now succeeds |
| AC4 | PASS | Unchanged from round 1 |
| AC5 | **PASS** | Same `harness.py` → `pr_merge()` path confirmed; since AC2 now genuinely passes, the canonical `/merge` endpoint's real behavior is fixed |
| AC6 | PASS | `tests/test_13654_pre_merge_body_neutralize.py::test_never_calls_gh_pr_edit` (new) locks the regression. Idempotency confirmed live: re-running against the now-clean PR #13659 was silent (no unnecessary `gh api` call). Full re-run of all 3 affected test files: 28/28 pass. Canonical static gate independently re-run: **5701/5701 PASS, 0 failures**. `comprehension_staleness.py check`: clean |

## Scratch test artifact cleanup (round 2)
PR #13659 and branch `zz-verifier-scratch-13654r2-livetest` (remote + local-tracking) closed/deleted, not merged. No production data touched.

## Zero-gap check (round 2)
No gaps.

## Verdict (round 2)
PASS → pending-ship.
