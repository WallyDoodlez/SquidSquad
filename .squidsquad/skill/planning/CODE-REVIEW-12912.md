I have completed the audit. Here are my findings:

---

### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: 3018-3021 (ack-stop handler spawns `_run_deploy_sequence`) and 4077-4153 (`_run_deploy_sequence` body)
- **Severity**: error
- **Issue**: **Cursor is never advanced past the deploy-signal event.** The TRDs require the harness to advance the agent's cursor past the deploy-signal as part of the deploy sequence before respawn. AGENT-RUNTIME §8.1 states: "do NOT POST ack-cursor; the harness advances the cursor past this deploy-signal as part of the deploy sequence (before respawn)." HARNESS-ARCH §7.1 states: "advance the agent's cursor past the deploy-signal event → respawn the agent." event-mode-contract.md line 97 states: "The harness advances your cursor past the deploy-signal itself, as part of the deploy sequence (before it respawns you)."
- **Evidence**: `_run_deploy_sequence(role)` receives only the `role` parameter — the deploy-signal's `event_id` is available at line 2972 (`ack_event_id = ack_payload.get("event_id")`) but is never passed to `_run_deploy_sequence`. Neither `_run_deploy_sequence`, `_respawn_after_deploy` (line 4023), nor `_deploy_recover_and_respawn` (line 4038) call `event_lifecycle.advance_cursor()`. The only `advance_cursor` caller in the entire file is the `ack-cursor` handler at line 2948. Without cursor advancement, the respawned agent's boot drain re-fetches the same deploy-signal, re-processes it, and re-halts — causing an infinite deploy → respawn → re-halt → deploy loop.
- **Suggested fix**: Pass the deploy-signal's `event_id` to `_run_deploy_sequence`. After a successful push and before `_respawn_after_deploy`, call `event_lifecycle.advance_cursor(role, deploy_signal_event_id)`. This must happen BEFORE the agent respawns. On failure paths, the cursor should ALSO be advanced (otherwise the respawned agent re-halts on the same stale signal), or the deploy-signal should be marked as "consumed" so the agent's care filter can skip it.

---

### Finding 2

- **File**: `references/scripts/harness.py`
- **Line**: 4023-4035 (`_respawn_after_deploy`) and 4038-4058 (`_deploy_recover_and_respawn`)
- **Severity**: error
- **Issue**: **The deploy sequence never results in an actual agent respawn.** Both `_respawn_after_deploy` (success path) and `_deploy_recover_and_respawn` (failure path) set `agent.intent = AgentState.INTENT_RUNNING` but do NOT change `agent.status`. The status remains `"deploying"` (set by the ack-stop handler at line 3012). On the next health poll, `"deploying"` is not in the `is_dead` set `("stopped", "error", "stalled")` (line 782), so `is_dead` is False. The status eventually degrades to `"unknown"` (line 779), which is also not in `is_dead`. Because the auto-reboot trigger `death_candidate` (line 877) requires `is_dead=True` AND `was_alive=True` (i.e., `prev_status == "running"`), the agent is **permanently stuck** — never auto-respawned.
- **Evidence**: Trace through `update_health` after `_respawn_after_deploy`: PID is dead, status is `"deploying"`, intent is `RUNNING`. Line 768 checks `agent.intent == AgentState.INTENT_DEPLOYING` → False (intent is now `RUNNING`). Line 776 checks `prev_status == "running"` → False (`"deploying"`). Line 778 sets status to `"unknown"`. `is_dead` = False. On subsequent polls, `prev_status` = `"unknown"` (never `"running"`), so `was_alive` is always False → `death_candidate` is always False → reboot never fires.
- **Suggested fix**: `_respawn_after_deploy` and `_deploy_recover_and_respawn` must either (a) call `boot_remote.boot_agent(role)` directly, or (b) set `agent.status = "running"` and `agent.claude_pid = None` so the next health poll sees `was_alive=True`, `is_dead=True`, and triggers auto-reboot. Option (b) is simpler and follows the pattern of other cleanup paths (e.g., the crash-looping resume path at line 868 that sets `agent.status = "crash-looping"` then the resume branch at lines 868-879 triggers the actual boot).

