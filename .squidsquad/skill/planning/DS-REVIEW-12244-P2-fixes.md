I have thoroughly traced all code paths. Here is my analysis:

## Finding 1: Crash-looping + stop wedge

**Correctness verified.** The old code at `elif agent.status not in ("starting", "crash-looping"):` excluded crash-looping agents from the status-update block entirely. A crash-looping agent with intent STOPPING would:
- Skip the status block (status stays "crash-looping")
- `is_dead = False` ("crash-looping" ∉ {"stopped","error","stalled"})
- `should_reboot = False` (STOPPING ∉ {RUNNING, RESTARTING}) → resume branch doesn't fire
- `if is_dead and intent==STOPPING:` → doesn't fire (is_dead is False)
- **Wedged forever**

The fix splits `agent.status not in ("starting", "crash-looping")` into two elif branches. The new `elif agent.status == "crash-looping":` block sets status to "stopped" + clears `reboot_blocked_until` when intent is STOPPING/STOPPED. Then `is_dead` becomes True, and the STOPPING-fulfillment block at line 585 fires (intent→STOPPED, intent_set_at→None, claude_pid→None). **Wedge resolved.**

**No regression for RUNNING/RESTARTING crash-loopers.** When intent is RUNNING/RESTARTING, the new crash-looping elif block enters but the inner `if agent.intent in (STOPPING, STOPPED):` is False → nothing happens. Status stays "crash-looping", the resume branch at line 567 still fires when backoff elapses. Behavior is identical to before.

**Edge case — INTENT_STOPPED:** If intent is already STOPPED (not STOPPING), the crash-looping block sets status to "stopped", but the fulfillment block at line 585 only matches INTENT_STOPPING. The agent ends with status="stopped" + intent=STOPPED — which is the correct terminal state. `intent_set_at` may remain non-None, but that field only matters for the force-kill safety net (which requires intent STOPPING or RESTARTING, line 393), so it's harmless.

## Finding 2: last_spawn_at gate consistency

**Correctness verified.** All four spawn paths now follow the same pattern:

| Path | Line | Gate | terminal_pid access |
|------|------|------|---------------------|
| Auto-start | 1513 | `result["success"]` | `.get("terminal_pid")` |
| POST start | 1758 | `result["success"]` | `.get("terminal_pid")` |
| POST restart | 1869 | `result["success"]` | `.get("terminal_pid")` |
| Auto-reboot (was) | 613 (old) | `success AND terminal_pid` | `["terminal_pid"]` |
| Auto-reboot (now) | 613 (new) | `result["success"]` | `.get("terminal_pid")` |

The auto-reboot path now matches. The `.get("terminal_pid")` change is safe — `terminal_pid` is always present when `_spawn_terminal` succeeds (returns `proc.pid`), and `terminal_pid` is only stored metadata (terminal window PID, line 186), never used in health-check logic.

**No regression.** In the normal path (spawn succeeds), `boot_agent` always returns `terminal_pid` when `success=True` and `action="spawn"` (lines 633-637 of `boot_remote.py`). The boolean gate change is functionally identical for the existing success path; it only differs in hypothetical cases where `terminal_pid` might be `None` or `0` on success, and there the new code is strictly more correct.

## Test verification

The new test `test_crash_looping_agent_can_still_be_stopped` (line 785) correctly:
1. Creates a crash-looping agent with `reboot_blocked_until` in the future and `claude_pid=None` (not alive)
2. Sets intent to STOPPING  
3. Runs `update_health` and asserts no boot was attempted
4. Verifies the terminal state: intent=STOPPED, status="stopped", reboot_blocked_until=None

This directly validates the wedged→unblocked transition.

NO_FINDINGS