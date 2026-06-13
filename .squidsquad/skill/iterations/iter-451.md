# Iteration 451 — cycle 1642

**When**: 2026-06-12 21:06
**Mode**: loop (polling; harness unreachable, port 7373 exit 7)

## Picked up
#11538 (high, role:skill) — Harness POST /agents/{role}/restart returns success but does not restart a non-cycling agent. Bug, auto-approved. Other queue items gated (#11503/#11505 on #11504; #10690/#10686 operator-gated; #11511 awaiting decision).

## Root cause
`HarnessState.update_health` (harness.py:372-377) reset intent RESTARTING→RUNNING + cleared intent_set_at on EVERY poll where the agent's claude PID was merely alive — no `pid_changed` guard. HEALTH_POLL_INTERVAL=5s → any restart of a still-alive (incl. wedged) agent silently reverted within 5s, AND disarmed the 60s force-kill net (scoped to STOPPING/RESTARTING). PM polled /status every 10s → never saw the 5s `restarting` window. Exact match to report.

The STOPPING branch directly below (378-388) was already correct — only resets on `pid_changed`. The RESTARTING branch lacked the guard.

## Fix (harness.py, 2 sites, mirrors STOPPING)
1. RESTARTING→RUNNING reset now requires `pid_changed` (old process died + new PID booted). Intent persists as RESTARTING → cooperative cycle-boundary exit OR 60s force-kill → reboot → new PID → reset.
2. Force-kill net skips when `pid_changed` — never SIGKILLs a freshly-rebooted replacement for the prior process's stale intent_set_at (latent edge my fix would widen).

## Tests
TestRestartLifecycle (4 cases) drives update_health across the full restart lifecycle. Verified via `git stash` of harness.py: 3 FAIL on pre-fix code, PASS with fix; 4th locks preserved happy path. test_harness.py = 184 pass. run_tests.py exit 0.

## Outcome
→ pending-test. PR #11564. Branch squidsquad/task/11538 → back on main. Handoff comment posted for verifier.

## Notes
- No DS-review: change is non-instruction code (harness.py), outside the 7.2 instruction/compose/sub-skill surface; small + test-locked with old/new distinction proven.
- No CQ / manifest / upgrade impact: pure runtime state-machine fix; live harness picks it up on next restart (runs from references/scripts/, no compose/copy).
