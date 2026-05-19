# External Code Review — #8999 (Claude fallback)

Model: deepseek-v4-pro hung after 12+ minutes with no output; per workflow §9c,
fell back to Claude (sonnet) sub-agent for the review.

## Findings + Dispositions

1. **[medium] Per-event atomicity not directly verified — only final cursor observed**
   `tests/integration/test_event_mode_e2e.py` reads the cursor only after the
   subprocess exits, so it cannot distinguish per-event writes from a single
   end-of-batch write. The implementation in `event_poll.py` already writes
   per-event atomically — this is an observational coverage gap, not a behavior
   gap.
   - **Disposition**: justified-ignore for this PR. A per-event-observation
     test would require killing the subprocess mid-batch, which crosses into
     §4.2 (crash recovery) territory. Better covered there.

2. **[low] Second poll in `test_skim_then_advance` implicitly tests cursor-from-file**
   The second `_run_event_poll(limit=100)` call (no `--since`) reads the cursor
   from `working-state.md`. This is intentional and documented at line 269-270.
   - **Disposition**: justified-ignore. Behavior is load-bearing and documented.

3. **[low] `/events/for/{role}` over-fetch multiplier may still under-fetch
   under aggressive role+type filtering**
   `harness.py:1363-1383` over-fetches by `limit * 3` then filters; if filter
   discards >2/3 of results the trimmed batch may still drop events.
   Pre-existing — not introduced by this PR.
   - **Disposition**: file-to-pm as a separate concern (out of scope for #8999).

## Clean (no finding)

- `get_since` slicing fix (harness.py:484): correct oldest-first semantics.
- Regression: no-`since` callers unchanged (events[-limit:] preserved).
- Test HTTP shim fidelity: mirrors harness endpoint logic exactly.
- §4.10 ACs 1, 3, 5, 6 verified strongly; 4, 7 partial (Finding 1).
- Filesystem hygiene: `.harness-port` backup/restore, test role dir cleanup.
- Threading: `ThreadingHTTPServer.shutdown` + `server_close` + bounded join.
- run_tests.py wiring correct.
- Philosophy match: no over-engineering, no extra abstractions.

## Verdict

Ready to ship. No design-level flaws found. Finding #3 will be noted in the
PR comment for PM awareness but does not gate this PR.
