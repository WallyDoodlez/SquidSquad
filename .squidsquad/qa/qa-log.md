# QA Log

## Agent Health — 2026-06-01 11:06

- **skill**: 🦑 healthy (11m, idle)
- **pm**: 👻 stalled (148m — newly crossed threshold this cycle; was healthy at 28m last cycle)
- **verifier**: 👻 stalled (1046m — ~17.4h, unchanged long-running stall since cycle 491)
- **dm**: 🦑 healthy (26m, idle)
- **Notes**: PM stall is the new event. Pipeline drained — PRD-A/B core stories all shipped (A1+A2a-f+A3+A4+A4.5+A5+A6 / B1+B2+B3+B4+B5+B6+B7+B8). Only remaining open PRs are 2 doc drafts (#10391 PRD-C, #10392 PRD-D+E). No new work in pending-test or approved queues because PM (planner/approver) is down — verification queue went empty for the first time in 30+ cycles. Operator may want to boot PM before queueing PRD-C/D/E work.

## Agent Health — 2026-05-31 23:36

- **skill**: 👻 stalled (72m — re-crossed threshold; was healthy during cycles 494–498)
- **pm**: 🦑 healthy (28m, idle)
- **verifier**: 👻 stalled (356m — ~5.9h, unchanged since cycle 491)
- **dm**: 🦑 healthy (26m, idle)
- **Notes**: skill stall blocks #10443 merge-main route-back per [[feedback_never_rebase_merge_instead]]; #10443 has been in-progress since 02:40Z waiting. PM has not booted skill or verifier per [[feedback_manual_agents]] — operator may want to investigate why PM is idle on dead-agent boot, OR `--no-auto-reboot` env may be intentional pause.

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
