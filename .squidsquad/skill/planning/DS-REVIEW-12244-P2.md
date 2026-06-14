I have now traced through all the relevant code paths. I found one genuine correctness issue:

---

### Finding 1

- **File**: references/scripts/harness.py
- **Line**: 461–476 (status-update block), 479 (is_dead definition), 572–577 (STOPPING fulfillment)
- **Severity**: error
- **Issue**: **Crash-looping agent stuck when operator issues stop**. If an agent is in `crash-looping` status and the operator sets intent to `STOPPING` via `POST /agents/{role}/stop` (line 2519), the agent can never transition to `stopped` status or `STOPPED` intent. It is permanently wedged in `crash-looping`/`STOPPING`.

  Three mechanisms that normally handle a dead STOPPING agent all fail:

  1. **Status-update dead branch** (line 461): `elif agent.status not in ("starting", "crash-looping")` — `crash-looping` is excluded, so the branch that would set `status = "stopped"` for `STOPPING` intent (line 469–472) never fires.

  2. **`is_dead`** (line 479): defined as `("stopped", "error", "stalled")` — does not include `"crash-looping"`. So `is_dead` is `False`.

  3. **STOPPING fulfillment** (line 572): `if is_dead and agent.intent == AgentState.INTENT_STOPPING` — requires `is_dead == True`, which is `False` for crash-looping.

  The resume `elif` (line 555) also does not fire because `should_reboot` is `False` when intent is `STOPPING`.

- **Evidence**: The `stop_all` endpoint (line 1790) skips agents that `_needs_boot()` returns `True` for (dead agents), so it avoids this path. But the single-agent `POST /agents/{role}/stop` endpoint (line 2518–2522) has **no guard** — it unconditionally sets `intent = STOPPING` on any agent including crash-looping ones. Once set, the health poller can never resolve this combination.

  Reproducible scenario:
  1. Agent enters crash-looping (3+ fast deaths, status=`crash-looping`, intent=`running`)
  2. Operator runs `POST /agents/{role}/stop`
  3. Health poller runs: `prev_status` = `crash-looping`, `is_dead` = `False`, `should_reboot` = `False`
  4. Outer `if is_dead and was_alive and should_reboot` → `False`
  5. `elif` resume → `should_reboot` is `False` → `False`
  6. STOPPING fulfillment → `is_dead` is `False` → `False`
  7. Agent stuck forever in `crash-looping`/`STOPPING`

- **Suggested fix**: Two minimal changes:

  **a)** In the dead-status-update block (line 461), add a clause for crash-looping agents with STOP intent:
  ```python
  elif agent.status == "crash-looping":
      if agent.intent in (AgentState.INTENT_STOPPING, AgentState.INTENT_STOPPED):
          agent.status = "stopped"
          agent.reboot_blocked_until = None  # clear stale backoff
  ```
  
  **b)** In the STOPPING fulfillment check (line 572), also handle the case where the agent was just marked `stopped` from `crash-looping` (so `is_dead` won't have caught it):
  ```python
  if is_dead and agent.intent == AgentState.INTENT_STOPPING:
      agent.intent = AgentState.INTENT_STOPPED
      ...
  elif (agent.status == "stopped" and agent.intent == AgentState.INTENT_STOPPING
        and prev_status == "crash-looping"):
      agent.intent = AgentState.INTENT_STOPPED
      agent.intent_set_at = None
      agent.claude_pid = None
      state_changed = True
  ```

  Or alternatively, add `"crash-looping"` to the `is_dead` set and handle the dead-status-update transition accordingly (requires more restructuring to preserve crash-looping for RUNNING/RESTARTING intents).

---

### Finding 2

- **File**: references/scripts/harness.py
- **Line**: 601–610
- **Severity**: warning
- **Issue**: **Inconsistent `last_spawn_at` guard in auto-reboot path**. In the auto-reboot path, `last_spawn_at` is stamped only when `result.get("terminal_pid")` is truthy (line 601). In the three other spawn paths (lifespan line 1508, `start_all` line 1753, `start_agent` line 1865), `last_spawn_at` is stamped unconditionally when `result["action"] == "spawn"` and `result["success"]` is true — there is no `terminal_pid` gating.

- **Evidence**: Looking at `boot_remote.py`, on success `terminal_pid` is always a truthy integer (`proc.pid`). So in practice this won't diverge — but the pattern is inconsistent. If a future change to `boot_agent` returned `success: True` with `terminal_pid: 0` or `terminal_pid: None` (e.g., a spawn mechanism that doesn't expose a terminal PID), the auto-reboot path would silently skip the `last_spawn_at` stamp. The next death would see `last_spawn_at` as the *previous* spawn's timestamp (or `None`), potentially misclassifying a fast death as slow (if the old timestamp was long ago) or resetting the streak (if `None`).

- **Suggested fix**: Align the auto-reboot path with the other spawn paths — gate on `result["action"] == "spawn"` (or just `result["success"]`) instead of `result.get("terminal_pid")`:

  ```python
  if result.get("success") and result.get("action") == "spawn":
      with self._lock:
          agent = self.agents.get(role)
          if agent:
              agent.terminal_pid = result.get("terminal_pid")
              agent.last_spawn_at = time.time()
  ```

  The `terminal_pid` assignment to `None` (when absent) is already valid — other paths do the same.

---

`NO_FINDINGS` is not appropriate — there is at least one correctness bug (Finding 1, severity: error) that can wedge an agent permanently.