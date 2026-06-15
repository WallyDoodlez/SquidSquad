I've completed a thorough review of the diff, tracing the full `update_health` status machine, the `active_pause`/`stopfailure_backoff_due` helpers, the pause hook endpoints, and all 10 new tests. Here are my findings:

---

### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: 641 (and block 628–641)
- **Severity**: warning
- **Issue**: The pause-hold block sets `state_changed = True` unconditionally on **every** poll a held "paused" agent is re-evaluated, even when `agent.status` was already `"paused"` and all fields (`claude_pid`, `bootup_complete`) already hold the values being re-assigned.

```python
# Line 628-641 — note state_changed=True is OUTSIDE the if agent.status != "paused":
if death_candidate and pause_reason is not None:
    if agent.status != "paused":
        _log(...)
    agent.status = "paused"          # idempotent when already "paused"
    agent.claude_pid = None          # idempotent when already None
    agent.bootup_complete = False    # idempotent when already False
    state_changed = True             # ← ALWAYS true, even when nothing changed
```

- **Evidence**: The commit message claims this "mirrors the proven crash-looping hold/resume pattern." However, the crash-looping status preservation block (`elif agent.status in ("crash-looping", "paused"):`, lines 572–590) only sets `state_changed = True` when it **transitions** the agent to `"stopped"` (the STOPPING-intent path). For a RUNNING-intent crash-looping agent whose status is preserved (the normal case), it does **not** set `state_changed`. The pause-hold block deviates from the pattern it claims to mirror: it triggers `save_state()` (line 799–800) on every 5s health poll for every held paused agent, even when nothing in the state actually changed. While this is not a correctness bug (the state writes are semantically no-ops), it is unnecessary I/O and diverges from the proven pattern.

- **Suggested fix**: Move `state_changed = True` inside the `if agent.status != "paused":` block, so it only fires on the initial transition into `"paused"`. The status preservation block at line 572 already ensures `"paused"` is preserved across subsequent polls, so this block only needs to signal a change on the FIRST hold:

```python
if death_candidate and pause_reason is not None:
    if agent.status != "paused":
        _log(...)
        agent.status = "paused"
        agent.claude_pid = None
        agent.bootup_complete = False
        state_changed = True
```

This mirrors the crash-looping pattern: the status block preserves the hold silently; only the **transition** signals a change.

---

### Finding 2

- **File**: `references/scripts/harness.py`
- **Line**: 284 (in `active_pause`)
- **Severity**: error
- **Issue**: `active_pause` has no ceiling guard on `in_flight_until`, unlike the `compacting_since` and `waiting_since` branches which both enforce `0 <= now - <timestamp> < MAX_SECONDS`. The in-flight check is a bare `now < self.in_flight_until`.

```python
# Line 284 — no max-age ceiling:
if self.in_flight_until is not None and now < self.in_flight_until:
    return "in-flight"
# Line 286-288 — compacting HAS a max-age ceiling:
if (self.compacting_since is not None
        and 0 <= now - self.compacting_since < COMPACTING_MAX_SECONDS):
    return "compacting"
# Line 289-291 — waiting HAS a max-age ceiling:
if (self.waiting_since is not None
        and 0 <= now - self.waiting_since < WAITING_MAX_SECONDS):
    return "waiting"
```

- **Evidence**: The commit message explicitly states each pause signal is "bounded by its staleness ceiling (TOOL_CALL_MAX 900s etc.) with a '0<=age' clock-skew guard." The in-flight branch relies on an **implicit** ceiling: `in_flight_until` is set to `now + TOOL_CALL_MAX_SECONDS` (line 2429) and cleared by PostToolUse/PostToolUseFailure (line 2431). If the PostToolUse hook is never delivered (crash, network loss, hook bug), `in_flight_until` persists in the state file at the value `T + 900`. After a harness restart where the clock has moved, this stale value is still loaded (line 1165: `agent.in_flight_until = agent_data.get("in_flight_until")`). Since there is no explicit ceiling guard, a post-restart clock that is still `< T+900` (even if the real wall-clock elapsed time far exceeds 900s, e.g., NTP correction that moved the clock backward) would hold the reboot. The compacting/waiting branches explicitly guard against this with `0 <= now - timestamp < MAX`; the in-flight branch should have an equivalent guard.

