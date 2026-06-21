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
5. **You then halt — cease output and end your turn** — see "Cooperative Stop — Halt, Harness Terminates" below. You cannot terminate your own process; a best-effort `/quit` is fine but is not what restarts you (#13077).
6. The harness's **60-second force-kill net** (armed when intent flipped to `restarting`, recording `intent_set_at`) terminates your still-running process and, because intent is `restarting`, respawns you through the proper RESTARTING flow. That net is the **actual** terminating actor here — not a should-never-fire backstop — because an LLM agent cannot exit itself.

### Cooperative Stop — Halt, Harness Terminates

**After `cycle_post.py` exits with code 42** (the cooperative termination signal — the harness asked you to stop/restart, or `cycle_post` detected its own context pressure exceeded), **halt: start nothing new, cease output, end your turn.** A best-effort `/quit` is fine but does **not** terminate the claude process — an LLM agent can only stop emitting output, not execute a real `/quit` (#13077). The harness terminates your process and (for a restart) respawns you per its intent state machine.

- Do NOT continue working after a 42 exit — stop emitting output so the harness can terminate you on an idle process.
- Do NOT attempt to suppress, retry, or override the 42 exit — it is the canonical cooperative-termination **signal** (`cycle_post.py` emits it).
- The exit-42 conditions are owned by `cycle_post.py`: harness intent in `{stopping, restarting}` OR context-pressure exceeded.

For exit-42 / stop-requested / restart, the harness's **60-second force-kill net** (armed on the intent flip to `stopping`/`restarting`) is what **actually terminates** your process, because you cannot self-`/quit`. It is **expected to fire** — it is the mechanism, not a rare safety net. (It is slower than the deploy-halt path, which the harness force-kills immediately; accelerating exit-42/stop to an active force-kill is a **separate future decision, not yet done** — do not document them as instant.)

**You do NOT**:
- Set `restart_needed` in cycle-output.json (deprecated).
- Write any sentinel files directly.
- Restart for template changes (handled by harness via `start_team.py --reboot`).
- Kill or manage other agents (harness handles this).
- Implement any restart loop logic (harness handles respawn).

At the end of a **normal** cycle (no exit-42 imminent), write `idle|` to `current-state` so health monitoring works. Do NOT overwrite it on the restart path — `cycle_post.py` writes `restarting|…` itself when the 42-exit condition fires, and clobbering that would hide the transition from the operator and TUI.
<!-- /sub-skill: self-restart -->