---

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: 2994-3013 (ack-stop handler for deploy-halted)
- **Severity**: warning
- **Issue**: **`reboot_blocked_until` is not set in the ack-stop handler.** HARNESS-ARCH §7.3 specifies: "When the harness receives an `ack-stop(result=deploy-halted)` from an agent, it sets `reboot_blocked_until` to a time well beyond the expected git/compose window (e.g., `now + 300s`, overridden on completion) and transitions `intent` to `deploying`." The code sets `intent=DEPLOYING` and `status="deploying"` but never sets `reboot_blocked_until`. This is TRD drift.
- **Evidence**: Lines 3003-3012 set `agent.intent`, `agent.intent_set_at`, and `agent.status`, but `agent.reboot_blocked_until` is never assigned. Compare with the StopFailure backoff branch at line 866 which sets `agent.reboot_blocked_until = now + backoff`. The `_respawn_after_deploy` function at line 4029 clears `reboot_blocked_until = None` — but it was never set, so this is a no-op.
- **Suggested fix**: Add `agent.reboot_blocked_until = time.time() + 300` in the ack-stop handler (line 3010 area) to match the HARNESS-ARCH §7.3 spec. While the status guard (`"deploying"` not in `is_dead`) functionally prevents auto-reboot, the TRD explicitly requires this field as a defense-in-depth mechanism.

---

### Finding 4

- **File**: `references/scripts/harness.py`
- **Line**: 3967-3997 (`_emit_boot_deploy_signals`) vs 3939-3950 (`_reboot_affected_agents`)
- **Severity**: warning
- **Issue**: **Inconsistent intent-sequencing for boot deploy-signals.** `_reboot_affected_agents` (post-merge path) sets `intent=DEPLOYING` BEFORE emitting the deploy-signal (lines 3941-3945: intent set, then save_state, then emit). `_emit_boot_deploy_signals` (boot-drift path) does NOT pre-set intent — it relies on the ack-stop handler at line 3006-3011 to defensively set `intent=DEPLOYING` when the agent responds. AGENT-RUNTIME §5.2's intent-sequencing rule says: "the harness MUST set `intent=deploying`… BEFORE the agent halts and its PID dies — so the health poller does not misread the deploy-halt death as a crash."
- **Evidence**: `_emit_boot_deploy_signals` at lines 3988-3993 calls `_emit_event("deploy-signal", ...)` without calling `state.set_agent()` or `state.save_state()` to set intent first. Between the harness emitting the deploy-signal and the agent's `ack-stop(result=deploy-halted)` arriving at the harness, if the agent's PID dies for any reason (even a legitimate exit), `intent` is still `RUNNING` → the health poll would misread it as a crash and auto-respawn. The docstring at lines 3972-3976 acknowledges this trade-off but the TRD's MUST requirement is not satisfied.
- **Suggested fix**: Either set intent=DEPLOYING before emit (accepting that the health poll's pid_changed logic at line 717-730 will reset it if the agent hasn't fully booted yet), or document the accepted risk explicitly in the TRD as an approved deviation.

---

### Finding 5

- **File**: `references/scripts/harness.py`
- **Line**: 3696 (inside `_emit_event`)
- **Severity**: warning
- **Issue**: **`_emit_event` uses `os.urandom(8).hex()` for event IDs, but deploy-signal events emitted via this path cannot be matched against the agent's `ack-stop` response.** The agent's `event-mode-contract.md` (line 96) instructs the agent to include `event_id: <the deploy-signal's event id>` in the ack-stop payload. The ack-stop handler at line 2994 checks `ack_payload.get("result") == "deploy-halted"` and starts the deploy sequence, but the deploy-signal's `event_id` (available as `ack_event_id` at line 2972) is only used for logging — it's never passed to `_run_deploy_sequence`, and even if it were, it's generated by `os.urandom(8).hex()` (line 3699) which is a random 16-hex string, not the content-hash-based ID described in AGENT-RUNTIME §5.3 / HARNESS-ARCH §5.3. This is a secondary aspect of Finding 1 (cursor advancement needs the event_id), but also reflects that the event ID format used by `_emit_event` diverges from the documented `sha256(timestamp + alias + event_type + payload + nonce)[:16]` formula.
- **Evidence**: AGENT-RUNTIME §5.3 states event IDs use `sha256(timestamp + alias + event_type + payload + nonce)[:16]`. The `_emit_event` function at line 3699 uses `os.urandom(8).hex()` (random, not content-derived). Though functionally both produce 16-char hex, the `_emit_event` docstring itself (line 3696) references #9415 for the width but does not follow the content-hash algorithm. This is pre-existing but becomes load-bearing because the deploy-signal's event_id is what the agent references in `ack-stop` and what needs to be cursor-advanced.
- **Suggested fix**: This is minor — the ID collision risk is negligible with 64-bit random. The real fix is Finding 1 (pass the ID and advance cursor). No separate change needed for this finding unless you want to align with the documented hash formula.