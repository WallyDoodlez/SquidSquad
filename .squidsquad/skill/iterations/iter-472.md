# iter-472 — 2026-06-18 (skill, event-mode) — continued

(Same session as iter-471; #12585 shipped to verifier, then picked up #12506.)

**#12506 — event-mode periodic driver (§8.6.1), units 1+2 built + committed:**
- Claimed approved→in-progress; gate satisfied (§8.6.1 PR #12518 on main). Published front-loaded plan (deterministic-seam architecture, primitive trade-off, 5 units, AC map, atomic-PR).
- **Unit 1**: `subloop_driver.py` — deterministic arm/tick/record-scan/reidle/cancel lifecycle. State `.squidsquad/<alias>/.subloop-driver.json` (atomic writes). 29 unit tests green.
- **Unit 2**: config.py (idle-scan-burst FIELD_MAP + default 3), wizard.py (new installs 30m + Idle Scan Burst 3), SAMPLE_CONFIG fixture.
- **DS review** (deepseek, exit0 real output): 4 findings. Fixed F1 (TypeError guard in cooldown_elapsed), F2 (read_state type-coercion + non-dict guard), F3 (tick armed-gate vs stale self-wake). Declined F4 (variable interval — §8.6.1 is fixed-cadence; within AC2 tolerance). +5 tests.
- Committed unit 1+2 to `squidsquad/task/12506` (pushed). Units 3-5 (sub-skill rewrite + primitive, compose, comprehension, finalize) remain — atomic PR not yet opened.

**Zero-gap RCA (facts-over-assumption applied):** full suite surfaced 2 reds. F1 mine = SAMPLE_CONFIG missing new field → fixed. F2 = pre-existing tracked volatile `.claude/scheduled_tasks.lock.stale-bak` (QA b3b11f646, on origin/main) failing test_volatile_files_not_tracked — NOT my regression. Reverted the hygiene fix from #12506 branch (scope purity + state-guard strips `.claude/` from feature branches anyway); filed **#12798** for separate direct-to-main fix.

**Carry**: resume at #12506 unit 3 (idle-cooldown-loop.md rewrite — current step 5 wrongly assumes Monitor delivers fixed-cadence wakes; settle scheduling primitive). Re-apply live config.md at finalize. #12585 awaits verifier.
