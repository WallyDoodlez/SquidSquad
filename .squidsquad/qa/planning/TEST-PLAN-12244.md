# TEST-PLAN-12244 — Harness infinite-reboots an agent on exit-1 (session/usage limit)

**Derived independently from issue #12244 AC list.** Verifier: qa · 2026-06-14 01:38 · PR #12293 (head `squidsquad/task/12244`, +423 −29, harness.py + test_harness.py)

## Acceptance Criteria (from issue body)

- **AC1** — Simulate/inject a claude exit-1 with 'session limit' output → harness pauses respawn (no tight loop), logs a clear 'session-limit' status, resumes after reset/backoff.
- **AC2** — Normal exit-1 (real crash) still reboots as today (distinguish session-limit from generic crash).
- **AC3** — Status endpoint shows the limited/paused state so PM/operator see the real reason.

## Delivered scope (per worker discussion)

P0 (restart-safe intent clock) + P2 (crash-loop backoff). P1 (force-kill sparing) deliberately out of scope; P3 (.claude-pid authoritative) spun off to #12294. Backoff is **cause-agnostic timing-based** (not output parsing — thin_launcher doesn't capture claude's stdout).

## Test Cases

| TC | AC | Method | Expected |
|----|----|--------|----------|
| TC-1 | P0 | Live: load_state on stale `RESTARTING` (intent_set_at 5min old) | intent→RUNNING, intent_set_at→None (force-kill clock cleared) |
| TC-2 | P0 | Live: load_state on stale `STOPPING` | intent preserved (operator stop survives restart) |
| TC-3 | AC1 | Unit: streak crosses FAST_DEATH_THRESHOLD | respawn held, status='crash-looping', reboot_blocked_until set |
| TC-4 | AC1 | Unit: backoff exponential + capped at 30m | deadline = base·2^over, ≤ cap |
| TC-5 | AC1 | Unit: backoff resumes after window elapses | respawn retried, blocked_until cleared |
| TC-6 | AC1 | Unit: no resume before window | stays crash-looping |
| TC-7 | AC2 | Unit: 1st/2nd fast death below threshold | reboots immediately (no backoff) |
| TC-8 | AC2 | Unit: slow death (lived > window) resets streak | streak→0, reboots immediately |
| TC-9 | AC2/recovery | Unit: spawn survives window → clears streak | consecutive_fast_deaths→0 |
| TC-10 | AC3 | Code: /status → all_agents() → to_dict serializes status + reboot_blocked_until + consecutive_fast_deaths | paused state visible to operator |
| TC-11 | edge | Unit: operator stop wins over backoff (crash-looping + STOPPING → stopped) | no wedge (DS-review finding 1) |
| TC-12 | edge | State persists across harness restart (backoff fields in save/load) | streak not reset mid-backoff |
| TC-13 | — | Full harness suite (197) + integration (53) — blast-radius (harness supervises every agent) | all green |

## Divergence to flag (PM)

AC1/AC2 literally ask for **session-limit-specific** detection ("logs a clear 'session-limit' status", "distinguish session-limit from generic crash", "resets HH:MM"). Impl is cause-agnostic crash-loop backoff. The literal is infeasible — thin_launcher does not capture claude's terminal output. AC's measurable intent (no tight loop / non-silent status / resume) IS met. Contract-feasibility note, not a code gap.
