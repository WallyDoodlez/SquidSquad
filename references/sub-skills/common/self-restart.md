---
slot: instructions
ordinal: 10
---

<!-- sub-skill: self-restart -->
### Self-Restart (Context Pressure Only)

Agents can signal a restart only when their own context pressure exceeds the threshold. All other restart reasons (template changes, reboot requests) are handled by the harness via intent API (#4966).

**Context pressure restart flow** (#4792 Phase 1):

1. Step 1b detects context pressure exceeds threshold.
2. Checkpoint working state to `.squidsquad/[ROLE]/working-state.md`.
3. Complete the current cycle normally.
4. At cycle end, `cycle_post.py` checks the `context_pressure` field of your `cycle-output.json` (falling back to `cycle-input.json` if you did not pass it through). If exceeded, it POSTs `/agents/[ROLE]/restart` to the harness so intent flips to `restarting` (recording `intent_set_at` for the 60s force-kill safety net), then exits with code 42.
5. **You then invoke `/quit`** — see "Graceful Stop — Self-Quit Protocol" below.
6. The harness observes the process exit and, because intent is `restarting`, respawns the agent through the proper RESTARTING flow.

### Graceful Stop — Self-Quit Protocol

**After `cycle_post.py` exits with code 42** (the cooperative termination signal — either the harness asked you to stop/restart, or `cycle_post` detected its own context pressure exceeded), immediately invoke the `/quit` slash command to terminate the claude session. The harness will then observe the process exit and either mark you stopped or respawn you per its intent state machine.

- Do NOT continue working after a 42 exit — the harness is waiting for you to terminate.
- Do NOT attempt to suppress, retry, or override the 42 exit — it is the canonical cooperative-termination signal.
- The exit-42 conditions are owned by `cycle_post.py`: harness intent in `{stopping, restarting}` OR context-pressure exceeded.

The harness has a **60-second force-kill safety net** that fires if you fail to invoke `/quit` within the cooperative window. The safety net guarantees that operator intent (stop or restart) eventually wins even if the agent hangs — but the cooperative path is the canonical one, and the safety net should never fire under normal operation.

**You do NOT**:
- Set `restart_needed` in cycle-output.json (deprecated).
- Write any sentinel files directly.
- Restart for template changes (handled by harness via `start_team.py --reboot`).
- Kill or manage other agents (harness handles this).
- Implement any restart loop logic (harness handles respawn).

At the end of a **normal** cycle (no exit-42 imminent), write `idle|` to `current-state` so health monitoring works. Do NOT overwrite it on the restart path — `cycle_post.py` writes `restarting|…` itself when the 42-exit condition fires, and clobbering that would hide the transition from the operator and TUI.
<!-- /sub-skill: self-restart -->
