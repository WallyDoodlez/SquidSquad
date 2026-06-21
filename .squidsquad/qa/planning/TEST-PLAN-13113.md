# TEST-PLAN-13113 — respawned-agent telemetry masquerade

**Issue**: #13113 (type:issue, severity:medium, role:skill) — respawned agent's harness telemetry (bootup_complete / last_activity_at) never updates, defeating health diagnosis.
**PR**: #13143, branch `squidsquad/task/13113`. **CQ**: none (deterministic harness code).
**Derived from**: issue's observed-behavior + impact (RCA is skill's).

## ACs
- **AC1** per-session activity/pause telemetry (last_activity_at, last_activity, in_flight_until, waiting_since, compacting_since) is reset on respawn so a fresh record is indistinguishable from a first boot (no frozen-masquerade).
- **AC2** reset applied on ALL spawn/respawn paths (health-poller respawn, lifespan, start_all, start_agent, _respawn_agent_process) — no path left behind.
- **AC3** scope boundary: crash-loop/backoff bookkeeping (last_spawn_at, consecutive_fast_deaths, reboot_history, reboot_blocked_until, last_stop_failure) PERSISTS (not reset).
- **AC4** structural guard prevents a future spawn path from clearing last_dispatch_at without also resetting session telemetry.
- **AC5** (verify, not in scope of fix) bootup_complete symptom: confirm it is already handled (reset-on-spawn + ungated set-on-bootup-complete-event) → not a residual gap.
- **AC6** no-regression: full static gate green.

## Test cases
| TC | Check | Expected |
|----|-------|----------|
| TC1 | reset_session_telemetry clears 5 session fields | all None |
| TC2 | respawned record == fresh boot (session fields) | equal |
| TC3 | backoff bookkeeping preserved | unchanged |
| TC4 | idempotent on fresh agent | no-op |
| TC5 | structural: reset_calls >= spawn-path dispatch clears | holds |
| TC6 | activity handler (/hooks/activity ~2942) ungated, role-keyed | new heartbeat lands → last_activity_at=now |
| TC7 | bootup-complete handler (~3140) ungated, role-keyed | new session emit → bootup_complete=True |

## Method
1. Read harness.py diff — confirm helper + all 5 wire-ins + scope.
2. Confirm update paths (2942 activity, 3140 bootup) are ungated → reset makes respawn honest + new events land.
3. Run test_harness_telemetry_reset_13113.py.
4. Full static gate.

## Pass condition
AC1-4/6 PASS; AC5 confirmed already-handled (no gap); zero-gap; static gate green.
