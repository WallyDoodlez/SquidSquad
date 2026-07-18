# TEST-PLAN-13551

Derived independently from the issue body (`ISSUE: IMPROVEMENT: worker branches routinely append to the same test-file anchor, causing recurring squash-blocking conflicts`). This is my own filed issue (verifier-lead, from an earlier session's #13454 rejection). Suggested fix offered three options ((a) cluster-aware rebasing, (b) dedicated-per-issue test files, (c) cluster-pickup sibling notes) — "any one closes it." Skill chose (b).

## ACs derived from the issue

- **AC1**: `git-commit.md` documents a clear preference for a new dedicated test file (`tests/test_<issue-number>_<short-name>.py`) over appending a new test class to an existing shared file's tail.
- **AC2**: The guidance explains the actual conflict mechanism — insertion-position collision (git can't auto-order two independent tail-appends), not a real code conflict — so future agents understand *why*, not just *what*.
- **AC3**: A carve-out exception is documented: only extend an existing shared file when the addition is a direct, tightly-scoped extension of that file's own existing coverage of the same function.
- **AC4 (independent CQ, #9184 hard gate)**: This is an LLM-consumed sub-skill (`git-commit.md`) change — a fresh agent given only the file must correctly derive AC1–AC3 plus the motivating history, with zero `must_not` violations.
- **AC5**: Regression test lock (`tests/test_13551_test_file_placement_guidance.py`) passes and the new PR's own regression test itself follows the newly-documented convention (a dedicated per-issue file, not an append) — a live self-consistency check.
- **AC6**: No regressions — canonical static gate passes; `comprehension_staleness.py check` clean.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1/AC2/AC3 | `gh pr diff 13636`; read the new "### Test-file placement (#13551)" section directly |
| TC2 | AC4 | Author `tests/comprehension/13551_spec.json` independently; spawn a fresh `general-purpose` (sonnet) subagent given ONLY `git-commit.md`, no other file/tool/prior knowledge; grade 4 questions |
| TC3 | AC5 | Run `test_13551_test_file_placement_guidance.py` (4 cases); confirm the file itself (`tests/test_13551_test_file_placement_guidance.py`, a new dedicated file, not an append to an existing shared file) practices what it documents |
| TC4 | AC6 | `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |
