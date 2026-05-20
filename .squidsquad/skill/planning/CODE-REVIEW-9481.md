# STATUS: REVIEWED
# Task: #9481
# Reviewer: claude-sonnet (fallback — deepseek hung)

## Summary

The fix correctly identifies and resolves the actual root cause (synchronous `update_health()` blocking the asyncio event loop) rather than the issue body's hypothesis (Proactor policy on a daemon thread). The two-part approach — drop the inline call from `/status` entirely and wrap it in `asyncio.to_thread` for the other three handlers — is the right shape and consistent with the #9242 `save_state` precedent. One test reliability issue is worth noting but is low-severity and does not block ship.

## Findings

### F1 — `test_start_poller_invoked_in_lifespan` is sensitive to how `lifespan`'s nested `def` is indented — low
**Evidence:** `_extract_handler_body` uses `source.find("\ndef ", sig_end)` as a boundary sentinel. `lifespan` contains a nested `def _deferred_init():` at line 980, indented 4 spaces (`    def _deferred_init():`). The raw text is `\n    def _deferred_init():` — the sentinel pattern is `"\ndef "` (no leading spaces), so this match will NOT fire and the function body is extracted correctly through `state.start_poller()` at line 1061. The test passes as-is.

However, the safety is accidental: if `_deferred_init` were ever dedented to column 0 (unlikely but possible in a refactor), the boundary would fire prematurely and the test would produce a spurious false-negative (missing `start_poller()`), making it look like a regression when none exists. The fix would be to anchor the sentinel to `\ndef [a-z]` at column 0, but this is cosmetic — current code is correct.

**Suggested fix (optional):** Add a comment in `_extract_handler_body` noting that the sentinel relies on top-level-only whitespace convention, so a future refactorer knows not to reindent `lifespan`'s inner functions. No code change required to ship.

### F2 — `/status` has an up-to-5s stale window on first boot — low
**Evidence:** `_poll_loop` runs `update_health()` immediately on first iteration (no initial sleep before the call, per lines 362-368), then sleeps `HEALTH_POLL_INTERVAL` (5s). However, `start_poller()` is called at line 1061 after the synchronous legacy-sentinel cleanup, and `_deferred_init` (which runs `load_state()`) starts concurrently in its own thread. There is a race: the poller's first call to `update_health()` may run before `load_state()` completes, meaning initial agent state could be empty on the first poll pass. This is pre-existing behavior — it was true even before this fix — and the comment at line 1005 explicitly acknowledges the `HEALTH_POLL_INTERVAL` window. Not a regression introduced by #9481.

**Impact:** Negligible. An operator running `curl /status` within the first 5s of a cold boot with zero agents registered will see an empty agents list, which is correct (no agents have been polled yet). The AC says "returns 200 within 5 seconds" — that is satisfied regardless of agent list contents.

### F3 — `asyncio.to_thread` on `update_health` does not prevent lock contention with the background poller — low
**Evidence:** `update_health()` acquires `state._lock` for its entire duration (lines 195-347). If `GET /agents`, `GET /agents/{role}`, and `GET /agents/{role}/health` all fire concurrently, each call spawns a worker thread that contends on `state._lock`. This is the correct behaviour — the lock serialises them — but it means that under high concurrency, these three endpoints can still exhibit latency spikes on Windows (each waiting for a 10-20s `tasklist` pass). This is pre-existing and not a regression from this fix; `/status` is the AC-bound endpoint and is unaffected. The other three endpoints are intentional per-request probes (the docstrings say so), and the `to_thread` fix is sufficient to unblock the event loop.

**Suggested fix (optional):** Long-term, these endpoints could also switch to the background-poller pattern (return cached state). But that's out of scope for #9481 which targets the wedge.

## What was checked

- **AC satisfaction**: Confirmed. `get_status` (lines 1118-1149) contains no call to `update_health()` — neither bare nor wrapped. It reads `state.all_agents()` (cached in-memory dict under lock) and returns immediately. Should respond in microseconds regardless of agent count.
- **Background poller is the sole freshness path for /status**: Confirmed. `lifespan` calls `state.start_poller()` at line 1061 before `yield`, guaranteeing the poller is running before any HTTP request is served. `_poll_loop` (lines 362-368) calls `self.update_health()` on every iteration. No other code path refreshes health for `/status`.
- **No caller assumes /status ran update_health()**: Confirmed. `squidsquad_cli.py _harness_alive` (line 63) and `cycle_pre.py` (line 277) both use `/status` as a liveness probe only — they check for HTTP 200 and do not parse or act on agent health fields. No caller relies on inline freshness from `/status`.
- **Test robustness — boundary detection**: `_extract_handler_body` uses `source.find()` (first occurrence), which correctly targets `HarnessState._poll_loop` at line 362 and not the second `_poll_loop` at line 2440. Nested `def`s inside handlers are indented (not at column 0), so `"\ndef "` boundaries do not fire prematurely for `lifespan`. The `re.sub(r"``[^`]*``", "")` in `test_get_status_does_not_call_update_health` correctly strips the RST double-backtick spans in the new docstring before the pattern match. Tests are stable against legitimate refactors that preserve whitespace conventions.
- **Regression risk from stale /status**: Acceptable. `HEALTH_POLL_INTERVAL = 5` seconds (line 44). The AC explicitly requires a 200 within 5s — that is a liveness guarantee, not a freshness guarantee. Operators who need per-request freshness for a specific agent use `GET /agents/{role}/health`, which still calls `update_health()` (via `to_thread`).
- **Test registration**: `test_9481_update_health_off_event_loop` is present in `STATIC_TEST_MODULES` at line 105 of `tests/run_tests.py`. Confirmed.
- **Import guard**: The test file wraps `_load_module` in a try/except with `HARNESS_AVAILABLE = False` fallback (lines 56-65), but none of the test classes are guarded by `@unittest.skipUnless(HARNESS_AVAILABLE, ...)`. If harness import fails (e.g., a missing dependency on CI), the tests will error rather than skip. This is consistent with the project's other harness tests — not a new issue introduced here.

## Recommendation

Ship as-is. F1 and F2 are cosmetic / pre-existing; F3 is pre-existing and explicitly accepted by the design. The core fix is correct, minimal, and consistent with the established `to_thread` pattern in this codebase.
