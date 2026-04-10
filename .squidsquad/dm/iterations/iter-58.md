# DM Iteration 58

- **Date**: 2026-04-10 17:01
- **Features Delivered**: #250 — Auto-restart wrapper (loop expiry, context pressure, crash recovery)
- **Version Bumped**: no (5/10)
- **Notes**: First full feature delivery (non-delivery:skip) in a while. README Key Features updated to reflect new auto-restart behavior. CHANGELOG entry prepared in Discussion for next version bump. Boot scripts wrap agents in while-loop with PID lock, exponential backoff, stop sentinel.
