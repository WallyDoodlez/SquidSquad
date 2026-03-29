#!/bin/bash
# SquidSquad Heartbeat — pushes lightweight orphan branch for agent health detection
# Usage: heartbeat.sh <role> [interval_seconds]
# Runs as background process, launched by boot scripts

ROLE="${1:?Usage: heartbeat.sh <role> [interval_seconds]}"
INTERVAL="${2:-10}"
BRANCH="heartbeat/${ROLE}"

# Cleanup on exit
cleanup() {
  exit 0
}
trap cleanup SIGTERM SIGINT EXIT

while true; do
  # Create a tree with a single timestamp file (no checkout needed)
  TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  BLOB=$(echo "$TIMESTAMP" | git hash-object -w --stdin 2>/dev/null) || { sleep "$INTERVAL"; continue; }
  TREE=$(printf "100644 blob %s\theartbeat\n" "$BLOB" | git mktree 2>/dev/null) || { sleep "$INTERVAL"; continue; }
  COMMIT=$(git commit-tree "$TREE" -m "heartbeat: ${ROLE} ${TIMESTAMP}" 2>/dev/null) || { sleep "$INTERVAL"; continue; }
  git push -f origin "${COMMIT}:refs/heads/${BRANCH}" 2>/dev/null || true

  sleep "$INTERVAL"
done
