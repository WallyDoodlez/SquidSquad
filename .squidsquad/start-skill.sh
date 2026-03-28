#!/bin/bash
cd "$(git rev-parse --show-toplevel)"

INTERVAL=$(grep "Minutes" .squidsquad/config.md | grep -o '[0-9]*' | head -1)
INTERVAL=${INTERVAL:-10}

echo "[squidsquad] skill agent starting. loop interval: ${INTERVAL}min"
echo "[squidsquad] press Ctrl+C to stop"
echo ""

N=0
while true; do
  N=$((N + 1))
  echo "[squidsquad] ---- cycle $N started at $(date '+%H:%M:%S') ----"
  claude --permission-mode auto --enable-auto-mode -p "$(cat .squidsquad/skill/CLAUDE.md)"
  echo ""
  echo "[squidsquad] ---- cycle $N complete. sleeping ${INTERVAL}min ----"
  sleep $((INTERVAL * 60))
done
