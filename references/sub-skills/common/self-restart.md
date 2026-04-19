### Self-Restart (Watchdog-Managed)

Agent lifecycle is managed by the external **watchdog** (`references/scripts/watchdog.py`). Agents do **not** self-restart.

The watchdog handles:
- **Context pressure restarts**: Detects high context pressure and restarts the agent between cycles.
- **Template change restarts**: Detects when `.squidsquad/[ROLE]/CLAUDE.md` has been updated and restarts the agent to pick up new instructions.
- **Dead agent recovery**: Detects crashed/stalled agents and reboots them.

**Agent responsibilities** (what you still do):
- Checkpoint working state when context pressure is high (Step 1b).
- Write `idle|` to `current-state` at cycle end so the watchdog knows you finished.
- Continue working normally — the watchdog handles restarts externally.

**You do NOT**:
- Write `.restart` sentinel files.
- Check template mtimes for restart triggers.
- Implement any self-restart logic.
