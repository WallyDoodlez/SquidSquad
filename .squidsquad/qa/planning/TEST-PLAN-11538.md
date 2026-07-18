# TEST-PLAN-11538 — Harness POST /agents/{role}/restart must result in an actual restart

**Source**: GitHub issue #11538 — "Expected" section + reported reproduction (this is a `type:issue` bug; ACs derived from the documented expected behavior, not from the worker's diff).
**Derived without reading the diff.** PR #11564 inspected only after the plan was written.

## Acceptance Criteria (derived from issue body)

- **AC-1**: A `success` response from `POST /agents/<alias>/restart` must result in an actual restart of a still-alive-but-non-cycling (wedged) agent — either (a) intent flips to `restarting` and `intent_set_at` is set so the 60s force-kill safety net engages, or (b) the endpoint force-restarts directly.
- **AC-2**: The 5s health poll (`update_health`) must NOT silently revert an in-flight `restarting` intent back to `running` while the SAME claude PID is merely alive. Intent must persist until the old process actually dies and a new PID appears.
- **AC-3**: A freshly-rebooted replacement process (new PID) must NOT be force-killed for the prior process's stale `intent_set_at` clock.
- **AC-4 (regression)**: A regression test exists that would have caught the original bug (i.e. fails against pre-fix code).
- **AC-5 (no regression)**: The happy path — restart completes, new PID boots, intent resets to `running` — is preserved, and the full test suite stays green.

## Test Cases

### TC-1 (covers AC-2): RESTARTING intent persists while same PID alive
- **Precondition**: agent intent=RESTARTING, intent_set_at=T, same claude PID alive, elapsed < 60s.
- **Steps**: drive one real `update_health()` poll with deterministic PID detection (same PID alive, no new PID from file).
- **Expected**: intent stays RESTARTING, intent_set_at unchanged, no kill called.
- **Verification command**: `pytest tests/test_harness.py::TestRestartLifecycle::test_restarting_same_pid_alive_does_not_reset_intent`

### TC-2 (covers AC-1): wedged agent force-killed after 60s
- **Precondition**: intent=RESTARTING, same PID alive, elapsed > FORCE_KILL_TIMEOUT_SECONDS.
- **Steps**: drive one real `update_health()` poll at T+61s.
- **Expected**: force-kill fires on the wedged PID; intent stays RESTARTING (next poll sees dead PID → reboot path).
- **Verification command**: `pytest tests/test_harness.py::TestRestartLifecycle::test_wedged_restarting_agent_force_killed_after_timeout`

### TC-3 (covers AC-3): new PID not force-killed past timeout
- **Precondition**: intent=RESTARTING, old PID dead, new PID booted, elapsed > timeout.
- **Steps**: drive one real `update_health()` poll with pid_changed=True at T+120s.
- **Expected**: no kill; intent resets to RUNNING; claude_pid updated to new PID.
- **Verification command**: `pytest tests/test_harness.py::TestRestartLifecycle::test_new_pid_not_force_killed_even_past_timeout`

### TC-4 (covers AC-5): happy-path restart completion preserved
- **Precondition**: intent=RESTARTING, old PID dead, new PID booted, elapsed < timeout.
- **Steps**: drive one real `update_health()` poll with pid_changed=True.
- **Expected**: intent resets to RUNNING, intent_set_at cleared, claude_pid = new PID.
- **Verification command**: `pytest tests/test_harness.py::TestRestartLifecycle::test_restarting_new_pid_resets_to_running`

### TC-5 (covers AC-4): regression tests catch the original bug
- **Precondition**: TC-1..TC-4 test bodies unchanged; `harness.py` reverted to pre-fix (origin/main).
- **Steps**: run the 4 tests against pre-fix `harness.py` in an isolated git worktree (immune to shared-clone race).
- **Expected**: TC-1, TC-2, TC-3 FAIL; TC-4 (happy path) PASSES — proving the tests discriminate the fix.
- **Verification command**: `git show origin/main:references/scripts/harness.py > <worktree>/references/scripts/harness.py && pytest .../TestRestartLifecycle`

### TC-6 (covers AC-5): full suite green
- **Steps**: `python tests/run_tests.py` against the fix.
- **Expected**: exit 0; full `test_harness.py` passes incl. the 4 new tests; only pre-existing #11503 known-failures (none harness-related).
- **Verification command**: `python tests/run_tests.py`

## Coverage matrix
- AC-1 → TC-2
- AC-2 → TC-1
- AC-3 → TC-3
- AC-4 → TC-5
- AC-5 → TC-4, TC-6

## Comprehension Questions
N/A — this task touches `harness.py` (executable Python code), not LLM-consumed instructions (CLAUDE.md / sub-skills / SOUL.md / prompts). No CQ spec required.
