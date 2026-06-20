### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: ~2375–2400 (`_respawn_agent_process`)
- **Severity**: error
- **Issue**: When `boot_remote.boot_agent(role)` raises an exception, `_respawn_agent_process` catches it, logs, and returns without updating any agent state. The agent remains in `status="deploying"` (which is NOT in the health poller's `is_dead` set at line ~583: `is_dead = agent.status in ("stopped", "error", "stalled")`), so the health poller will **never** auto-respawn it. The agent is permanently stuck.
- **Evidence**: The `except` block at lines ~2384–2386 only logs and returns. No `state.set_agent` or `state.save_state` call follows. The `_deploy_lock` is released when `_run_deploy_sequence` returns, and no retry occurs. The `_deploy_recover_and_respawn` caller (line ~2427) emits a `deploy-error` event claiming the agent was respawned when it wasn't.
- **Suggested fix**: In the exception handler, set `agent.status = "error"` (or `"stalled"`) and `agent.intent = AgentState.INTENT_RUNNING` so the health poller's `is_dead` check catches it and auto-respawns on the next poll. Persist with `state.save_state()`. Likewise, guard the `_deploy_recover_and_respawn` deploy-error emit on whether `_respawn_agent_process` actually succeeded.

### Finding 2

- **File**: `references/scripts/harness.py`
- **Line**: ~2389–2397 (`_respawn_agent_process`, after `boot_agent` call)
- **Severity**: error
- **Issue**: When `boot_remote.boot_agent(role)` succeeds but returns `action != "spawn"` (e.g. `"skip"` — another boot already in flight), `agent.status` is **not** set to `"starting"`. The `status = "starting"` assignment is gated inside `if result.get("success") and result.get("action") == "spawn":` (line ~2390). But `agent.intent` is unconditionally set to `RUNNING` at line ~2388. The result: `intent=RUNNING`, `status="deploying"` (leftover from the ack-stop handler). The health poller's `is_dead` does **not** include `"deploying"`, so the agent will never be auto-respawned.
- **Evidence**: Line ~2388: `agent.intent = AgentState.INTENT_RUNNING` runs unconditionally. Line ~2390: `if result.get("success") and result.get("action") == "spawn":` gates `agent.status = "starting"`. A successful but non-spawn result leaves status as the prior value (`"deploying"`), which is absent from the `is_dead` tuple at line ~583.
- **Suggested fix**: Always set `agent.status = "starting"` (or at minimum `"error"`/`"stalled"`) when `intent` is set to `RUNNING` during respawn. The intent+status must form a valid pair that the health poller can recover from if the PID never appears.

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: ~2420–2428 (`_deploy_recover_and_respawn`)
- **Severity**: warning
- **Issue**: `_deploy_recover_and_respawn` calls `_respawn_agent_process(role)` and then unconditionally emits a `deploy-error` event saying the agent was "respawned on existing CLAUDE.md". If `_respawn_agent_process` failed (boot_agent raised or returned non-spawn), the deploy-error event is misleading — the agent was not actually respawned, and the operator investigating the event would be misdirected.
- **Evidence**: `_deploy_recover_and_respawn` at line ~2420–2428 calls `_respawn_agent_process` (which can silently fail per Findings 1–2) then immediately emits `deploy-error` without checking the outcome. The event payload has no field indicating respawn success/failure.
- **Suggested fix**: Have `_respawn_agent_process` return a boolean success indicator. Only emit the `deploy-error` event with the "respawned on existing CLAUDE.md" message if the respawn actually succeeded. If it failed, emit a different diagnostic or log at a higher severity.

### Finding 4

- **File**: `references/scripts/harness.py`
- **Line**: ~2359 (cursor advance in `_run_deploy_sequence`)
- **Severity**: warning
- **Issue**: If `event_lifecycle.advance_cursor(role, deploy_signal_event_id)` raises an unexpected exception (caught and logged), the cursor is NOT advanced past the deploy-signal. If a subsequent `_deploy_recover_and_respawn` respawns the agent successfully, the respawned agent's boot drain will re-fetch the deploy-signal event (which is still ahead of the cursor in the deque) and re-halt — an infinite deploy loop. The exception handler only logs; it does not fall back to any alternative cursor-recovery strategy.
- **Evidence**: Lines ~2359–2366 catch `Exception` from `advance_cursor` and log, but continue with the deploy sequence regardless. If `_deploy_recover_and_respawn` is later called (any stage failure), `_respawn_agent_process` boots a fresh agent whose cursor still predates the deploy-signal. The event-mode-contract Case E explicitly says the agent must not ack-cursor the deploy-signal — the harness owns it — so the agent will re-halt.
- **Suggested fix**: If `advance_cursor` raises, record that the cursor advance failed. Before respawning the agent (in both `_respawn_after_deploy` and `_deploy_recover_and_respawn`), check whether the cursor was advanced. If not, retry `advance_cursor` once, or fall back to advancing to the current deque head (oldest retained event) to guarantee forward progress.

### Finding 5

- **File**: `references/scripts/harness.py`
- **Line**: ~586–589 (health poller `is_dead` check) and ~3100–3120 (`load_state` — does not restore `status`)
- **Severity**: warning
- **Issue**: (Pre-existing, widened by deploy-signal) `AgentState.status` is persisted in `save_state` (line ~925: `"status": a.status`) but is **never restored** in `load_state`. On harness restart, every agent starts with `status = "unknown"` (from `AgentState.__init__`). The health poller's `is_dead` set is `("stopped", "error", "stalled")` — `"unknown"` is absent. If an agent died before harness restart (PID dead, intent=RUNNING), the poller sets status to `"unknown"` (line ~600), which is NOT in `is_dead`, so auto-reboot never fires. The deploy-signal changes add a new persisted status value (`"deploying"`) that also falls to `"unknown"` on restart, widening the window for this latent bug to manifest.
- **Evidence**: `load_state` (lines ~3095–3145) loads ~17 fields from agent_data but does **not** include `agent.status = agent_data.get("status")`. Compare `save_state` line ~925 which DOES persist `"status": a.status`. The health poller at line ~583 defines `is_dead = agent.status in ("stopped", "error", "stalled")` — `"unknown"` is not in this set.
- **Suggested fix**: Either (a) add `agent.status = agent_data.get("status", agent.status)` to `load_state`, or (b) add `"unknown"` to the `is_dead` tuple (and verify no false-positive implications), or (c) have the health poller treat `not alive and agent.status == "unknown"` as a candidate death the same way it treats `"stalled"`. Option (a) is the most surgical and matches the persistence contract.