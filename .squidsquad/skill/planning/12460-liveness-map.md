# #12460 cutover — harness liveness/reboot map (implementation reference)

Front-load for the #12271 slice-d cutover: PID-liveness → progress-based. All line refs `references/scripts/harness.py` unless noted. PM-locked strategy = **shadow/parallel validation FIRST** (compute both decisions, log divergence, confirm no false-pos/neg), THEN remove PID-liveness.

## The decision: `HarnessState.update_health()` lines 420–876
- **PID-liveness gate (THE line to shadow/replace):** line 455 `alive = boot_remote._is_process_alive(pid)` (pid = `agent.claude_pid`, line 451). Fallbacks: `.claude-pid` file via `reboot_agent._read_claude_pid` (457–466); legacy `health_check.check_agent_health` (468–482). These three derive `alive`.
- **Force-kill safety net (TEARDOWN, stays):** 484–535, `reboot_agent._kill_process(pid)` at 524 when alive & intent STOPPING/RESTARTING & >60s (FORCE_KILL_TIMEOUT_SECONDS).
- **Death-candidate vars (630–633):**
  ```python
  is_dead = agent.status in ("stopped","error","stalled")   # 610
  was_alive = prev_status == "running"
  should_reboot = agent.intent in (INTENT_RUNNING, INTENT_RESTARTING)
  fresh_death = is_dead and was_alive
  held = agent.status == "paused" and not alive
  death_candidate = (fresh_death or held) and should_reboot
  pause_reason = agent.active_pause(now) if death_candidate else None
  ```
- **Decision tree (635–815):** (1) explained-pause HOLD 635–653; (2) _NO_AUTO_REBOOT escape 654–666; (3) StopFailure backoff 667–705; (4) normal death 706–792 (graceful-vs-crash via last_session_end vs last_spawn_at; fast-death streak → reboot_blocked_until = now+min(30*2^over,1800), crash-looping). Crash-loop resume check 800–815.
- **Reboot trigger (828–875, outside lock):** `boot_remote.boot_agent(role)`; on success clears `agent.last_session_end = None` (862).
- **reboot_blocked_until:** checked 800–815; set 771 & 695; cleared 553–554 (survived FAST_DEATH_WINDOW → streak reset).

## Progress signals on AgentState (class 178–346, __slots__ 181–195)
- **last_activity_at / last_activity** (slice b #12443): set in `hook_activity` (`POST /hooks/activity`, 2383–2477) line 2446–2447; throttled disk write 30s (`_ACTIVITY_SAVE_THROTTLE_SECONDS`). NEVER cleared (monotonic). **NOT yet consumed by reboot decision** (2392 comment) ← this slice wires it in.
- **in_flight_until** (slice c): set 2459 `now+TOOL_CALL_MAX_SECONDS` on PreToolUse; cleared 2462 on Post(Tool)Use(Failure). Ceiling TOOL_CALL_MAX_SECONDS=900 (L109).
- **waiting_since**: set 2530 (hook_pause Notification); cleared 2460/2463. WAITING_MAX_SECONDS=1800 (L118).
- **compacting_since**: set 2532 (PreCompact); cleared 2534 (PostCompact). COMPACTING_MAX_SECONDS=300 (L112).
- **last_stop_failure** {cause,at}: set 2542–2544 (StopFailure); self-expires via STOP_FAILURE_RECENT_SECONDS=180 (L124). Backoff causes = {rate_limit,overloaded} (L123).
- **last_session_end** {reason,at} (slice a): set 2363 (hook_session_end 2313–2370); cleared on spawn (862/2035/2148).

## Pause-aware guard: `AgentState.active_pause(self, now)` 273–299
Returns "in-flight"|"compacting"|"waiting"|None. Called at 633. Critical (290–292):
```python
if (self.in_flight_until is not None and 0 < self.in_flight_until - now <= TOOL_CALL_MAX_SECONDS): return "in-flight"
```
Suppress-reboot block 635–653 (sets status="paused", clears claude_pid). `held` (631) keeps it re-evaluated each poll until ceiling elapses.

## PID teardown (STAYS) vs liveness (GOES)
- STAYS (teardown): `reboot_agent._kill_process` (reboot_agent.py 39–87) at update_health 524 + restart endpoint. `.claude-pid` file (thin_launcher.py descendant-walk #10101) as kill-handle.
- GOES (liveness): `boot_remote._is_process_alive(pid)` @455, `.claude-pid` fallback 457–466, health_check fallback 468–482.

## HARNESS-ARCH §15 / §15.6
- §15.1 locked "dead" = after dispatch, no activity heartbeat (relative to dispatched work) AND `active_pause()` None. Idle-with-no-dispatched-work is NOT monitored on a pure timer — liveness evaluated relative to nudge/assign dispatch. Each pause ceiling-bounded.
- Knobs: TOOL_CALL_MAX_SECONDS=900, COMPACTING_MAX=300, WAITING_MAX=1800, STOP_FAILURE_RECENT=180.
- §15.6 = pointer-only ("tracked in #12271"); "PID used only to terminate, never to determine liveness."

## Persistence
- to_dict 315–346; save_state 1036–1104 (atomic .tmp+replace, _lock); load_state 1106–1196 (safe defaults for missing keys; INTENT_RESTARTING→RUNNING on load 1152–1154).
- Hook endpoints: /hooks/session-end 2313–2370; /hooks/activity 2383–2477; /hooks/pause 2480–2549+.

## Shadow-phase plan (first commits, observational — no behavior change)
1. Add a pure helper `progress_liveness(agent, now)` → returns ("alive"|"dead", reason) from heartbeat+pause+sessionend, mirroring §15.1, WITHOUT touching the reboot path. Needs a dispatch-relative activity window (define ACTIVITY_WINDOW vs last dispatched nudge/assign — careful: idle agents legitimately silent). Open Q: what's "dispatched work" reference time on AgentState? (last_activity_at advances on cycle_post too). 
2. In update_health, AFTER computing PID `alive`, compute progress decision; `_log` divergence (PID says alive, progress says dead → candidate zombie; PID dead, progress alive → candidate false-reboot-avoided). DO NOT change `alive`/reboot yet.
3. Tests: divergence logging fires on constructed states; zombie repro (alive pid, last_activity_at stale, no pause) → progress=dead while PID=alive (the #10855 catch). Busy/paused → progress=alive.
4. LATER (after shadow data, separate commit/cycle): flip `alive` to progress-derived, demote PID to teardown-only, remove 455/457-482 from liveness. DS-review-per-change.
