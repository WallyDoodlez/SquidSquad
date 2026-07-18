# QA-RESULTS-13551

## Summary
VERIFIED — PASS. All 6 ACs confirmed. My own filed issue (verifier-lead, from the #13454 rejection); fixed on `references/sub-skills/common/git-commit.md` (PR #13636, `squidsquad/task/13551`). Comprehension-tested per #9184 (this is an LLM-consumed sub-skill change) with an independently-authored CQ spec, not reused from the worker's PR.

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | New section: "prefer a new dedicated file — `tests/test_<issue-number>_<short-name>.py` — over appending a new test class to an existing shared file's tail" |
| AC2 | PASS | "Two independent branches that each append a class after the same anchor point... cannot be auto-ordered by git... the merge reports `mergeable=CONFLICTING/DIRTY` purely from insertion-position collision — not from any real code conflict." |
| AC3 | PASS | "Only extend an existing shared test file... when the test is a direct, tightly-scoped addition to that file's own existing coverage of the same function — not merely 'this fix happens to touch a function that file already tests.'" |
| AC4 | PASS | `tests/comprehension/13551_spec.json` authored independently by verifier. Fresh sonnet `general-purpose` subagent, file-only, no other tools/knowledge: 4/4 correct with accurate supporting quotes, zero `must_not` violations (preference+naming, conflict mechanism, carve-out condition, motivating history) |
| AC5 | PASS | `test_13551_test_file_placement_guidance.py` — 4/4 pass. Self-consistency check: the PR's own regression test IS a new dedicated file (`tests/test_13551_test_file_placement_guidance.py`), not an append to `test_git_ops.py` or any shared file — practices the guidance it locks in |
| AC6 | PASS | Canonical static gate independently re-run on the branch: **5677/5677 PASS, 0 failures**. `comprehension_staleness.py check` — exit 0 after registering the new `13551_spec.json` baseline (self-authored spec refreshed by verifier per the established #13574 precedent: CQ-spec baseline bookkeeping for a verifier-authored spec is verifier's own, not routed back to the worker) |

## Zero-gap check
No gaps.

## Verdict
PASS → pending-ship.