Concretely: if `in_flight_until` was set at epoch 1000 (deadline = 1900), the harness restarts, the system clock says 500 (NTP step backward), then `now (500) < 1900` is True and the agent is held for 1400 more seconds — far exceeding the TOOL_CALL_MAX_SECONDS ceiling. A `0 <=` age guard would prevent this.

- **Suggested fix**: Add an explicit ceiling guard to the in-flight check:

```python
if (self.in_flight_until is not None
        and now < self.in_flight_until
        and 0 <= self.in_flight_until - now <= TOOL_CALL_MAX_SECONDS):
    return "in-flight"
```

This ensures that even if `in_flight_until` is corrupted, stale, or subject to clock skew, the hold cannot exceed TOOL_CALL_MAX_SECONDS (900s). The `0 <= self.in_flight_until - now` sub-expression is the clock-skew guard (deadline must be in the future but not by more than the ceiling).

---

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: 655–673 (StopFailure backoff block)
- **Severity**: error
- **Issue**: The StopFailure backoff path (clause 3) increments `consecutive_fast_deaths` and computes the backoff timer identically regardless of whether the StopFailure cause is `"rate_limit"` or `"overloaded"`. However, the `stopfailure_backoff_due` method (line 294–306) already validates the cause is in `STOP_FAILURE_BACKOFF_CAUSES = frozenset({"rate_limit", "overloaded"})`. The problem is that the StopFailure path does **not** check the `graceful` exit flag — unlike clause 4 (the general crash-loop path, which respects the #12418 graceful-exit guard at lines 707–710 and skips the fast-death increment for graceful exits at lines 711–728).

This means: an agent that exits **gracefully** (sends SessionEnd) but happens to have a recent `rate_limit` StopFailure (perhaps from a start attempt that hit a rate limit 30 seconds ago) will have `consecutive_fast_deaths` incremented and enter crash-loop backoff, even though the death itself was graceful and should not count as a crash.

- **Evidence**: The commit message says AC3d handles "a death coinciding with a recent rate_limit/overloaded StopFailure" and "counts it as a fast death so repeated throttles escalate the wait." This is intentional for the throttle case. However, consider: the agent exits gracefully (cooperative exit via SessionEnd, no crash), but 10 seconds earlier an operator's `/start` attempt on a different agent hit the same API key's rate limit and recorded a `last_stop_failure` on this agent. The graceful death now gets counted as a crash-loop fast death. While the throttle backoff is indeed desirable, **incrementing the crash streak** for a graceful exit contradicts the #12418 contract (AC4: "graceful exit is not a crash — it must not accumulate the #12244 crash-loop streak"). The StopFailure backoff timer itself is correct; it's the `consecutive_fast_deaths += 1` that is wrong for graceful exits.

- **Suggested fix**: Check the graceful flag before incrementing `consecutive_fast_deaths` in the StopFailure path. The backoff should still apply (to avoid re-hitting the rate limit), but it should not accumulate the crash streak if the exit was graceful:

```python
elif death_candidate and agent.stopfailure_backoff_due(now):
    # … graceful check (same logic as clause 4) …
    se = agent.last_session_end
    se_at = (se.get("at") or 0) if isinstance(se, dict) else 0
    graceful = bool(
        agent.last_spawn_at is not None
        and se_at >= agent.last_spawn_at
    )
    if not graceful:
        agent.consecutive_fast_deaths += 1
    # … rest: compute backoff, set crash-looping, etc. …
```

This preserves the throttle-avoidance intent (still sets `crash-looping` + `reboot_blocked_until`) while respecting #12418's contract that graceful exits don't count toward the crash streak. If a graceful exit hits the rate limit repeatedly, the operator needs to address the rate limit — not have the crash-loop streak silently accumulate.

---

NO_FINDINGS for: the elif chain mutual exclusivity (verified correct — `death_candidate` requires `fresh_death` or `held`, neither of which can be True when status is `"crash-looping"`); the operator-stop-wins path (verified via the status block at line 585–590 + STOPPING fulfillment at line 791–796, tested by `test_operator_stop_wins_over_pause`); and the lock safety (all `active_pause` fields are written under `state._lock` at line 2493, matching the `update_health` lock at line 429).