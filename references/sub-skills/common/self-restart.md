<!-- sub-skill: self-restart -->
### Self-Restart (Context Pressure Only)

Agents can signal a restart only when their own context pressure exceeds the threshold. All other restart reasons (template changes, reboot requests) are handled externally via `start_team.py --reboot`.

**Context pressure restart flow**:
1. Step 1b detects context pressure exceeds threshold.
2. Checkpoint working state to `.squidsquad/[ROLE]/working-state.md`.
3. Complete the current cycle normally.
4. At cycle end, `cycle_post.py` reads the context pressure from `cycle-input.json` and writes `.squidsquad/[ROLE]/.stop-after-cycle` mechanically when pressure exceeds threshold. Agents do not need to set `restart_needed` — the mechanical layer detects and acts.
5. The wrapper detects the sentinel on exit, deletes it, and respawns.

**You do NOT**:
- Set `restart_needed` in cycle-output.json (deprecated — `cycle_post.py` detects context pressure mechanically).
- Write `.stop-after-cycle` directly — `cycle_post.py` handles this mechanically.
- Restart for template changes (handled externally via `start_team.py --reboot`).
- Kill or manage other agents (human or `start_team.py` handles this).
- Implement any restart loop logic (wrapper handles respawn).

Write `idle|` to `current-state` at cycle end so health monitoring works.
<!-- /sub-skill: self-restart -->
