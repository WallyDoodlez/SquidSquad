# Working State

- **Task**: none active — on main (#11538 fix shipped to pending-test, PR #11564)
- **Status**: none (idle)
- **Updated**: 2026-06-12 21:06
- **Last Processed Event ID**: 9d7c2489
- **Quiet Cycle Counter**: 0

## ⚠️ Session note
Booted PRE-v0.44.0; runs OLD composed CLAUDE.md (reboot pending per DM — do NOT self-reboot). Harness DOWN (port 7373 exit 7) — loop-mode this session.

## Last cycle (1642, iter-451): fixed #11538 harness restart bug
update_health reset RESTARTING→RUNNING on every poll where the same claude PID was alive (no pid_changed guard) → HEALTH_POLL_INTERVAL=5s silently reverted any restart of a still-alive/wedged agent AND disarmed the 60s force-kill net. Fix mirrors STOPPING branch: (1) RESTARTING→RUNNING reset gated on pid_changed; (2) force-kill skips when pid_changed. TestRestartLifecycle (4 cases) — 3 fail on pre-fix code, verified via git stash. 184 harness tests + run_tests.py green. → pending-test, PR #11564, back on main.

## Standing
- **#11538 / PR #11564**: pending-test — verifier to verify (harness restart endpoint fix).
- **#11512 / PR #11518**: pending-ship, MERGEABLE/CLEAN — DM to ship promptly (may re-stale).
- **#11519 / PR #11530**: pending-ship — DM to ship.
- **#11511 (medium)**: root cause = merge=ours not honored by GitHub server-side; recommendation posted (A=state-branch via state_bus [recommended]; B=stopgap merge=union). Awaiting PM/operator decision. NOT implementing (high blast radius).

## Watch
- **PR #11504 / #11394**: static-gate auto-discovery — MERGED into this branch base (5f6caffbf). On confirmed merge → #11503/#11505 ungated.
- #11503 (high) / #11505 (low): gated on #11504 (now likely unblocked — re-check next cycle).
- #10690 / #10686 (E7): operator-gated.
- #11329 (approved): runtime per-event ack-cursor.

## ⚠️ Recurring conflict note
PR CONFLICTING-while-locally-clean = merge=ours custom driver not honored by GitHub server-side (#11511). Verify real vs cosmetic with `git merge-tree --write-tree origin/main origin/<branch>` (exit 0 = cosmetic). Real fix = state-branch (state_bus, unwired). See [[learning-pr-conflicting-flag-can-be-cosmetic]].
