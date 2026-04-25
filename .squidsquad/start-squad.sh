#!/bin/bash
# Start all configured SquidSquad agents.
# Calls boot_remote.py --all which handles liveness detection,
# .stop sentinel checks, clone path resolution, and PID singleton enforcement.
cd "$(git rev-parse --show-toplevel)"

echo "🦑 Starting SquidSquad agents..."
python references/scripts/boot_remote.py --all

exit $?
