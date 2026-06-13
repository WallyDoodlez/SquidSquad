# Working State

- **Task**: #11587 — uvicorn loop=none (harness ProactorEventLoop fix) — COMPLETE, PR #11722
- **Status**: in-progress — HELD pre-pending-test, gated on #11683 shipping (full-suite green)
- **Updated**: 2026-06-13 07:44
- **Branch**: squidsquad/task/11587 (current). Other in-flight: task/11640, task/11641.
- **Quiet Cycle Counter**: 0 (iter-457: implemented #11587)

## ⚠️ Session note
Harness DOWN (port 59999, curl exit 7) — loop-mode (skill pinned stable per #11586). `/loop 30m` cron c8644353. cycle_pre/post DON'T fire — commit/push/PR MANUALLY. working-state.md is PER-BRANCH in git — switching branches swaps it; git tree + issue status is truth ([[learning-resume-git-tree-is-truth]]).

## THREE skill PRs in flight — ALL gated on #11683 ship
| Issue | Fix | Branch | PR | Tests | DS | State |
|---|---|---|---|---|---|---|
| #11640 | _get_clone_path raises (no REPO_ROOT fallback); spawn paths refuse | task/11640 | #11709 | 237 | NO_FINDINGS | in-progress, gated |
| #11641 | thin_launcher reclaims stale scheduled_tasks.lock before Popen | task/11641 | #11715 | 37 | NO_FINDINGS | in-progress, gated |
| #11587 | uvicorn loop="none" → SelectorEventLoopPolicy governs server loop | task/11587 | #11722 | 9 | running (b0gcqdjtm) | in-progress, gated |

All own-tests-green; each held ONLY because merging current main pulls in the #11657 stale event_poll test (the single full-suite red).

## ⚠️ The shared gate: #11683 (carries #11657 + #11503), pending-ship, MERGEABLE
Unshipped ~5 cycles. DM-starvation (harness down → DM not waking). Shipping #11683 → main green → I merge into all 3 branches → all → pending-test. Escalated on #11586 (iter-455). ALSO removes a test that kills live Monitors (iter-456 triage). **Operator action: manually ship #11683.**

## #11587 detail (this cycle)
uvicorn 0.41.0 asyncio_loop_factory hard-codes ProactorEventLoop on win32 (use_subprocess=False), bypassing the #9562 policy entirely. Server.run()→asyncio.run(serve(), loop_factory=get_loop_factory()); loop='auto'→Proactor factory. Fix: _build_uvicorn_config() sets loop='none'→factory None→asyncio.run uses new_event_loop()→respects policy→Selector. Commit a81f532e9. Read DS output (b0gcqdjtm); address real findings on PR #11722.

## Next cycle
- Check #11683 mergedAt → if shipped, for EACH branch (task/11640, task/11641, task/11587): merge origin/main, run tests/run_tests.py, confirm green, transition → pending-test.
- Read #11587 DS review (b0gcqdjtm); address findings.
- If harness comes back up: #11586 (A) reboot→loop-mode becomes diagnosable.

## Standing
- **#11538 / PR #11564**: ✅ SHIPPED. **#11716 (low)**: improvement-scan filed (run_tests.py target drift) — awaiting triage.
- **#11586 (high)**: event-mode/DM-starvation — (B) resolved (folds into #11683), (A) reboot→loop-mode open, operator/harness-gated. **#11511**: PR conflict-flap, NOT implementing (awaiting PM/operator). #10690/#10686: E6/E7/operator-gated. #11505 (low): deadwood.
