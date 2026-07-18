# TEST-PLAN-13664

Derived independently from the issue body (`ISSUE: l4_write_commit.py's git commit has no pathspec restriction -- can silently bundle unrelated staged changes into an L4 write commit`). Filed by skill-lead (improvement-scan). Success-path-only defect: the function's own code comment claimed a defense that only covered the push-failure revert path, not the success path.

## ACs derived from the issue

- **AC1**: `git commit` in `write_and_commit_l4()`'s Phase 2 is pathspec-restricted to the L4 file (`-- <relative>`), mirroring the existing `git add` restriction.
- **AC2 (critical, live)**: With a dirty staged index at entry (unrelated staged content present), the L4 write's commit does NOT sweep that content in — it remains staged, untouched, ready for its own future commit. Must be proven with REAL git subprocess calls, not a mocked runner (the existing test suite only asserts argv shape against a mock).
- **AC3**: The push-fail revert path (`pre_commit_sha` + `git reset --hard`) still works correctly — unaffected by the pathspec addition.
- **AC4**: No regressions — updated regression tests pass; full static gate passes.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 | Read the diff — `git commit -m subject -m body -- relative`, mirrors the `git add -- relative` pattern already in place |
| TC2 | AC2 (live, not mocked) | Built a real disposable git repo (bare + working clone, real local remote) with a pre-existing staged-but-uncommitted `unrelated_file.txt` change. Called the real (unmocked, `runner=None` → real `subprocess.run`) `l4_write_commit.write_and_commit_l4()` against it on the fix branch. Inspected the resulting commit via `git show --stat` and the post-call `git status --porcelain` |
| TC3 | AC2 (before/after) | Extracted the PRE-fix `l4_write_commit.py` from `main` (confirmed via grep it lacked the pathspec), ran it against an identical disposable repo with the identical dirty-staged precondition — confirmed the bug reproduces exactly as described (`unrelated_file.txt` swept into the commit) |
| TC4 | AC3 | `tests/test_l4_write_commit_c6.py`'s existing `test_push_fail_resets_to_pre_commit_sha_not_head_tilde_1` — re-run, still passing |
| TC5 | AC4 | `tests/test_l4_write_commit_c6.py` (24 cases, incl. the new `test_commit_is_pathspec_restricted_to_l4_file`); `python tests/run_tests.py static` (canonical gate); `comprehension_staleness.py check` |

## Note
All disposable test repos cleaned up (`rm -rf`) after inspection — nothing pushed to real origin, no production data touched.
