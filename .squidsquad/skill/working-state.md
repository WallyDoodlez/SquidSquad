# Working State

- **Task**: none (idle — #12506 handed off to verifier).
- **Just completed**: #12506 → pending-test (PR #12812). Event-mode periodic driver, all units, §8.6.1. Worker lane done; verifier owns it now.

## #12506 — DONE this session (pending-test, PR #12812)
- **Unit 1** `subloop_driver.py` — arm/tick/record-scan/reidle/cancel state machine. 29 tests green. (DS-unit1 record on main.)
- **Unit 2** config wiring: `config.py` idle-scan-burst FIELD_MAP + default 3; `wizard.py` new-installs `Cool-Down: 30m` + `Idle Scan Burst: 3`; `test_config_functions.py` (90 green).
- **Unit 3** `idle-cooldown-loop.md` rewritten to the driver-tick model. **PRIMITIVE DECISION settled: CronCreate+CronDelete** (§8.6.1 says "cron"/"cancel the cron"; ScheduleWakeup is bound to /loop dynamic mode; /loop conflicts with event-mode wake binding). Cron is `durable:false` (session-scoped) + CronList-confirm at idle-entry re-creates after restart. Names §8.6.1 driver as cadence source (not Monitor). Keeps NUDGE branch + cooldown gate.
- **Unit 4 / AC8-AC9**: harness.py untouched (AC8 ✓). idle-cooldown-loop is a runtime-loaded `common-events/` fragment (NOT inlined) → reaches agents via boot Read; composed CLAUDE.md references it (`→ run sub-skill`, line 514). No recompose embeds it (by design) → did NOT run the LLM-polish `compose.py deploy-all`.
- **DS review (AC12)**: model_router exit 0, 6 findings ALL resolved (incl. 1 error-severity: cancel-action ignored `reason:at-cap` → crash-recovery dormancy regression). Record: `DS-REVIEW-12506-unit3.md` (on main).
- **Main-side landed (direct-to-main, blocked from PR by #11511 guard)**: config.md `30m`+`Idle Scan Burst:3` + DS-unit3 record (commit eda40966d, pushed). Graceful defaults cover interim until PR merges.
- **Tests**: subloop 29 + config 90 green; full run_tests.py green EXCEPT pre-existing **#12798** (not a regression).

## KEY LEARNINGS this session (see also personal memory)
- **#11511 pre-commit guard**: install/transient state files (`config.md`, `.squidsquad/<role>/planning/*`, working-state) are BLOCKED from PR/feature branches → main-only. Don't fight it; commit those direct-to-main. (Explains the "config.md keeps reverting" confusion.)
- **#12408** (high, open): run_tests.py static gate exits 0 despite a failing test — that's WHY the #12798 failure was silently masked. Relevant when reasoning about suite health.
- **compose.py deploy** invokes an LLM-polish step (`claude -p`) per role; non-deterministic; it's a DM main-landing concern, not a worker feature-branch step.

## Queue (skill) — next pickup candidates
- **#12798** (low, open) — stale-bak hygiene (git rm --cached + gitignore); trivial, clears team-wide red suite + relates to #12408. Good small next item.
- **#12799** (HIGH, open) — L1 async-no-pause (agents must never block on a human). Instruction change → CQ test.
- **#10540** (medium, open) — DM batch-ship dispatch "Base branch was modified" (PM routed to skill as fix-surface owner).
- Approved tasks (high): #12801 (Harness TUI action bar), #12800 (human as non-agent role), #12527, #12492, #12450, #12271.

## Blocked / not mine
- #10855 PM-parked (do-not-resume). #12493 HELD on §8.3 (PR #12494 built). #12585 SHIPPED (L1 Soul; reboot deferred per operator).

- **Status**: idle, #12506 pending-test (PR #12812). Ready to pick up next queue item.
- **Updated**: 2026-06-18 13:10 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
