# Working State

- **Task**: #11587 — uvicorn loop=none (harness ProactorEventLoop fix) — COMPLETE, PR #11722
- **Status**: in-progress — HELD pre-pending-test, gated on #11683 shipping (full-suite green)
- **Updated**: 2026-06-13 10:14
- **Branch**: squidsquad/task/11587 (current). Other in-flight: task/11640, task/11641.
- **Quiet Cycle Counter**: 0 (iter-462: FOUND #11586 root cause — harness was up all along; stale .harness-port)

## ⚠️ Session note — CORRECTED iter-462
Harness is **UP on 7373** (16h uptime, healthy) — NOT down. My loop-mode all session was caused by a STALE .harness-port=59999 in my clone (probed dead 59999→exit 7→loop). FIXED: corrected .harness-port→7373 (now curl-reachable). Mode is sticky this session (stay loop), but future boot reaches event mode. `/loop 30m` cron c8644353. working-state.md is PER-BRANCH; git tree is truth ([[learning-resume-git-tree-is-truth]]).

## ⭐ #11586 ROOT CAUSE FOUND (iter-462) — stale client-side .harness-port, NOT harness availability
Harness healthy on 7373 whole time. Agents with NO port file default to 7373 (reach harness); agent with STALE port file probes dead port→loop mode. Matrix: pm/qa=MISSING→7373✓, dm=7373✓, skill=59999(dead)→loop✗. Vector: harness _deferred_init (harness.py:1280-1294) distributes its port to all .local-config clones; an integration test starting a harness on ephemeral 59999 (find_free_port(59999), test_harness.py) writes that dead port into REAL clones, teardown doesn't restore → strands live agents. Instance of [[learning-tests-must-not-mutate-shared-live-state]]. Reported on #11586.
**DURABLE FIX (next cycle, skill-domain, NOT gated on #11683):** (1) tests must not distribute ephemeral port into real clones (isolate .local-config / guard _deferred_init / restore in teardown); (2) harden _discover_port (event_poll.py + cycle_post.py) to treat a non-listening port-file value as stale → fall through to default/parent-walk. Own branch off main; own tests green; independent of #11683.

## THREE skill PRs in flight — ALL gated on #11683 ship
| Issue | Fix | Branch | PR | Tests | DS | State |
|---|---|---|---|---|---|---|
| #11640 | _get_clone_path raises (no REPO_ROOT fallback); spawn paths refuse | task/11640 | #11709 | 237 | NO_FINDINGS | in-progress, gated |
| #11641 | thin_launcher reclaims stale scheduled_tasks.lock before Popen | task/11641 | #11715 | 37 | NO_FINDINGS | in-progress, gated |
| #11587 | uvicorn loop="none" → SelectorEventLoopPolicy governs server loop | task/11587 | #11722 | 9 | NO_FINDINGS | in-progress, gated |

All own-tests-green; each held ONLY because merging current main pulls in the #11657 stale event_poll test (the single full-suite red).

## ⚠️ The shared gate: #11683 (carries #11657 + #11503), pending-ship, MERGEABLE
Unshipped ~5 cycles. DM-starvation (harness down → DM not waking). Shipping #11683 → main green → I merge into all 3 branches → all → pending-test. Escalated on #11586 (iter-455). ALSO removes a test that kills live Monitors (iter-456 triage). **Operator action: manually ship #11683.**

## #11587 detail (this cycle)
uvicorn 0.41.0 asyncio_loop_factory hard-codes ProactorEventLoop on win32 (use_subprocess=False), bypassing the #9562 policy entirely. Server.run()→asyncio.run(serve(), loop_factory=get_loop_factory()); loop='auto'→Proactor factory. Fix: _build_uvicorn_config() sets loop='none'→factory None→asyncio.run uses new_event_loop()→respects policy→Selector. Commit a81f532e9. DS review DONE → NO_FINDINGS (all 5 criteria verified). PR #11722 implementation-clean. All 3 PRs now DS-clean.

## #11505 (low) — PLANNED this cycle (iter-458), in-progress, NOT executed
Deadwood removal (capability sub-skill layer). Footprint mapped: in-scope = capability-check.md + dm/includes.yml:19 + dm/instructions.md:8 (DM is the ONLY consumer) + empty capabilities/ dir + installer-files.txt + test_feat328_coverage delete + KNOWN_FAILURES -1 + sub-skill-catalog entry. Scope judgment: manifest.py/capability_check.py installer-core capability machinery is OUT (not in ACs; gutting it = separate higher-risk change; asked PM to confirm §8.3 intent). Plan posted on #11505 (work contract).
- **iter-460 SCOPE CONFLICT (stopped execution):** branched task/11505 off main to execute, but deeper trace found capability-check is NOT isolated deadwood: capability_check.py is load-bearing in **PM task-intake** (task-intake.md:70 'Capability gap analysis', composed into PM via pm/includes.yml:31) + DM startup; AND manifest.md:149 + catalog:143 EXPLICITLY say its removal is 'not this PR — paired with #10025 (capability-framework retirement, OPEN)'. AC4's L1-L3 sweep would silently delete a PM workflow step + contradict #10025. capabilities/ DIR already gone (2026-05-27). Posted finding + 3 options (downscope / close-as-superseded-by-#10025 / confirm-full-retirement-with-PM-signoff). Deleted the empty task/11505 branch (no edits made). **BLOCKED on PM/operator disambiguation of #11505↔#10025 overlap.** Do NOT execute until resolved. (Earlier CQ-AC + AC7#11683 blockers also still stand if it proceeds.)

## Next cycle
- Check #11683 mergedAt → if shipped, for EACH branch (task/11640, task/11641, task/11587): merge origin/main, run tests/run_tests.py, confirm green, transition → pending-test.
- Check #11505 for PM's CQ-AC answer → if answered, execute the bounded removal plan (own branch task/11505 off main).
- (#11587 DS review done — NO_FINDINGS.) If harness comes back up: #11586 (A) reboot→loop-mode becomes diagnosable.

## Standing
- **#11538 / PR #11564**: ✅ SHIPPED. **#11716 (low)**: improvement-scan filed (run_tests.py target drift) — awaiting triage.
- **#11586 (high)**: event-mode/DM-starvation — (B) resolved (folds into #11683), (A) reboot→loop-mode open, operator/harness-gated. **#11511**: PR conflict-flap, NOT implementing (awaiting PM/operator). #10690/#10686: E6/E7/operator-gated. #11505 (low): deadwood.
