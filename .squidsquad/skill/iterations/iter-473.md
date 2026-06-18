# iter-473 — 2026-06-18 (skill, event-mode) — continued

(Same session as iter-472; resumed in-progress #12506 from working-state after a fresh boot.)

**Boot**: EVENT mode (harness reachable, port 7373). Drained boot backlog (72 events across 3 pages — all stale/test-issue churn + my own known transitions; advanced cursor per-page, no action). Emitted bootup-complete. No legacy cursor line (migration 1a no-op).

**#12506 — event-mode periodic driver (§8.6.1) → pending-test (PR #12812). Worker lane complete.**
- Merged origin/main into branch (clean). 
- **Unit 3** (the big one): rewrote `idle-cooldown-loop.md` to the driver-tick re-entry model. **PRIMITIVE DECISION settled = CronCreate+CronDelete** (prior note "recommended ScheduleWakeup" overridden): §8.6.1 says "cron"/"cancel the cron" throughout; ScheduleWakeup is bound to /loop dynamic mode (wrong for event mode); /loop conflicts with the event-mode wake binding. Maps every subloop_driver action → Cron tool call. Handles `durable:false` (session-scoped) cron restart loss via a CronList-confirm at idle-entry so the dormancy can't reappear. Names the §8.6.1 driver as the idle cadence source (not the Monitor — that false claim WAS the bug); keeps NUDGE branch + cooldown gate; documents Idle Scan Burst.
- **DS review (AC12)**: model_router exit 0, 6 findings, ALL resolved. One error-severity: Step B `cancel` action ignored `reason:at-cap` → crash-recovery dormancy regression (restart at cap left armed:true + no cron). Fixed by splitting cancel handling by reason. F3 was a code fix (arm already-armed now returns interval_minutes; +test). Record: DS-REVIEW-12506-unit3.md.
- **AC8** harness.py untouched ✓. **AC9** reconciliation: idle-cooldown-loop is runtime-loaded common-events/ (NOT inlined) → reaches agents via boot Read; composed CLAUDE.md references it (line 514). Did NOT run the LLM-polish `compose.py deploy-all` (it's a DM main-landing step and wouldn't embed a runtime-loaded fragment anyway).
- **Direct-to-main** (blocked from PR by #11511 transient-state guard): config.md `30m`+`Idle Scan Burst:3` + DS-unit3 record (eda40966d, pushed). Graceful defaults cover interim.
- **Tests**: subloop 29 + config 90 green; full run_tests.py green EXCEPT pre-existing #12798 (proven on origin/main, not a regression).

**Learnings** (→ working-state + personal memory): #11511 guard makes state files (config.md, planning/*, working-state) main-only — don't fight it on PR branches. #12408 (run_tests.py static gate exits 0 despite a failing test) is why #12798 was silently masked. compose.py deploy = per-role LLM-polish (non-deterministic; DM main-landing concern).

**Carry**: idle, queue next. Candidates: #12798 (trivial hygiene, clears team-wide red suite), #12799 (HIGH L1 async-no-pause), #10540 (DM batch-ship), approved tasks #12800/#12801/etc. #12506 awaits verifier.
