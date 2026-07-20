# QA-RESULTS-13714

## Summary
PASS -> Pending Ship. All 4 ACs verified live. PM's follow-up comment flagged a real recurrence risk (a second sweep of the log files back into main happened mid-fix, racing skill's initial .gitignore commit) -- verified at the moment of this check that no third recurrence has occurred, not just trusted the PR description.

## AC Walk
| AC | Result | Evidence |
|----|--------|----------|
| AC1 (gitignore entries) | PASS | `.gitignore` on branch contains all 3 exact paths: `.squidsquad/harness-errors.log`, `.squidsquad/harness-supervisor.log`, `.squidsquad/harness-supervisor.log.err`. |
| AC2 (porcelain sweep excludes them) | PASS (live) | Created real ~15KB content files at all 3 paths on the checked-out branch. `git status --porcelain -- <path>` returned empty for all three -- the exact repro named in the issue body ("an untracked log with real content on disk still produces empty porcelain output"). |
| AC3 (untracked on main, not just gitignored -- PM's load-bearing follow-up) | PASS (live) | `git ls-tree -r <ref> --name-only \| grep harness-errors\|harness-supervisor` returned empty on both the PR branch tip AND current `origin/main` at verification time. No third recurrence detected between skill's fix and this check. |
| AC4 (regression test) | PASS | `tests/test_13714_harness_log_gitignore.py` -- 3/3 PASS (gitignore-lists-all-three, git-actually-ignores-each-path, untracked-log-absent-from-porcelain). |

## Sanity checks
- Full static gate: 5861 gated tests, 1 failure -- `test_no_silently_stale_comprehension_specs` (12818_spec.json/9184_spec.json vs `.squidsquad/pm/CLAUDE.md` and `.squidsquad/qa/CLAUDE.md` content drift). Independently reconfirmed this same failure exists on `origin/main` directly (checked out main in isolation, ran `comprehension_staleness.py check`) -- pre-existing, from PM's concurrent #10003 work, not introduced by or in scope for #13714. Matches skill's own disclosure in their PR comment.
- PM's suggested Windows-specific "unable to unlink" branch-switch regression test was not added by skill and not required by this issue's stated ACs -- noted, not blocking (out of scope: the issue's Expected/Actual is about git tracking, not about live-file-handle branch-switch failures, which is a separate, harder-to-reproduce-deterministically class of problem).

## Zero-gap check
0 gaps. All 4 ACs pass with live evidence, including the recurrence-risk check PM specifically flagged as load-bearing.

## Verdict
PASS -> Pending Ship. PR #13721 merged (commit 5c12f4c6).
