I now have full context. Let me compile my findings.

---

### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: 3995–3998 (EAD stamp) and 333–372 (`progress_liveness`)
- **Severity**: warning
- **Issue**: Handoff re-emits (#12442) perpetually refresh `last_dispatch_at` with the same 600s interval as the grace window, creating a **false-negative window** where a zombie verifier/DM agent can never be detected. The re-emit cadence (`_HANDOFF_REEMIT_SECONDS = 600`, line 3739) exactly equals `ACTIVITY_GRACE_SECONDS = 600` (line 134). Each re-emit stamps `last_dispatch_at = check_time` (line 3998), resetting the grace clock. The zombie is then in `"dispatch-grace"` → alive for the entire next 600s, at which point another re-emit fires and repeats the cycle indefinitely. The only gap where the zombie could read dead is the sub-poll-interval window between grace expiry and the next re-emit — and only if the EAD poll doesn't land at the exact boundary.
- **Evidence**: Trace a handoff zombie (e.g., verifier never acts on `pending-test`):
  1. T0: fresh transition, `last_dispatch_at = T0`, `_mark_handoff_emit(T0)`
  2. T0+600: `_handoff_due` returns True, re-emit fires, `last_dispatch_at = T0+600` (reset)
  3. T0+600 to T0+1200: `now - last_dispatch_at ≤ 600` → `"dispatch-grace"` → alive
  4. T0+1200: re-emit again, `last_dispatch_at = T0+1200` … cycle repeats forever
  The zombie never reaches the `"wedged-no-activity-since-dispatch"` verdict because `last_dispatch_at` moves forward in lockstep with the grace expiry. Non-handoff dispatches (worker `status:approved`/`status:open`) are unaffected — they emit once and correctly age out.
- **Suggested fix**: For the cutover, the re-emit path should either NOT refresh `last_dispatch_at` (the grace should be measured from the *original* dispatch, not the re-nudge), OR the re-emit interval must be strictly longer than the grace window (e.g., `_HANDOFF_REEMIT_SECONDS = 1200`), OR a separate counter (`reemit_count`) should cap the number of grace resets. The comment at lines 3991–3993 acknowledges this as deferred, but the shadow data from the current design cannot observe the perpetual-grace problem because it never produces a "wedged" verdict for handoff zombies — so the divergence data won't inform the cutover decision as intended.

---

### Finding 2

- **File**: `references/scripts/harness.py`
- **Line**: 333–372 (`progress_liveness` method body)
- **Severity**: warning
- **Issue**: `progress_liveness` reads multiple fields — `self.bootup_complete` (line 351), `self.last_dispatch_at` (lines 360, 363, 368), `self.last_activity_at` (line 367), and the pause flags via `self.active_pause(now)` (line 356, which reads `in_flight_until`/`compacting_since`/`waiting_since` at lines 308–316) — **without holding `state._lock`**. All of these fields are written by other daemon threads under `state._lock`: the EAD writes `last_dispatch_at` (line 3998), the activity hook writes `last_activity_at` (line 2513) and the pause flags (lines 2526+), and `save_state`/`load_state` also hold `state._lock`. While CPython's GIL makes individual attribute reads atomic, the compound read across five fields is not guaranteed consistent. A TOCTOU interleaving could, for example, read a stale `last_dispatch_at` (just before a re-emit) and a fresh `last_activity_at` (just after an activity hook), producing a verdict based on a cross-section of state that never existed at any single point in time.
- **Evidence**: `state._lock` is a `threading.Lock()` (non-reentrant, line 428). The EAD thread (`activity-detector`, line 3842) and the health-poller thread (`health-poller`, line 944) both acquire it for writes. `progress_liveness` — when called from the health poller in the next slice — will read these fields without that lock. The writes are unlocked relative to these reads, so there is no happens-before edge guaranteeing visibility of the latest values from other threads. The Python memory model for non-synchronized cross-thread access to plain object attributes makes no ordering guarantees.
- **Suggested fix**: When `progress_liveness` is wired into the health poller at cutover, either: (a) call it from within an existing `with state._lock:` block that the health poller already holds (most natural — the caller already holds the lock when reading agent state for the PID-based liveness check), or (b) document that snapshot inconsistency is acceptable at the call site because the observational-then-cutover gating catches any resulting jitter. For this slice (observational only, not yet called), this is forward-looking.

---

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: 3979–3998 (emit → mark_emitted → state._lock ordering)
- **Severity**: warning
- **Issue**: The `_emit_event` call (line 3980) and `mark_emitted` (line 3986) execute **before** the `with state._lock:` block (line 3995). If `_emit_event` or `mark_emitted` raises an unhandled exception, the `last_dispatch_at` stamp is skipped. While `_poll_loop` (line 3854) catches exceptions at the per-cycle level, an exception from `_emit_event` would leave the dedup state (`_emitted_issues`) unstamped for that issue, causing a **duplicate emit on the next poll** (the status appears fresh again because `mark_emitted` was never called). More critically, the dispatch reference is never recorded, so `progress_liveness` will return `"idle-no-dispatch"` for this agent indefinitely for this work item — the dispatch is invisible to the liveness check (a false-negative for this specific dispatch).
- **Evidence**: The ordering at lines 3979–3998:
  1. `_emit_event(...)` — can fail (file I/O, event stream full, etc.)
  2. `self.mark_emitted(...)` — can fail (lock contention, though unlikely)
  3. `with state._lock: ... last_dispatch_at = check_time` — never reached if (1) or (2) raise.
  The `mark_emitted` call is the dedup record; if it fails, the issue re-emits next poll as a fresh transition (the old `_emitted_issues` entry wasn't updated). On that re-emit, `last_dispatch_at` IS stamped. So the window is one poll interval (~60s). The practical blast radius is small, but the invariant "every assigned-to emit MUST stamp last_dispatch_at" is technically violated.
- **Suggested fix**: Reorder so `last_dispatch_at` is stamped (under `state._lock`) BEFORE `mark_emitted`, or wrap the emit+mark+stamp in a single try/except that either commits all three or rolls back the emit. Example reorder:
  ```python
  with state._lock:
      _disp_agent = state.agents.get(target_alias)
      if _disp_agent is not None:
          _disp_agent.last_dispatch_at = check_time
  _emit_event(...)
  self.mark_emitted(issue_num, status)
  ```
  (The stamp-before-emit ordering is safe because `check_time` is a past epoch; the agent's eventual activity heartbeat will carry a later timestamp, so `last_activity_at >= last_dispatch_at` still holds.)

---

### Finding 4

- **File**: `references/scripts/harness.py`
- **Line**: 3995–3998
- **Severity**: warning
- **Issue**: The EAD stamps `last_dispatch_at` for **any** agent found in `state.agents`, regardless of that agent's `intent` (RUNNING/STOPPED/STOPPING/RESTARTING). If an agent is in STOPPED intent and a handoff re-emit fires, `last_dispatch_at` is refreshed. Later, if the agent is restarted, its `bootup_complete` becomes True after boot, and the stale `last_dispatch_at` from the stopped period remains. The agent would then need a `last_activity_at >= last_dispatch_at` to be "active." During boot, the agent emits activity (PreToolUse for boot commands), so this typically self-corrects. However, if the boot completes (`bootup_complete = True`) and the agent's first post-boot activity lands BEFORE the refresh of `last_dispatch_at` that occurred during boot (e.g., a re-emit fires mid-boot), the agent could briefly read "wedged" after bootup. The window is narrow and self-correcting, but it introduces non-determinism into the shadow data for restarted agents.
- **Evidence**: The EAD code at line 3995–3998 does not filter by `_disp_agent.intent` or `_disp_agent.status`. The stamp is unconditional on agent liveness. Combined with the handoff re-emit refresh, a STOPPED agent can accumulate fresh `last_dispatch_at` timestamps that outlive the stop period.
- **Suggested fix**: Guard the stamp with an intent/status check:
  ```python
  if _disp_agent is not None and _disp_agent.intent == AgentState.INTENT_RUNNING:
      _disp_agent.last_dispatch_at = check_time
  ```
  Or, at minimum, clear `last_dispatch_at` to None when an agent transitions to STOPPED/STOPPING, so a subsequent restart starts with a clean dispatch baseline.