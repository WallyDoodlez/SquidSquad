# QA Log

## Agent Health — 2026-05-31 19:06

- **skill**: 👻 stalled (81m — exceeds 60m threshold)
- **pm**: 🦑 healthy (28m, idle)
- **verifier**: 👻 stalled (87m — exceeds 60m threshold)
- **dm**: 🦑 healthy (23m, idle)
- **Notes**: skill + verifier both 👻. Working tree has `start-no-autoreboot.ps1` + `harness.py` UU conflict — harness likely running with auto-reboot disabled, so dead agents won't respawn. Not filing bug (operator-intentional environment). PM idle, may auto-boot per feedback_manual_agents next cycle.

## QA Run — 2026-04-15 00:40

- **Result**: Skipped (no E2E command)
- **Tests Run**: 0 (E2E), 588 static (via test plan)
- **Failures**: none (2 pre-existing integration errors in test_status_flow.py — unrelated to #942)
- **Notes**: Verified #942 (boot process health overhaul) — 34/34 TCs PASS, 13/13 smoke tests PASS. Status → Pending Ship.

## Agent Health — 2026-04-15 00:40

- **skill**: 🦑 healthy (2m)
- **pm**: 🦑 healthy (7m)
- **dm**: 🦑 healthy (9m)
- **Notes**: All agents active and cycling normally.

## Agent Health — 2026-04-14 21:43

- **skill**: 🦑 healthy (10m)
- **pm**: 👻 stalled (75m — exceeds 60m threshold)
- **dm**: 🦑 healthy (11m)
- **Notes**: PM current-state shows "idle|Initializing..." — may have failed to complete boot cycle.

## QA Run — 2026-04-13 02:50

- **Result**: Skipped (no E2E command)
- **Tests Run**: 0
- **Failures**: none
- **Notes**: Unit test suite run: 545 passed, 1 failed (pre-existing: designer missing working-state.md). Filed #758.
