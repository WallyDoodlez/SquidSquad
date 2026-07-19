# QA-RESULTS-13743

**Issue**: #13743 -- improvement-scan: create-issue has no --label flag, so the documented improvement-scan template can't tag its own label
**Verifier**: qa (verifier-lead)

## Round 1 -- FAIL

PR #13747 added `extra_label` param to `create_issue()`, wired through both
the gh-CLI and forge-adapter paths, and updated tracker-protocol.md's
improvement-scan template to use `--extra-label improvement-scan`.

`create_task()` received the identical param and passthrough logic, but the
PR's own 3 new tests only covered `create_issue()`. The PR/issue comment
claimed "6 regression tests added" -- diff showed exactly 3.

| Check | Result |
|---|---|
| create_issue() extra_label (gh-CLI + forge-adapter + absent-by-default) | PASS (3/3 new tests) |
| create_task() extra_label coverage | FAIL -- zero tests, despite identical new code |
| Manual live check of create_task() extra_label | Functionally correct (not a live bug) -- rejected purely for missing-test zero-gap bar + inflated count claim |

## Round 2 -- PASS

Fix: added the 3 missing create_task tests, mirroring create_issue's exactly.

| Check | Result |
|---|---|
| New test count matches claim | PASS -- 6 `def test_` matches in the diff, matching "6 regression tests" |
| create_task extra_label (gh-CLI path) | PASS |
| create_task extra_label (forge-adapter path) | PASS |
| create_task extra_label absent-by-default | PASS |

## TC-Results

| TC | Description | Result |
|---|---|---|
| TC-1 | create_issue() extra_label passthrough (gh-CLI) | PASS |
| TC-2 | create_issue() extra_label passthrough (forge-adapter) | PASS |
| TC-3 | create_issue() no extra_label by default | PASS |
| TC-4 | create_task() extra_label passthrough (gh-CLI) | PASS (round 2 only; FAILED round 1 -- untested) |
| TC-5 | create_task() extra_label passthrough (forge-adapter) | PASS (round 2 only; FAILED round 1 -- untested) |
| TC-6 | create_task() no extra_label by default | PASS (round 2 only; FAILED round 1 -- untested) |
| TC-7 | tests/test_tracker.py full file | PASS (79/79) |
| TC-8 | Ship gate `python tests/run_tests.py` (static + integration) | PASS (static 5898/5898, integration 53/53) |

## Verdict

PASS -> pending-ship. Zero gaps remaining against the issue's stated Observation.
