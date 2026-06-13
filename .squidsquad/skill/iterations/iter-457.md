# Iteration 457 — implemented #11587 (uvicorn ProactorEventLoop fix)

**Mode**: loop (harness DOWN). Manual ops.

## What happened
- Gate re-check: #11683 still unshipped (5th gated cycle); harness still down (59999, exit 7). My 2 PRs (#11709/#11715) still blocked; #11586(A) still undiagnosable (harness down).
- Stopped re-escalating (noise) and picked up genuinely-actionable skill-owned work: **#11587** (high-blast-radius harness asyncio bug — auto-approved). It could relate to harness instability, though reported as "cosmetic today."
- **Diagnosed precisely** (read installed uvicorn 0.41.0 source): `asyncio_loop_factory` HARD-CODES `asyncio.ProactorEventLoop` on win32 (use_subprocess=False), bypassing the event-loop policy. `Server.run()`→`asyncio.run(serve(), loop_factory=get_loop_factory())`; `Config(loop='auto').get_loop_factory()` = ProactorEventLoop on win32 → the #9562 main-thread SelectorEventLoopPolicy never governs the daemon-thread server loop. Confirms the issue's investigation lead.
- **Fix**: extracted `_build_uvicorn_config()` (testable seam) setting `loop='none'` → factory None → `asyncio.run` uses `new_event_loop()` → respects policy → SelectorEventLoop. Verified empirically: `Config(loop='none').get_loop_factory() is None`; `new_event_loop()` under policy = `_WindowsSelectorEventLoop`; `loop='auto'` = ProactorEventLoop factory. Cross-platform safe.
- **Tests**: tests/test_11587_uvicorn_selector_loop.py — 5 new behavioral+wiring (loop=none contract, factory-is-None, rationale-lock loop=auto⇒Proactor on win32, end-to-end none+policy⇒Selector, main()-uses-helper) + 4 #9562 regression = 9 pass. Full suite: only the pre-existing #11683-gated event_poll red; zero new failures.
- Committed a81f532e9, pushed task/11587, opened **PR #11722**, posted status on #11587, spawned DS review (b0gcqdjtm). Held in-progress (same #11683 gate).

## Net: 3 skill PRs now in flight, all gated on #11683 ship (#11709, #11715, #11722).

## Next cycle
- #11683 mergedAt → if shipped, land all 3 PRs (merge main, run suite, confirm green, transition).
- Read #11587 DS output (b0gcqdjtm); address findings on PR #11722.
