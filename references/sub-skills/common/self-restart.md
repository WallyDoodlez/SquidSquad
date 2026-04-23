<!-- sub-skill: self-restart -->
### Self-Restart (Context Pressure Only)

Agents can signal a restart only when their own context pressure exceeds the threshold. All other restart reasons (template changes, reboot requests) are handled externally by PM → DM via `reboot_agent.py`.

**Context pressure restart flow**:
1. Step 1b detects context pressure exceeds threshold.
2. Checkpoint working state to `.squidsquad/[ROLE]/working-state.md`.
3. Complete the current cycle normally.
4. At cycle end, write the restart reason to `.squidsquad/[ROLE]/.restart`:
   ```bash
   echo "context pressure at [X]%" > .squidsquad/[ROLE]/.restart
   ```
5. The wrapper detects the sentinel on exit, deletes it, and respawns.

**You do NOT**:
- Restart for template changes (DM handles post-ship reboots).
- Kill or manage other agents (PM coordinates, DM executes).
- Implement any restart loop logic (wrapper handles one retry on crash).

Write `idle|` to `current-state` at cycle end so health monitoring works.
<!-- /sub-skill: self-restart -->
