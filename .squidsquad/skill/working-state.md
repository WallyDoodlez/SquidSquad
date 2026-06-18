# Working State

- **Task**: #12506 (in-progress) — event-mode periodic driver (fixes dormant improvement subloop across all event-mode agents). Build to LOCKED AGENT-RUNTIME §8.6.1 (PR #12518, on main 06888b854). role:skill, high. Plan published as comment 01:47.
- **Prior this session**: #12585 → pending-test (PR #12782, L1 Soul Health & Diagnostics) — DONE, in verifier lane.

## #12506 PLAN (work contract — published on issue)
**Seam:** driver-lifecycle decisions (lazy-arm@first-idle, scan_count++, cancel@`Idle Scan Burst`, re-arm+reset@re-idle, config reads) → NEW testable module `references/scripts/subloop_driver.py` (deterministic core, makes AC1/3/4/6 unit-testable). Scheduling tool call stays in prose (idle-cooldown-loop.md). State file `.squidsquad/<alias>/.subloop-driver.json` (armed, scan_count, last_run).
**Primitive:** recommend ScheduleWakeup (single-shot self-reschedule: arm=first wake; tick=scan+reschedule while under cap; cap=stop=natural cancel; re-arm=schedule again). Fallback CronCreate+CronDelete. Confirm in unit 1.
**Units (ATOMIC — one PR per §8.6.1 DS-audit Q1):**
1. subloop_driver.py + unit tests → AC1/AC3/AC4/AC6. ← NEXT (primitive-agnostic, build+test first)
2. config.md `## Improvement Scanning`: `Cool-Down: 30`→`30m`; add `- **Idle Scan Burst**: 3` → AC6/AC11.
3. idle-cooldown-loop.md rewrite step5 + "after each empty poll interval" → driver-tick model; name §8.6.1 as cadence; KEEP NUDGE branch + cooldown check; doc Idle Scan Burst → AC2/AC5/AC7.
4. compose deploy-all + verify driver instruction in event-mode composed CLAUDE.md → AC9; harness.py untouched → AC8.
5. comprehension AC10 (PM-authored in body; verifier makes spec per TEST-PLAN).
**Discipline:** DS-review per change (AC12) w/ Sonnet fallback on model_router exit1/2/3; run_tests.py green before pending-test; if harness change needed → STOP + route to PM (§8.6.1 constraint).
**TODO before unit 1:** read existing throttle machinery — `.subloop-last-run` (§8.6) vs `## Improvement Scan` working-state block (idle-cooldown-loop.md) — integrate, don't duplicate. Check scan_index.py throttle logic.

## Blocked in-progress (carried, not mine to action)
- #10855 PM-parked (do-not-resume; #12460 shipped → PM to close-as-superseded). Stale PR #10952 hygiene deferred.
- #12493 HELD on §8.3 semantic-handoff-backstop (NOT landed). PR #12494 built.

- **Branch**: squidsquad/task/12506 (adopting via task-begin).
- **Status**: #12506 in-progress (planning done, building unit 1).
- **Updated**: 2026-06-18 01:47 (skill — event-mode)
- **Quiet Cycle Counter**: 0

## Improvement Scan
Status: idle
Last completed: (none this session)
Next scan after: (eligible)
