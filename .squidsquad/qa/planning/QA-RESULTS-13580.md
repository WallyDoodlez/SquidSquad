# QA-RESULTS-13580

## Summary
VERIFIED — PASS. All 4 ACs confirmed via live, unmocked (or minimally-mocked, isolating one variable) calls against real gh data (PR #13586), independent of the worker's fully-mocked test suite. Zero side effects (PR #13586 confirmed still OPEN afterward).

## AC Walk

| AC | Result | Evidence |
|----|--------|----------|
| AC1 | PASS | Live call: `git_ops.pr_merge(13586)` with only `_pr_state_scope_violations` mocked, `_pr_declared_files` REAL (hits live `gh pr view --json files` against PR #13586, which genuinely touches `git_ops.py`). stderr contains `#13580` and `Split it`. |
| AC2 | PASS | Negative control: same call with declared-files patched to exclude `git_ops.py`. stderr does NOT contain `#13580`. |
| AC3 | PASS | `git diff origin/main...squidsquad/task/13580 -- references/scripts/git_ops.py` shows only the message-building block after the refusal changed; `_pr_state_scope_violations`, `_is_launcher_script`, `_is_state_file` bodies untouched. |
| AC4 | PASS | Worker's own `test_split_hint_fail_open_when_declared_none` PASSED (mocked `_pr_declared_files` → `None`; hint skipped, refusal still fires). |

## Additional checks
- TC-5 (no side effect): `gh pr view 13586` confirmed `state=OPEN` both before and after my live calls — the state-violation branch returns before any real `gh pr merge` invocation.
- Worker's #13580-specific tests: 2/2 PASS (`test_state_violation_with_classifier_touch_gets_split_hint`, `test_split_hint_fail_open_when_declared_none`).
- Initial bare-branch static gate showed 1 failure (`test_windows_script_is_ascii_or_has_bom[.squidsquad\inject-permissions.ps1]`) — diagnosed as a stale-branch artifact: `squidsquad/task/13580` forked before #13582 (the em-dash fix for that exact file) merged to main; confirmed the branch's own diff never touches `inject-permissions.ps1`. Verified combined state via local `git merge origin/main --no-edit` (no push): that one test now PASSES, and the **full static gate is 5526/5526 green, 0 failures** — decisive.

## Zero-gap check
No gaps. Design non-regression (AC3) explicitly confirmed, not just assumed.

## Verdict
PASS → pending-ship.
