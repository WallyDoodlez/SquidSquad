All four fix areas (F1–F4) have been verified against the code. Here is my assessment:

**F1** (lines 4003-4004): The gate `agent.status == "running"` correctly excludes crash-looping (`status="crash-looping"`), paused, stalled, and starting agents from the DEPLOYING flip. Verified that `should_reboot` at line 807-809 excludes `INTENT_DEPLOYING`, so a crash-looping agent flipped to DEPLOYING would indeed be locked out of the resume path. The gate prevents this. ✓

**F2** (lines 770-796): When a dead agent has `intent=DEPLOYING` for longer than `_DEPLOY_WINDOW_SECONDS` (300s), intent is reset to `RUNNING` and status to `"running"`. On the next poll, `prev_status == "running"` causes `status = "stalled"`, `is_dead` becomes True, and the normal auto-reboot path fires. This is a two-poll recovery (bounded, 5–10s). The `_deploy_age` computation at line 782-784 guards against `intent_set_at is None`. ✓

**F3** (lines 4275-4286): Push rejection routes directly to `_deploy_recover_and_respawn` with zero retries. The comment correctly explains why a retry is futile (the clone holds a local compose commit; `git pull --ff-only` can't fast-forward a diverged branch). ✓

**F4** (lines 4033-4052): Docstring updated — `respawn_ok` means "agent is now alive/recovering" (True for spawn OR already-alive skip), not "fresh PID spawned." The `_respawn_agent_process` body at lines 4068-4080 correctly implements this: `action="skip"` (already alive) returns True, `success=False` returns False, and exceptions return False. The call site at line 4162 feeds this into the deploy-error event's `respawn_ok` field. ✓

**Cross-checked interactions**: 
- F1 + F2 interact correctly: a `_reboot_affected_agents` that flips intent→DEPLOYING right before the agent crashes is recovered by F2 after 300s.
- F2 + the crash-loop backoff interact correctly: F2 resets intent→RUNNING, then the normal death path runs, and if the respawn repeatedly fails, the crash-loop breaker accumulates and backs off.
- The `_emit_boot_deploy_signals` path (line 4091) intentionally does NOT gate on `status=="running"` — it does NOT pre-set intent to DEPLOYING, so the concern motivating F1 does not apply there. The ack-stop handler (line 3044-3055) sets DEPLOYING synchronously before the PID dies.
- Cursor advance (lines 4208-4229) prevents the infinite deploy→respawn→re-halt loop (AC4).

**No new stuck-agent, infinite-loop, or crash-misread paths found.**

NO_FINDINGS