# Working State

- **Task**: #9481 (harness HTTP wedge — move update_health off the asyncio event loop)
- **Status**: in-progress
- **Started**: 2026-05-20 01:43
- **Last Processed Event ID**: 9d7c2489
- **Branch**: squidsquad/task/9481

## Completed Steps

- Prior session investigation: minimal repro falsified the issue body's IOCP+daemon-thread hypothesis (uvicorn on daemon thread under default ProactorEventLoopPolicy returns 200 in ms). Actual cause: four read-only async handlers (`/status`, `/agents`, `/agents/{role}`, `/agents/{role}/health`) called `state.update_health()` synchronously on the asyncio loop. On Windows, `update_health()` shells out to `tasklist` per agent under `state._lock` (~10-20s cold-cache blocking call) — same anti-pattern shape as #9242's save_state.
- harness.py: `/status` no longer calls update_health inline (background poller is the freshness source); other three handlers wrap in `await asyncio.to_thread(state.update_health)`.
- tests/test_9481_update_health_off_event_loop.py: 3 test classes pinning the invariant — /status no inline call, other handlers wrapped in to_thread, _poll_loop + lifespan still drive freshness.
- Workspace recovery this cycle: moved staged work from squidsquad/task/8999 (wrong branch) → squidsquad/task/9481 (correct branch).

## Remaining Steps

- Run full test suite (this cycle).
- Self-verification reflection (regression / integration / philosophy / personas).
- External code review against harness diff + tests.
- Commit on branch, open PR, transition → pending-test.
- PR description must flag the divergence from the issue body so PM can update the body per #8917.

## Key Decisions

- Implementation diverges from the issue body's proposed one-line `WindowsSelectorEventLoopPolicy` fix because empirical repro falsified the hypothesis. Test file documents the falsification. No CONTEXT-9481.md exists, so no locked decision to honor — divergence will be flagged in PR description for PM.
