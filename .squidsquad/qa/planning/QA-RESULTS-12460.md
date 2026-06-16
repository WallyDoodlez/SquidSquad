# QA-RESULTS #12460 — #12271 slice-4 SHADOW increment

**Verdict: PASS** (against the operator PATH B shadow scope) → pending-ship (merge deferred to DM).
**Cycle 223, 2026-06-16. Branch squidsquad/task/12460, PR #12472.**

## Results

| TC | AC | Result | Evidence |
|----|----|--------|----------|
| TC1 | N1 | ✅ PASS | harness.py update_health: `prog_alive,prog_reason = agent.progress_liveness(...)`; logs only `if prog_alive != alive`. `alive` (PID verdict) is read-only in the block — reboot decision untouched. Comment explicitly: "does NOT change `alive` or the reboot decision." |
| TC2 | N1 | ✅ PASS | TestShadowDivergenceLogging: zombie→candidate-zombie log; agreement→no log; idle→no divergence. |
| TC3 | N2 | ✅ PASS | Own harness: zombie (dispatch+grace elapsed, no activity, no pause) → `(False, 'wedged-no-activity-since-dispatch')`. TestZombieRepro::test_inert_boot_zombie_detected green (#10855 pattern). |
| TC4 | N3 | ✅ PASS | Own harness: in-flight→`(True,'in-flight')`, acted→`(True,'active')`, idle→`(True,'idle-no-dispatch')`, not-booted→`(True,'booting')`. Pause tests (compacting/waiting/within-grace) green. Stale-pause-past-ceiling still lets a genuine wedge read dead (good edge). |
| TC5 | N4 | ✅ PASS | Own harness: reemit-unacted should_advance=**False** (grace keeps aging — the DS-c1 trap); caught-up=True; stopped=False. TestShouldAdvanceDispatch (6) green incl. grace-does-not-reset-forever simulation. |
| TC6 | N4 | ✅ PASS | EAD stamp site: `with state._lock: ... if _disp_agent.should_advance_dispatch(): _disp_agent.last_dispatch_at = check_time` — under lock, guarded, BEFORE emit (DS-c1 F3). last_dispatch_at cleared on every spawn/respawn path (DS-c1 F4); persisted + restored across harness restart. |
| TC7 | N5 | ✅ PASS | Harness/liveness/reboot regression: **374 passed, 4 skipped** (test_harness, test_reboot_agent, test_9242_harness_wedge_fixes, test_11723_port_discovery_liveness, test_harness_freshness_restart_e5, test_harness_route_contract, + 12460). Reboot path provably untouched (shadow adds only a log line). Integration suite (run_tests.py): 53 OK. |
| TC8 | N6 | ✅ PASS | test_12460_progress_liveness.py → **24 passed**. |

## AC mapping (narrowed shadow scope)
- **N1** ✅ TC1/TC2 — observational; reboot decision unchanged.
- **N2** ✅ TC3 — #10855 zombie detectable by the shadow.
- **N3** ✅ TC4 — no false positive across busy/paused/idle/booting/within-grace/acted.
- **N4** ✅ TC5/TC6 — grace integrity; re-emit of unacted work doesn't reset; lock+guard+pre-emit; spawn-clear; persistence.
- **N5** ✅ TC7 — no regression; reboot path untouched.
- **N6** ✅ TC8 — 24 tests incl. zombie repro + busy/paused no-false-positive.

Lone warning in the regression run is a cosmetic Windows cp1252 emoji-encode in a shutdown `_log` line (pre-existing, unrelated, not a failure).

## DEFERRED — flagged, not a reblock (operator PATH B split)
Issue-body **AC1** (liveness/reboot decision keys off progress signals, NOT PID) and **AC4** (PID
demoted to teardown-only; #10101/#10440 walk removed from the liveness path) are **NOT delivered**
in this increment — they are the CUTOVER, deliberately deferred to **#12492** (confirmed OPEN,
status:approved, role:skill, priority:high; title: "Cutover flip: remove PID-poll, progress-liveness
decides reboot … GATED on #12460 shadow observation window"). This is operator-sanctioned (PM
comment 00:50, "Operator decision: PATH B (formal split)"; skill handoff 00:52 scoping THIS
increment to observational), so it is an explicit-override of the zero-gap gate, not a gap waved
through. **#12271 is NOT complete** — #12460 ships the safety-observation layer the cutover is
gated on; #12492 completes the epic once a clean live PID-vs-progress divergence window confirms
no false pos/neg.

## Comprehension
Not required — harness.py script + tests only; no LLM-consumed instruction change. HARNESS-ARCH §15
is human-facing documentation.

## Disposition
PASS → pending-test → pending-ship. **Merge deferred to DM** (standing post-cy151 pattern; PR #12472
has no closing keyword so no auto-close, but DM owns the ship ceremony + the live observation window
that gates #12492). Ship counter NOT bumped (DM owns). test_12460_progress_liveness.py already under
tests/ (preserved). TEST-PLAN-12460 / QA-RESULTS-12460 committed.
