# Working State

- **Task**: #11723 — liveness-aware port discovery (#11586 root-cause fix) — COMPLETE, PR #11729
- **Status**: in-progress — HELD pre-pending-test, gated on #11683 (full-suite green); DS review running
- **Updated**: 2026-06-13 11:52
- **Branch**: squidsquad/task/11723 (current). Other in-flight: task/11640, task/11641, task/11587.
- **Quiet Cycle Counter**: 0 (iter-465: #11723 root fix attempt #2, backed out — 404 deeper than expected)

## ⚠️ Session note
Harness is UP on 7373 (confirmed iter-462). My clone's .harness-port keeps getting re-stomped to 59999 by the verifier's per-cycle test runs (harness _deferred_init distributes test port into real clones). Mode sticky this session (loop). #11723 makes discovery resilient to this for future boots. `/loop 30m` cron c8644353. working-state per-branch; git tree is truth.

## FOUR skill PRs in flight
| Issue | Fix | Branch | PR | DS | Gated on |
|---|---|---|---|---|---|
| #11640 | clone-resolution refuse | task/11640 | #11709 | NO_FINDINGS | #11683 ship |
| #11641 | stale scheduled_tasks.lock reclaim | task/11641 | #11715 | NO_FINDINGS | #11683 ship |
| #11587 | uvicorn loop=none (ProactorEventLoop) | task/11587 | #11722 | NO_FINDINGS | #11683 ship |
| #11723 | liveness-aware port discovery (#11586 root cause) | task/11723 | #11729 | NO_FINDINGS | #11683 ship |

All own-tests green; each held only because merging current main pulls in the #11657 stale event_poll test (the single full-suite red).

## ⭐ #11586 ROOT CAUSE (iter-462/463): stale .harness-port, NOT harness availability
Harness healthy on 7373 whole time. Agents with a stale/dead port file (test-pollution via harness _deferred_init + verifier per-cycle test runs) probe a dead port → loop mode / Monitor death. #11723 = the DURABLE fix (Part 2 resilience: discovery skips dead ports). Team has been band-aiding with a 'pin-keeper' watchdog (main commit caf10fe21: 'durable fix still pending operator'). Reported on #11586.
**#11723 follow-ups (open, next):** (1) stop test harnesses distributing ephemeral ports into REAL clones (isolate .local-config in test fixtures) — the ROOT fix; (3) boot Step 1 instruction fall-through to default when file-port probe fails (CQ + recompose).

## Gates / blockers
- **#11683 ship** (operator/DM): unblocks all 4 PRs + #11505 AC7. Verified+MERGEABLE, pending-ship ~6h.
- **#11505**: blocked on PM/operator disambiguation (#11505↔#10025 overlap, touches PM task-intake).

## #11723 follow-up (1) — ROOT fix scoped (iter-464), backed out, queued
EXACT mechanism: boot_remote.py:35-39 hard-codes SQUIDSQUAD_DIR (ignores $SQUIDSQUAD_DIR env — the lone holdout vs harness/event_bus/event_poll). So _deferred_init clone-distribution reads the REAL .local-config even from an isolated test harness → pollutes real clones. Fix = 2 coupled parts: (a) boot_remote._resolve_squidsquad_dir() honoring the env (drafted + 4 unit tests green this cycle); (b) REQUIRED ripple — real_harness fixture writes NO .local-config in its isolated SQUIDSQUAD_DIR, so (a) alone → isolated harness reads missing config → sys.exit(2) → 404s (confirmed: test_9398_real_agent_subprocess 404). Fixtures must write an isolated .local-config (test role → temp clone w/ .squidsquad). Backed out (a) this cycle to keep PR #11729 clean; Part 2 already protects the symptom so this is non-urgent cleanup. Full detail on #11723 comment. (3) boot-instruction fall-through also open.

## Next cycle
- Check #11683 → if shipped, land 4 PRs (merge main, run suite, confirm green, transition). **This is the priority once unblocked.**
- #11723 follow-up (1): root fix is NOT a quick fixture patch (attempt #2 this cycle: (a)+(b) still 404 — bootup-complete doesn't create the role record under isolated SQUIDSQUAD_DIR; harness healthy/no crash). Needs dedicated fresh-context debugging of boot_agent_subprocess stub + bootup-complete role resolution under (a). Lead on #11723. NON-urgent (Part 2 #11729 protects). Consider deprioritizing vs other work — keep deferring until fresh context or until it actually matters operationally.

## Standing
#11538 SHIPPED. #11716 (low improvement-scan) awaiting triage. #11511 not-implementing. #10690/#10686 E6/E7-gated. #11505 blocked (above). Pre-existing test-debt: test_cycle_pre TestGetVerifiableRoles (verifier/qa #6274, quarantined in KNOWN_FAILURES — not mine).
