# TEST-PLAN #12460 — #12271 slice-4 SHADOW increment (progress-liveness, observational)

**Scope is the operator PATH B split** (PM comment 2026-06-16 00:50; skill handoff 00:52):
#12460 = the **SHADOW increment** (progress-liveness computed ALONGSIDE PID, divergence
LOGGED, reboot decision UNCHANGED). The **CUTOVER** (issue-body ACs 1 & 4 — make progress
authoritative, demote PID to teardown-only, remove the #10101/#10440 walk from the liveness
path) is moved to **#12492** (approved, role:skill, HARD-GATED on a clean live divergence
window). The issue #12460 body's 6 ACs describe the full cutover and LAG this pivot — TEST-PLAN
is derived against the narrowed shadow scope + HARNESS-ARCH §15.1, with body ACs 1/4 flagged
as deferred (verified to land in #12492).

## Narrowed ACs (shadow increment)

- **N1 (observational only)**: `progress_liveness()` computed alongside the PID verdict in
  `update_health()`; divergence LOGGED (candidate-zombie / candidate-false-reboot-avoided); the
  live reboot decision (`alive`, the PID verdict) is UNCHANGED — PID still decides this slice.
- **N2 (zombie detectable)**: the shadow computation CAN return "dead" for the #10855 inert-boot
  pattern (alive PID, no activity heartbeat past the grace window, no pause signal).
- **N3 (no false positive)**: a busy (in-flight tool call), paused (compacting/waiting),
  within-grace, acted-since-dispatch, idle-no-dispatch, or not-yet-booted agent is NOT flagged
  dead by the shadow.
- **N4 (grace integrity — DS-c1 trap)**: a handoff re-emit (#12442, 600s == ACTIVITY_GRACE_SECONDS)
  of STILL-UNACTED work must NOT reset the grace clock; `should_advance_dispatch()` advances only
  on first dispatch or after the agent caught up; never stamps a stopped/stopping agent; dispatch
  stamped under `state._lock` before emit (DS-c1 F3).
- **N5 (no regression)**: genuine death still reboots; the reboot path is untouched (shadow adds
  only a log line); #12244 backoff, #12442 routing, SessionEnd graceful-vs-crash all hold.
- **N6 (suite green)**: comprehensive tests incl. the zombie repro + busy/paused no-false-positive.

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC1 | N1 | read harness.py diff (update_health divergence block) | computes prog verdict, logs on disagree, `alive` untouched |
| TC2 | N1 | TestShadowDivergenceLogging (3) | divergence logged; agreement/idle log nothing |
| TC3 | N2 | own harness + TestZombieRepro::test_inert_boot_zombie_detected | (False, 'wedged-no-activity-since-dispatch') |
| TC4 | N3 | own harness (in-flight/active/idle/booting) + pause tests | all (True, …) |
| TC5 | N4 | own harness + TestShouldAdvanceDispatch (6) | re-emit-unacted=False; caught-up=True; stopped=False |
| TC6 | N4 | read diff (EAD stamp site) | under _lock, guarded by should_advance_dispatch, before emit |
| TC7 | N5 | harness/liveness/reboot regression suite | green |
| TC8 | N6 | test_12460_progress_liveness.py (24) | all pass |

## Deferred (flag, not reblock)
- **Body AC1** (decision keys off progress, not PID) → **#12492**.
- **Body AC4** (PID teardown-only; #10101/#10440 walk removed from liveness path) → **#12492**.
- #12271 is NOT complete until #12492 ships. Confirmed #12492 OPEN, approved, role:skill, title
  carries the cutover.

## Comprehension gate
NOT required — change is `references/scripts/harness.py` (a script) + `tests/`. No composed
CLAUDE.md / SOUL / instructions / sub-skills. HARNESS-ARCH §15 is human-facing documentation,
not LLM-consumed-at-runtime instruction.
