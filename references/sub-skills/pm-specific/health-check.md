### Step 7 — Agent Health Check (Watchdog-Managed)

Agent health monitoring is now handled by the external **watchdog** (`references/scripts/watchdog.py`). PM no longer runs health checks.

The watchdog:
1. Checks all agent health every ~30 seconds using `health_check.py`.
2. Boots dead/stalled agents via `boot_remote.py`.
3. Handles context pressure and template change restarts.
4. Logs all actions to `.squidsquad/watchdog-log.txt`.

This step is a no-op — skip it entirely.
