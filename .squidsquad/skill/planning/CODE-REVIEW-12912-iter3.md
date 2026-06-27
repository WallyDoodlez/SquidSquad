Now I have a thorough understanding of the deploy-signal lifecycle code. Let me compile my findings.

---

### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: 3973-3984
- **Severity**: error
- **Issue**: `_reboot_affected_agents` flips agent intent to DEPLOYING based solely on `agent.intent == INTENT_RUNNING`, ignoring the agent's actual liveness. An agent in "crash-looping" status has `intent=RUNNING` (the health poller preserves intent during crash-loop backoff). The intent flip to DEPLOYING permanently prevents the crash-loop resume branch (line 971-974) from firing — it requires `should_reboot` which is `agent.intent in (RUNNING, RESTARTING)`, excluding DEPLOYING. Status remains "crash-looping", `reboot_blocked_until` retains its old value, but the resume path is unreachable.

- **Evidence**: The crash-loop resume branch (line 971) gates on `should_reboot` (line 972) which is defined at line 784-787 as `agent.intent in (INTENT_RUNNING, INTENT_RESTARTING)`. DEPLOYING is not in this set. `_reboot_affected_agents` at line 3975-3976 checks only `agent.intent == INTENT_RUNNING` without verifying the agent is actually alive (e.g., `agent.status == "running"` or PID alive). An agent in crash-loop (status="crash-looping", PID dead, intent=RUNNING) would have its intent flipped to DEPLOYING, locking it out of all health-poll recovery paths. Only harness restart recovers via `load_state` line 1338-1343.

- **Suggested fix**: Gate the intent flip and deploy-signal emit on the agent being actually alive. Change line 3975 from `if agent and agent.intent == AgentState.INTENT_RUNNING:` to something like `if agent and agent.intent == AgentState.INTENT_RUNNING and agent.status == "running":` or verify PID liveness. Alternatively, add `INTENT_DEPLOYING` to `should_reboot` at line 784-787 and add a timeout path that resets DEPLOYING→RUNNING if the agent stays dead without a deploy-halted ack for too long.

---

### Finding 2

- **File**: `references/scripts/harness.py`
- **Line**: 3976-3984
- **Severity**: warning
- **Issue**: Same root cause as Finding 1, different scenario. `_reboot_affected_agents` sets `intent=DEPLOYING` before the agent receives the deploy-signal. If the agent crashes in the window between the intent flip and its `ack-stop(result=deploy-halted)` response — e.g., during "finish current atomic unit" per AGENT-RUNTIME §8.1 — the health poller will never auto-respawn it. The dead agent's status settles to "deploying" (line 775), which is excluded from `is_dead` at line 782. `should_reboot` excludes DEPLOYING. `reboot_blocked_until` is only set by the ack-stop handler (line 3041), not here. Result: agent permanently stuck until harness restart.

- **Evidence**: The post-ack-stop path at line 3036-3041 sets `reboot_blocked_until = time.time() + _DEPLOY_WINDOW_SECONDS` as defense-in-depth, but this only fires in the ack-stop handler, which the agent never reaches if it crashes before responding. The pre-ack-stop path in `_reboot_affected_agents` sets `intent_set_at` but the force-kill safety net at line 664-665 only covers STOPPING and RESTARTING, not DEPLOYING. There is no dead-agent timeout for DEPLOYING intent.

- **Suggested fix**: Same as Finding 1. Additionally, consider setting `reboot_blocked_until` in `_reboot_affected_agents` (not just in the ack-stop handler) and adding a dead-agent timeout path for DEPLOYING: if the agent is dead with intent=DEPLOYING and either `reboot_blocked_until` has elapsed or was never set, reset to RUNNING and auto-respawn.

---

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: 4241-4251
- **Severity**: warning
- **Issue**: The push-retry loop after a rejected `git push` uses `git pull --ff-only origin main` (line 4251) to recover, but does not check its return value. When another clone pushed first — the scenario the code comment at line 4247 says it handles — local `main` has a local compose commit that diverges from the remote. `git pull --ff-only` will fail (non-zero exit) because it cannot fast-forward a diverged branch. The return value is silently ignored. The next `git push` will also fail for the same reason. After `_DEPLOY_PUSH_RETRIES + 1` (3) futile attempts, the code falls through to `_deploy_recover_and_respawn` — correct recovery, but the retry loop never actually recovers from its documented scenario.

- **Evidence**: The code at line 4249-4251 does `_git_in_clone(clone_path, ["pull", "--ff-only", "origin", "main"])` without capturing or checking the return value. The `--ff-only` flag explicitly refuses to merge; it only succeeds when local `main` is an ancestor of (or equal to) `origin/main`. After a local compose commit, it is not — it has diverged. The retry loop only works for transient network failures (where the pull is a no-op fast-forward to the same commit), not for genuine concurrent-push conflicts which is the scenario documented at line 4247.

- **Suggested fix**: Either (a) use `git pull --rebase origin main` and check the return value, handling rebase conflicts as a recovery case; or (b) drop the retry loop and go directly to `_deploy_recover_and_respawn` on first push rejection, since the sequential `_deploy_lock` makes genuine concurrent-push conflicts extremely rare and the recovery path handles them correctly.

---

### Finding 4 (Iter-2 fix F1 verification — docstring/return mismatch)

- **File**: `references/scripts/harness.py`
- **Line**: 4012, 4053
- **Severity**: warning
- **Issue**: `_respawn_agent_process` docstring states "Returns True iff a fresh process was spawned" (line 4012), but the actual return value is `bool(result.get("success"))` (line 4053). This returns True for `action="skip"` (agent already alive) as well as `action="spawn"`. The caller `_deploy_recover_and_respawn` uses the return value as `respawn_ok` in a deploy-error event emitted to pm (line 4136). An operator seeing `respawn_ok: true` could be misled into thinking a fresh spawn occurred when the agent was simply already alive.

- **Evidence**: `boot_remote.boot_agent` can return `{"success": True, "action": "skip", ...}` when the agent is already running. `_respawn_agent_process` line 4033 correctly distinguishes spawn-vs-skip for its internal state mutations (lines 4034-4045), but line 4053 returns `bool(result.get("success"))` which conflates both outcomes. The docstring at line 4012 promises a narrower contract.

- **Suggested fix**: Either (a) return `spawned` (the variable computed at line 4033) to match the docstring, or (b) update the docstring to "Returns True iff the respawn/reboot succeeded (fresh spawn or agent already alive)". Option (a) would change `respawn_ok` semantics in deploy-error events to mean "fresh process was spawned" which is more precise; `_deploy_recover_and_respawn` already handles the case where `respawn_ok=False` by including it in the event payload.

---

**Summary of iter-2 fix verifications:**

- **F1** (`_respawn_agent_process` returns bool, settles to "error" on failure, "starting" on success-non-spawn): CONFIRMED at lines 4025-4027 (raise → error), 4041-4045 (skip → starting), 4046-4048 (success=False → error), 4053 (returns bool). Minor docstring issue noted in Finding 4.
- **F2** (same as F1): CONFIRMED.
- **F3** (deploy-error carries respawn_ok): CONFIRMED at line 4136.
- **F4** (cursor advance retries once on exception): CONFIRMED at lines 4180-4194 (range(2), retries on exception, logs warning on final failure).
- **F5** (load_state restores status, interrupted "deploying" → "running"): CONFIRMED at lines 1370 (restores status), 1377-1378 (deploying→running).