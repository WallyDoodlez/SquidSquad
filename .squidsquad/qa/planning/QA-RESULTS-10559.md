# QA-RESULTS-10559 — gh pr edit broken by GitHub GraphQL projects-classic deprecation

**Verified**: 2026-06-01 00:18
**Branch**: `squidsquad/task/10559` @ `857bcc21`
**PR**: #10581 (MERGEABLE against main)
**Verifier**: qa-lead
**Result**: **PASS**

## Scope Check

PR touches exactly the 3 files the issue scope demands:
- `references/sub-skills/roles/dm/delivery-packaging.md` (source)
- `.squidsquad/dm/CLAUDE.md` (recomposed output)
- `tests/test_feat_6126_harness_merge.py` (assertion update)

## Acceptance Criteria

| # | AC | Evidence | Status |
|---|---|---|---|
| 1 | `delivery-packaging.md` route-back comment template no longer instructs `gh pr edit --base`; references `gh api -X PATCH ... -f base=...` form | Line 55 diff: comment template now reads `\`gh api -X PATCH repos/OWNER/REPO/pulls/[PR_NUMBER] -f base=$WORKING_BRANCH\``. Surrounding doc text still mentions `gh pr edit` once, but only to describe the deprecation bug ("`gh pr edit --base` is broken in this repo's installed `gh` (2.34.0)") — not as an instruction. | PASS |
| 2 | `test_feat_6126_harness_merge.py` route-back assertion updated to match the new instruction; intent preserved | Line 379 diff: assertion changed from `"gh pr edit" in block and "--base" in block` to `"gh api" in block and "base=" in block`. Failure message updated with deprecation context. Original intent ("comment must instruct worker to retarget the PR on GitHub") preserved. `pytest tests/test_feat_6126_harness_merge.py::TestTemplateUpdates -v` → **12 passed in 0.10s** | PASS |
| 3 | Full test suite green | **Targeted scope**: `TestTemplateUpdates` (the AC-relevant class) 12/12 pass. **Wider scope**: 12 pre-existing failures on branch, **all 12 also fail on origin/main baseline** (same count, same files: test_manifest, test_manifest_registry, test_installer_wiring, test_feat328_coverage, test_state_bus, test_feat_6126_harness_merge::TestEventReactionsTable). None of those failures are caused by or related to this PR — they reference a long-deleted `references/sub-skills/common/event-reactions.md` and other unrelated manifest/installer concerns. Skill's stated "52 passed, 2 skipped, 0 failed" refers to the unittest portion of `run_tests.py` (STATIC_TEST_MODULES), which is genuinely 52/2-skip/0-fail. | PASS (within PR scope) |
| 4 | `.squidsquad/dm/CLAUDE.md` recomposed so live DM instructions reflect the fix | Diff shows the composed file contains the same `gh api -X PATCH` instruction text as the source. The recompose was included in the PR, not deferred. | PASS |

## Test Methodology Notes

- Failure-baseline comparison done by running `python tests/run_tests.py` against both `origin/squidsquad/task/10559` and `origin/main` in clean worktrees. Both show 12 pytest FAILED markers in the same test files. Conclusion: pre-existing main-suite degradation.
- The `TestEventReactionsTable` 3-test cluster in the same file as the AC2 test fails because `references/sub-skills/common/event-reactions.md` is not present on either branch — that file appears to have been removed; the tests reading it should likely be removed or the file restored. **Not part of this issue's scope, but worth filing as a follow-up.**

## Outcome

All 4 ACs met within PR scope. The PR does NOT introduce regressions; pre-existing main-suite failures are tracked elsewhere (or worth filing). **Transitioning #10559: pending-test → pending-ship.**

## Follow-up suggestion (out of scope here)

File an ISSUE: tests reference deleted `references/sub-skills/common/event-reactions.md` — `test_feat_6126_harness_merge::TestEventReactionsTable` consistently fails on main and on every feature branch. Either restore the file or delete the tests.
