# QA-RESULTS-10682 — PRD-E / Story E3: L4-write file-watch + restart-required event (REWORK)

**Verified**: 2026-06-02 07:10 (rework)
**Branch**: `skill/e3-l4-filewatch-10682` @ `62ade3e6` (rework on top of `bcb32b7a`)
**PR**: #10746
**Verifier**: qa-lead
**Result**: **PASS** (was FAIL in cycle 560; route-back closed)

## Route-back resolution

Skill addressed every gap from cycle 560's route-back:

- **Harness wiring in this PR** (path 1 from the route-back). `HarnessState` now owns `_l4_observer` / `_l4_debouncer` / `_l4_watcher_thread` / `_l4_watcher_running` state and `start_l4_watcher()` / `stop_l4_watcher()` lifecycle methods.
- **AC5 survive-and-restart loop**: `_l4_watcher_loop` runs on a 5-second cadence (`L4_WATCHER_SUPERVISE_INTERVAL`), each tick calling the testable `_supervise_l4_once(starter)` helper. When `observer.is_alive()` flips False the helper flushes the stale debouncer + respawns the Observer on the same tick.
- **Static-grep gate** on the lifespan wiring (`test_lifespan_calls_start_and_stop`) — asserts both `state.start_l4_watcher()` and `state.stop_l4_watcher()` appear inside `async def lifespan(...)`. This blocks the exact gap I caught at parse-time, not just at unit-test time.
- **Graceful degrade** on missing `watchdog`: import is inside the supervisor thread body. If unavailable, the supervisor logs once and exits; the rest of the harness keeps running.

Rework diff: `harness.py` (+149) + 6 new tests in `test_l4_file_watcher_e3.py`.

## Acceptance Criteria

| # | AC | Evidence (rework) | Status |
|---|---|---|---|
| 1 | File-watch mechanism — watchdog | Lazy import inside `_l4_watcher_loop`; falls back to log-and-exit if missing. Still in module + now wired. | PASS |
| 2 | Watch path: `.squidsquad/project/` recursive | `start_watcher` configures `observer.schedule(..., str(watch_path), recursive=True)`; invoked from harness lifespan. | PASS |
| 3 | On `<role-class>.md` change: identify aliases, run `compose.py deploy <alias>`, emit `assigned-to(...)` | `make_change_callback` chain unchanged from base PR; now actually invoked at runtime via the supervisor's started Observer. | PASS |
| 4 | File-watch primary; optional `.git/hooks/post-commit` script can call `recompose_path` | Module still exposes `recompose_path` for hook-style invocation. Hook itself out of scope per "optional". | PASS |
| 5a | Watcher crash → harness logs + restarts the watcher | `_supervise_l4_once` (line 524-572 of harness.py) checks `observer.is_alive()` and respawns on death. Pinned by `test_dead_observer_is_respawned` + `test_stale_debouncer_flushed_on_respawn`. Supervisor thread itself swallows tick exceptions so a transient fault doesn't kill the supervisor. | PASS |
| 5b | Compose failure → emit compose-failed event (NOT restart-required) | `recompose_for_role_class` constructs `compose-failed` events on compose stderr — unchanged from base, still correct. | PASS |
| 6 | Tests: write → recompose / event emitted / debounce / unrelated → no compose | 22 base + 6 rework = 28 tests on the watcher; **220 passed across watcher + harness + §9a** suites on `62ade3e6`. | PASS |

## Defense-in-Depth (rework additions)

- **`_supervise_l4_once` returns a string action verb** (`"started"` / `"running"` / `"restarted"` / `"start-failed"`) so the regression test asserts the right branch fired without depending on watchdog Observer internals. Makes the supervisor logic testable without spawning real `Observer` threads.
- **Stale-debouncer flush on respawn** — `test_stale_debouncer_flushed_on_respawn` guards against pending timers from a dead Observer firing callbacks into the freshly-spawned one. Subtle race that would have been hard to debug in production.
- **Start-failure path tested** — `test_start_failure_logs_and_retries_next_tick` confirms an exception in `starter()` logs and leaves state unset, so the next supervisor tick retries cleanly. No state-poisoning.
- **Lazy import isolated to supervisor thread** — harness module-import stays free of watchdog as a hard dep. The lazy-import test `test_module_does_not_eagerly_import_watchdog` (existing in the base PR) is preserved.

## v1 Coexistence

§9a v1 byte-stability gate: **5/5 passed** on `62ade3e6`. Harness wiring is additive; existing health-poller lifecycle is untouched (supervisor starts AFTER poller, stops BEFORE poller — explicit ordering rationale in the comment block).

## Test Execution

`pytest tests/test_l4_file_watcher_e3.py tests/test_harness.py tests/test_v1_byte_stability_9a.py -q` on `62ade3e6` → **220 passed in 1.97s** (28 watcher + 187 existing harness + 5 §9a).

The new tests at the harness level:
- `test_first_tick_spawns_observer` — cold start path
- `test_live_observer_is_no_op` — steady-state path
- `test_dead_observer_is_respawned` — **AC5 crash-restart regression**
- `test_start_failure_logs_and_retries_next_tick` — failure path
- `test_stale_debouncer_flushed_on_respawn` — race guard
- `test_lifespan_calls_start_and_stop` — **static-grep gate against the cycle-560 gap**

## Outcome

The route-back caught a real integration gap that skill resolved cleanly. The rework delivers a properly wired file-watch with crash-restart resilience, lifecycle ordering, graceful degrade on missing `watchdog`, and a static-grep regression guard that prevents the exact gap from recurring. **Transitioning #10682: pending-test → pending-ship.**
