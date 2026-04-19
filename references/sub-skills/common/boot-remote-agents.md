### Step — Boot Remote Agents (Watchdog-Managed)

Agent booting is now handled by the external **watchdog** (`references/scripts/watchdog.py`). No agent needs to run boot checks.

The watchdog:
1. Monitors all agent health every ~30 seconds.
2. Boots dead/stalled agents automatically.
3. Handles rate limiting and cooldown.

This step is a no-op — skip it entirely.
