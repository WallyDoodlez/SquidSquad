# QA-RESULTS-11641 — Stale scheduled_tasks.lock crashes claude at startup → reboot loop

**Verifier**: verifier-lead (qa)
**Date**: 2026-06-13
**PR**: #11715 (squidsquad/task/11641 → main)
**Branch verified**: squidsquad/task/11641 @ ee8b210ca
**Verdict**: **PASS**

## AC Walk

### AC-1: dead-holder lock removed before exec, reclamation logged
**PASS.** thin_launcher.py:191 `_reclaim_stale_scheduled_lock(clone_path)`:
lock exists + `_is_process_alive(holder_pid)` False → `lock_path.unlink()` + stdout log
"reclaimed stale scheduled-tasks lock ... (holder pid N not alive) — #11641", returns True.
Wired at thin_launcher.py:524 — AFTER the singleton/.claude-pid gate (returns 3 on live
sibling) and BEFORE env setup/Popen. Test: test_dead_holder_lock_reclaimed +
test_main_launch_path_invokes_reclaim (confirms main() calls it on the launch path).

### AC-2: live-holder lock preserved (never stomp)
**PASS.** `_is_process_alive(holder_pid)` True → return False, no unlink.
Test: test_live_holder_lock_preserved.

### AC-3: regression — stale lock → claude launches; live-PID → preserved
**PASS.** Both paths covered by dedicated tests; the main-path test confirms the reclaim
runs on the real launch path before Popen so a dead-holder lock can no longer abort startup.

### Edge hardening (beyond AC, verified sound)
- no lock → no-op (test_no_lock_is_noop)
- unparseable JSON / non-int pid → warn + leave, conservative (test_unparseable_lock_preserved,
  test_missing_pid_field_preserved) — correct: cannot prove staleness, so does not risk
  stomping a live holder.
- unlink race (FileNotFoundError) → treated as already-gone; unlink OSError → warn + leave.

## Test Execution
- `pytest tests/test_thin_launcher.py` → **37 passed**, EXIT=0.
- Reclaim subset (TestStaleScheduledLockReclaim) → 6 passed.
- skill-reported full suite green (4123 passed / 15 skipped); DS review NO_FINDINGS.

## Verdict
**PASS → pending-ship.** Fix is correctly placed (before Popen, after singleton gate),
logic matches AC, regression tests cover dead-remove + live-preserve. DM ships PR #11715.
