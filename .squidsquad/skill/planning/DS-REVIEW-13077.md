Here are my findings:

---

### Finding 1

- **File**: `tests/test_harness_deploy_12912.py`
- **Line**: 488–506
- **Severity**: error
- **Issue**: `test_recovery_path_emits_single_deploy_error_no_double` is under-patched — it does NOT mock `boot_remote._is_process_alive` or `reboot_agent._kill_process`, so the force-kill abort path it claims to test is never entered. The test falls through to the `boot_agent`-raising branch instead.
- **Evidence**: The test sets `agent.claude_pid = 4242` and patches `_await_pid_death` to return `False`, but never patches `boot_remote._is_process_alive`. In `_respawn_agent_process` at line 4252, the guard `if old_pid and boot_remote._is_process_alive(old_pid)` calls the **real** `_is_process_alive(4242)`. On any real machine, PID 4242 almost certainly does not exist → returns `False` → the entire force-kill block (lines 4252–4274) is skipped. The test then reaches `boot_agent` (patched to `AssertionError`), catches that exception, and emits a single deploy-error. So the test passes, but it exercises the `boot_agent`-raising path (already covered by `test_boot_agent_raises_leaves_recoverable_error_status` at lines 378–386), NOT the force-kill-abort path its own comment describes ("still-alive → respawn aborts inside the call"). On the very unlikely chance PID 4242 *does* exist on the test machine, the unpatched `_kill_process(4242)` would attempt a real OS process kill — a safety hazard.

- **Suggested fix**: Patch `harness.boot_remote._is_process_alive` with `return_value=True` and patch `harness.reboot_agent._kill_process` with a no-op side-effect (matching the pattern used in the `_respawn` helper at lines 358–360). This makes the force-kill block actually execute, `_await_pid_death` return `False`, and `_respawn_agent_process` abort without reaching `boot_agent`. The `boot_agent` patch should then be `side_effect=AssertionError("must not boot over live PID")` to guard the contract that `boot_agent` is never called on this path — which would correctly fail the test if a regression bypasses the abort.

---

### Finding 2

- **File**: `references/scripts/harness.py`
- **Line**: 4211–4216 (docstring of `_respawn_agent_process`)
- **Severity**: warning
- **Issue**: The function docstring states "The agent's PID is already dead (it halted on the deploy-signal)" — this is now false after #13077. The whole purpose of #13077 is that the agent's PID is **not** dead (the LLM cannot self-/quit), and the function actively force-kills it.
- **Evidence**: Lines 4252–4256 show the function explicitly checks `boot_remote._is_process_alive(old_pid)` and calls `reboot_agent._kill_process(old_pid)`. The inline #13077 comment at lines 4233–4250 correctly explains this, but the docstring header contradicts it — a future reader will be confused about whether the PID is expected to be alive or dead on entry.
- **Suggested fix**: Update the first paragraph of the docstring to read something like: "Explicitly respawn a deploy-halted agent's claude process (DS-12912 Finding 2). If the agent's old PID is still alive (the agent cannot self-/quit — #13077), we force-kill it, confirm death, then boot the replacement. After a deploy the agent's status is 'deploying' — which is NOT in the health poller's is_dead set…" (rest unchanged).

---

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: 4377–4379 (docstring of `_respawn_after_deploy`)
- **Severity**: warning
- **Issue**: Same stale statement as Finding 2: "The PID is dead and status is 'deploying' (not in is_dead), so the health poller will not do it." The PID is now **alive** at this point — `_respawn_agent_process` force-kills it.
- **Evidence**: `_respawn_after_deploy` calls `_respawn_agent_process(role)` at line 4386, which force-kills the old PID inside the `_deploy_lock`-held scope. The docstring's premise is wrong.
- **Suggested fix**: Rewrite to: "Successful deploy: respawn the halted agent against the freshly-committed CLAUDE.md. The agent's old PID is still alive (halted but not exited — the LLM cannot self-/quit, #13077), and status is 'deploying' (not in is_dead), so the health poller will not auto-respawn — we respawn explicitly inside `_respawn_agent_process`, which force-kills the old process and boots the replacement."

---

### Finding 4

- **File**: `tests/test_harness_deploy_12912.py`
- **Line**: 348–356 (the `_respawn` helper) — used by all 6 `TestRespawnAgentProcess` tests except `test_recovery_path_emits_single_deploy_error_no_double`
- **Severity**: warning
- **Issue**: The `_respawn` helper patches `harness.boot_remote._is_process_alive` with a single `return_value=pid_alive` — a flat constant. This means tests using the helper cannot verify the case where `_is_process_alive` returns `True` on the pre-kill check but `_await_pid_death` returns `True` afterwards (the normal kill→confirm→boot flow). The test `test_force_kills_old_pid_since_agent_cannot_self_quit` works correctly because it relies on the kill happening when `pid_alive=True` and then `_await_pid_death` (separately patched to return `True`) succeeding. However, the helper's flat `_is_process_alive` return value cannot model the **transition** from alive→dead that the real system provides — `_await_pid_death` is patched separately so this is not currently broken, but the `_is_process_alive` patch scope covers both the pre-kill check (line 4252) AND the internal calls inside `_await_pid_death` (lines 4205/4208). If `pid_alive=True` and `pid_dies=True`, the test has `_is_process_alive` return `True` even during `_await_pid_death`'s polling — yet `_await_pid_death` is separately patched to return `True`, so the internal `_is_process_alive` calls are never reached. This silent patch-overlap works by accident: `_await_pid_death` is replaced wholesale, so its internal `_is_process_alive` calls don't execute. If someone later changes `_await_pid_death`'s test to use `side_effect` instead of `return_value` (to model mid-wait death), the flat `_is_process_alive` patch would return wrong values. Currently correct, but fragile.
- **Suggested fix**: This is a lower-priority observation. The current tests are functionally correct. A follow-up could make `_is_process_alive` use `side_effect` that returns `True` on first call (pre-kill check) then `False` (post-kill in `_await_pid_death`), and remove the `_await_pid_death` patch so the real polling loop is exercised. Tracked as a test-hardening follow-up only — not a correctness bug today.