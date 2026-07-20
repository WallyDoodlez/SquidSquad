# QA-RESULTS-13793

**Issue**: #13793 -- improvement-scan: two unexplained sibling directories (SquidSquad-web, SquidSquad-qa-omain) not tied to any configured agent
**Verifier**: qa (verifier-lead)

## Round 1 -- FAIL

All 3 new tests mocked `_run()` to synthesize the failure. Live-tested real
`git clone` against 3 real failure modes: DNS failure and repo-not-found
left NO directory at all; interrupted mid-transfer (`timeout 1 git clone
<large-repo>`) left a directory WITH a `.git` folder present. Confirmed a
retry against that leftover still fails with the exact "destination path
already exists" error the issue describes. `_cleanup_failed_clone()`'s
bare `.git`-exists guard wrongly protected this broken-partial case.

## Round 2 -- FAIL

Added `git rev-parse --verify HEAD` completeness check -- correctly
identifies the round-1 repro as needing cleanup. But `shutil.rmtree()`
itself silently failed on Windows: git writes pack objects read-only, and
rmtree has no handler to clear that bit. Reproduced deterministically 3x
(not flaky, no lingering process holds the lock) against the same repro
directory; confirmed the standard onerror/chmod workaround resolves it.

## Round 3 -- PASS

Added an `onexc` callback (Python 3.12+, this repo's floor) that clears the
read-only bit and retries the delete. Re-ran the exact round-1/round-2 live
repro one final time: `timeout 1 git clone <linux-kernel> <dir>` -> `.git`
present, no resolvable HEAD -> called the fixed `_cleanup_failed_clone()`
directly -> directory fully removed, confirmed via `ls` returning "No such
file or directory".

Tests: tests/test_wizard.py -k 13793 9/9. Ship gate: static 5918/5918
passed, integration 53/53 OK.

## TC-Results

| TC | Description | Result |
|---|---|---|
| TC-1 | Early clone failure (DNS/repo-not-found) leaves no directory -- premise correction | PASS (round 1 finding) |
| TC-2 | Interrupted mid-transfer leaves a .git-present, no-resolvable-HEAD directory | PASS (round 1 repro) |
| TC-3 | rev-parse --verify HEAD correctly distinguishes complete vs broken-partial clones | PASS (round 2) |
| TC-4 | shutil.rmtree onexc clears read-only pack objects and retries successfully | PASS (round 3, live-confirmed against the exact repro directory) |
| TC-5 | Legitimate completed clone is never touched | PASS (test_successful_clone_is_not_touched) |
| TC-6 | tests/test_wizard.py -k 13793 full class | PASS (9/9) |
| TC-7 | Ship gate `python tests/run_tests.py` (static + integration) | PASS (static 5918/5918, integration 53/53) |

## Verdict

PASS -> pending-ship. Zero gaps.
