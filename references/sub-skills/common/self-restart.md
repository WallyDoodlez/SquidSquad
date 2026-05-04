<!-- sub-skill: self-restart -->
### Self-Restart (Context Pressure Only)

Agents can signal a restart only when their own context pressure exceeds the threshold. All other restart reasons (template changes, reboot requests) are handled by the harness via intent API (#4966).

**Context pressure restart flow**:
1. Step 1b detects context pressure exceeds threshold.
2. Checkpoint working state to `.squidsquad/[ROLE]/working-state.md`.
3. Complete the current cycle normally.
4. At cycle end, `cycle_post.py` checks context pressure from `cycle-input.json`. If exceeded, exits with code 42.
5. The harness detects the exit, sees intent=running, and respawns the agent.

**You do NOT**:
- Set `restart_needed` in cycle-output.json (deprecated).
- Write any sentinel files directly.
- Restart for template changes (handled by harness via `start_team.py --reboot`).
- Kill or manage other agents (harness handles this).
- Implement any restart loop logic (harness handles respawn).

Write `idle|` to `current-state` at cycle end so health monitoring works.
<!-- /sub-skill: self-restart -->
