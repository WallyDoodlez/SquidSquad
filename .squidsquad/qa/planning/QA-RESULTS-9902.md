# QA Results — #9902 (#9873-A retro DeepSeek findings)

**Verifier**: qa-lead
**Timestamp**: 2026-05-22 09:31 cycle 727
**PR**: #9923 (branch `squidsquad/task/9902`)
**Verdict**: PASS — zero gaps. Status → Pending Ship.

## Findings & Fixes

| # | Finding | Fix verified in diff | Test verified | Result |
|---|---------|----------------------|---------------|--------|
| F1 | `advance_cursor` TOCTOU: `has_event` called outside lock; missing `target_pos < 0` guard | `has_event` now inside `with self._lock:` (harness.py:756-760); `target_pos < 0` early-return added (harness.py:770-776) | `test_ac19_has_event_called_inside_lock_9902`, `test_target_evicted_during_regression_check_9902` | PASS |
| F2 | D11 "persist under lock" comment lied (release-reacquire pattern) | Comment rewritten to accurately describe outside-lock persist (option b — matches `ack()`/`dispatch()`) | Covered by existing `TestCursorState9873A` behavior tests | PASS |
| F3 | `ack_stop` silent no-op when `SQUIDSQUAD_ROLE` unset | Added `role=None` kwarg with env fallback (event_bus.py:166-188); matches `ack_cursor` API | `test_explicit_role_param_overrides_env_9902`, `test_emits_when_env_unset_but_role_passed_9902` | PASS |
| F4 | Inline ack handler missing `isinstance(payload, dict)` guard → 500 on string/list payload | Guard added on BOTH ack-cursor branch (harness.py:1672-1675) and ack-stop branch (harness.py:1706-1709); `result` check also uses dict-guarded variable | `TestAckEndpointPayloadGuard9902`: 4 cases (string/list payload on ack-cursor, string/null payload on ack-stop) all return 200 | PASS |

## Test runs

- Targeted: `pytest tests/test_event_bus.py::TestAckStop tests/test_harness.py::TestCursorState9873A tests/test_harness.py::TestAckEndpointPayloadGuard9902` → **27 passed in 3.81 s** (8 new + 19 existing).
- Regression: `pytest tests/test_harness.py tests/test_event_bus.py` → 210 collected, exit 0, no failures.

## DeepSeek pre-push review

Skill-lead reports pre-push DeepSeek returned NO_FINDINGS on this PR (per the `feedback_deepseek_review` memory — the retro review on #9899 was what spawned this issue; this PR did the review pre-push). I did not re-run DeepSeek; I trust the skill comment and the diff is small enough that the inspection above caught any obvious issues.

## Non-blocking observation for skill / DM

PR #9923 includes two runtime artifacts of the DeepSeek tool:
- `.deepseek-9902.diff` (+430 lines)
- `.deepseek-9902.out` (+3 lines)

`.deepseek-*` is NOT in `.gitignore`. These are accidental commits of review-tool scratch files — they don't break anything but they bloat the PR diff. Recommend either gitignoring the `.deepseek-*` pattern or removing these two files before merge. Not a QA defect (no AC mentions them, no behavior breaks), filed here as info for skill/DM.

`mergeable: MERGEABLE, mergeStateStatus: CLEAN, isDraft: false` per `gh pr view`.
