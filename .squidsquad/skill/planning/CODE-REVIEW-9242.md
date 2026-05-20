NO_FINDINGS

After thorough analysis of all three changed files, all three fixes are correctly implemented and the tests are structurally sound. Specifically:

- **Fix 1 (`--no-auto-start`)**: The module-level `_NO_AUTO_START` switch defaults `False`, is set by `main()` from both the CLI flag and the `SQUIDSQUAD_HARNESS_NO_AUTO_START` env var, and is read by `_deferred_init`'s auto-spawn block before the health poller starts. Production boot path unchanged.

- **Fix 2 (`asyncio.to_thread` wraps)**: All seven (not eight — task description miscounts) async-handler `state.save_state()` call sites are wrapped: `start_all`, `stop_all`, `start_agent`, `receive_event` ×2 (bootup-complete + ack/stop-confirmed), `stop_agent`, `restart_agent`. The five sync/thread-context `save_state()` calls (`update_health`, `_deferred_init`, `_do_shutdown`, `_reboot_affected_agents`, `_graceful_stop`) remain correctly bare. No async handler with a bare `save_state()` was missed.

- **Fix 3 (git_ops source + harness boundary)**: `git_ops._emit` drops events silently when argv inference fails instead of defaulting to `role="unknown"`. The harness `POST /events` boundary check rejects events with roles not in `get_all_roles() ∪ {pm}` with 204 + logged WARNING. Both layers are consistent.

- **Fall-open on config unreadable**: Intentional and justified. The original symptom (HTTP wedge) is worse than letting events through during a transient config-read failure. The primary defense is at the source (git_ops.py never emits unknown); the boundary check is defense-in-depth that must not block all legitimate traffic during a config hiccup.

- **Tests**: The static check for bare `save_state()` in async handlers correctly bounds each top-level handler's body. The sync-functions-remain-bare test's body-range imprecision for nested functions (`_deferred_init` inside `lifespan`, `_graceful_stop` inside `CtrlCHandler`) does not cause false positives — the oversized ranges happen to contain no other `state.save_state()` calls. All 11 tests verify genuine properties.