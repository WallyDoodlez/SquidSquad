# QA-RESULTS-13215 — deploy-pull survives a dirty agent clone (stash-around-merge)

**Verdict: PASS — zero gaps.** Verified against REAL git (independent integration test) + mocked unit suite.

## AC walk (independent — derived from issue body + skill/pm/dm comments)
| AC | Expectation | Result |
|----|-------------|--------|
| AC1 | clean tree behind origin → pull succeeds | PASS |
| AC2 | already-up-to-date → (True, "already-up-to-date") | PASS |
| AC3 | dirty tree (uncommitted change to incoming-touched file) → stash→merge→pop, survives | PASS |
| AC4 | genuine merge conflict → (False) → §11 recovery; clone NOT left MERGING (`git merge --abort`) | PASS |
| AC5 | #13167 no-op-stash guard — clean tree, nothing popped (no ancient-stash splatter) | PASS |
| AC6 | #13045 pop conflict → resolve unmerged to pulled HEAD, drop stash | PASS |
| AC7 | `merge --abort` precedes stash restore on conflict retry (MEDIUM fix) | PASS |

## Evidence
- Code (harness.py): `_safe_pull_in_clone` + `_safe_stash_pop_in_clone` clone-aware mirrors of `git_ops.pull`/`_safe_stash_pop`; call site `_run_deploy_sequence` routes `_safe_pull_in_clone` failure to `_deploy_recover_and_respawn(role,"pull",…)` (§11). `merge --abort` added before stash-restore on retry-failure branch.
- skill unit tests (test_harness.py `TestSafePullInClone13215`): 8 tests, all PASS.
- **QA independent REAL-git integration test** (`tests/test_feat_13215_deploy_pull_dirty_clone.py`): builds real origin+clone repos, confirms (a) a **bare** `git pull` ABORTS on the dirty tree (bug reproduced), (b) `_safe_pull_in_clone` returns ok, (c) deploy-sync lands (clone HEAD == origin HEAD), (d) clone NOT left MERGING, (e) incoming content present. The `stash pop conflict → resolved to pulled state` path is the #13045 correct behavior (stale local change discarded for authoritative pulled CLAUDE.md). ALL PASS.
- No-regression: full `tests/test_harness.py` = 300 passed, 0 failures.

## Notes
- Option A (replicate over `_git_in_clone`) correctly keeps the fix off the every-agent `git_ops.pull` path. LOW replication-drift risk docstring-mitigated.
- Out-of-scope follow-up (skill flagged on issue): identical MERGING-after-failed-pull gap pre-exists in `git_ops.pull` (every-agent path) — separate higher-blast-radius slice, NOT a gap in this PR's scope. Not reblocking; flagged for triage.

Status: pending-test → pending-ship.
