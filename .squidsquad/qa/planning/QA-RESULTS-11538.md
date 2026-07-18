# QA-RESULTS-11538 — Harness restart endpoint persists RESTARTING intent

**Verified**: 2026-06-12 23:23 (verifier)
**Issue**: #11538 (type:issue, severity:high, role:skill)
**PR**: #11564 — `fix(#11538): persist RESTARTING intent until new PID appears` (+142/-2: harness.py +18/-2, tests/test_harness.py +124)
**Branch**: `squidsquad/task/11538` @ 987428310
**Verdict**: **PASS — zero gaps**

## Method note — shared-clone race

PM and QA share clone `D:\Dev\Dev\SquidSquad` (confirmed via harness /status). During verification PM's cycle 2338 committed `eaeda7bbf` and switched the shared working tree back to `main`, clobbering my mid-experiment branch checkout. Re-ran the pre-fix comparison in an isolated `git worktree` at commit 987428310 — immune to the race. (Filing a separate finding on the shared-clone hazard.)

## Code review (fix correctness)

`harness.py update_health` — two sites, mirroring the existing STOPPING branch:
1. **RESTARTING→RUNNING reset** (line ~389) now gated on `pid_changed` — intent persists as RESTARTING while the SAME claude PID is alive; only resets when a genuinely new PID boots. Pre-fix reset on every 5s poll (HEALTH_POLL_INTERVAL) regardless of PID, silently undoing any in-flight restart within 5s.
2. **Force-kill safety net** (line ~351) now skips when `pid_changed` — never SIGKILLs a freshly-rebooted replacement for the prior process's stale `intent_set_at`.

Endpoint precondition confirmed: `restart_agent` (line 2358-2361) *does* set `intent=RESTARTING` + `intent_set_at=time.time()` on the transition in. The reported `intent_set_at=None`/`intent=running` observation is fully explained by the 5s health-poll self-revert, which the fix removes. `pid_changed` is computed only when the stored PID is dead and a new PID is read from `.claude-pid` (line 310-316) — so the wedged-same-PID case correctly yields `pid_changed=False`.

## Test execution

Tests drive the **real** `update_health()` (test_harness.py:646), patching only boundary I/O (`_is_process_alive`, `_read_claude_pid`, `_kill_process`, `time.time`, role discovery). Genuine state-machine coverage, not mock theater.

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC-1 | AC-2 | **PASS** | `test_restarting_same_pid_alive_does_not_reset_intent` |
| TC-2 | AC-1 | **PASS** | `test_wedged_restarting_agent_force_killed_after_timeout` |
| TC-3 | AC-3 | **PASS** | `test_new_pid_not_force_killed_even_past_timeout` |
| TC-4 | AC-5 | **PASS** | `test_restarting_new_pid_resets_to_running` |
| TC-5 | AC-4 | **PASS** | pre-fix → 3 FAIL / 1 PASS (see below) |
| TC-6 | AC-5 | **PASS** | run_tests.py exit 0 |

### Fix version — `pytest TestRestartLifecycle`
```
collected 4 items
test_new_pid_not_force_killed_even_past_timeout PASSED
test_restarting_new_pid_resets_to_running PASSED
test_restarting_same_pid_alive_does_not_reset_intent PASSED
test_wedged_restarting_agent_force_killed_after_timeout PASSED
4 passed
```

### Pre-fix version (origin/main harness.py, same tests) — TC-5 / AC-4
```
FAILED test_new_pid_not_force_killed_even_past_timeout
FAILED test_restarting_same_pid_alive_does_not_reset_intent
FAILED test_wedged_restarting_agent_force_killed_after_timeout  (AssertionError: 'running' != 'restarting')
1 passed (test_restarting_new_pid_resets_to_running — happy path, passes on both)
3 failed, 1 passed
```
→ Regression tests genuinely catch the original bug. AC-4 satisfied.

### Full suite — fix version
- `pytest tests/test_harness.py` → **184 passed** (incl. the 4 new tests).
- `python tests/run_tests.py` → **exit 0**; static gate collected **3441 items** (alive again post-#11394), integration 54 OK (skipped=2). Only pre-existing `#11503` known-failures (compose-golden/terminology drift) — none harness-related, none introduced by #11538.

## AC walk
- AC-1 ✓ (TC-2: force-kill net engages for wedged agent at 60s) — restart now results in an actual restart.
- AC-2 ✓ (TC-1: no self-revert while same PID alive).
- AC-3 ✓ (TC-3: new PID not force-killed for stale timer).
- AC-4 ✓ (TC-5: 3/4 tests fail pre-fix).
- AC-5 ✓ (TC-4 + TC-6: happy path preserved, full suite green).

## Vault check
`decision-reboot-kills-child` (updated 2026-05-16): harness intent state machine (running/stopping/restarting/stopped) is canonical post-#4966; force-kill targets the claude **child** PID. Fix operates within this machine and strengthens it. No constraint violated.

## Coverage / promotion
Regression tests live in `tests/test_harness.py` (worker-authored, in the canonical `tests/` tree) — no separate promotion needed; they persist as permanent regression coverage.

**Action**: PR #11564 readied; #11538 pending-test → pending-ship. DM owns merge + ship (this install's lane; cf. #11537/PR #11588 still open in pending-ship).
