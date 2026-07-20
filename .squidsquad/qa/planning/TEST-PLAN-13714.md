# TEST-PLAN-13714

Derived independently from the issue body (`type:issue` — Description/Impact/Steps-to-Reproduce/Expected/Actual bug report) plus PM's follow-up Discussion comment flagging a recurrence risk. Not read from the PR diff before writing this plan.

## ACs (from issue body + PM follow-up)

- **AC1**: The 3 exact runtime log paths (`.squidsquad/harness-errors.log`, `.squidsquad/harness-supervisor.log`, `.squidsquad/harness-supervisor.log.err`) are present in `.gitignore`.
- **AC2**: `git_ops.py commit-state`'s porcelain-based sweep excludes these paths even when real content exists on disk untracked (the exact repro: an untracked log with content still produces empty `git status --porcelain` output for that path).
- **AC3** (PM follow-up, load-bearing): `.gitignore` alone is inert while a file is already tracked — verify the 3 files are actually **untracked on main** at verification time, not just gitignored. A recurrence already happened once mid-fix (PM's commit-state re-swept them at `d16cdb9b4`, after skill's `.gitignore` fix at 23:01) — must confirm the untrack held through to the current branch/main tip, not assume it from the PR description.
- **AC4**: Regression test exists (`tests/test_13714_harness_log_gitignore.py` per skill's comment) covering the exact failure mode.

## Test cases

| TC | Maps to | Method |
|----|---------|--------|
| TC1 | AC1 | `grep` the 3 exact paths in `.gitignore` on the branch. |
| TC2 | AC2 (live) | Create a real file at each of the 3 paths with actual content (not a mock), run `git status --porcelain -- <path>`, confirm empty output for all three. |
| TC3 | AC3 (live, the real gate per PM's comment) | `git ls-files -- .squidsquad/harness-errors.log .squidsquad/harness-supervisor.log .squidsquad/harness-supervisor.log.err` on the branch tip AND on current `origin/main` — must return nothing for all 3 paths in both. This is not inferable from the diff; must be checked live against actual git-tracked state, since a second recurrence after the PR's diff was authored is exactly the failure mode PM flagged. |
| TC4 | AC4 | `python -m pytest tests/test_13714_harness_log_gitignore.py -v` — 3 cases per skill's comment. |
| TC5 | (regression) | Full test suite / static gate — confirm no new failures beyond the pre-existing, already-confirmed-unrelated `12818_spec.json`/`9184_spec.json` staleness gap (skill's comment already verified this exists on main independent of this PR; re-confirm still true, don't just trust the claim). |

## Note

PM's comment is the real teeth here: two prior "fixes" (gitignore entry, then an untrack) have already happened in sequence this session, and a live harness could re-sweep the files a THIRD time between now and merge. TC3 must be re-run at the moment of final verification (not cached from an earlier check), and again after merge as a sanity confirmation before shipping.
