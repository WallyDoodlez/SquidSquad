# QA-RESULTS-13267 — git_ops.pull first pull pinned to --no-rebase

**Verdict: PASS — zero gaps.** PR #13270 merged (squash). (My own filed finding from #13261 verification.)

## AC walk (independent — derived from my filed finding)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | the FIRST `git pull` (git_ops.py:267) is pinned to `git pull --no-rebase` | PASS |
| AC2 | BOTH first + retry pulls are `--no-rebase`; no bare `git pull` survives | PASS |
| AC3 | regression test asserts the first pull is `--no-rebase` | PASS |
| AC4 | #13261 retry merge-abort behavior preserved (no regression) | PASS |

## Evidence
- Code (git_ops.py:267): `_run("git pull --no-rebase", check=False)` with a comment tying it to the #13261 recovery (a bare first pull under `pull.rebase=true` could leave a REBASE state the `git merge --abort` recovery can't clear).
- skill test (test_git_ops.py `test_first_pull_is_no_rebase`): asserts `mock_run.call_args_list[0][0][0] == "git pull --no-rebase"`. PASS.
- **QA independent test** (`tests/test_feat_13267_pull_both_no_rebase.py`): exercises the stash→retry path and asserts **EVERY** `git pull` invocation is `--no-rebase` (skill's test only checks the first) — zero bare `git pull` remain. ALL PASS.
- No-regression: full `tests/test_git_ops.py` = 168 passed, 0 failures (incl. #13261's merge-abort test).

## Notes
- Completes the every-agent pull-path consistency: both pulls now match the project always-merge-never-rebase rule. Closes the latent REBASE-state trap I flagged on #13261.

Status: pending-test → pending-ship.
