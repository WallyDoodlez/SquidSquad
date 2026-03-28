#!/bin/bash
cd "$(git rev-parse --show-toplevel)"

if [ -d .squidsquad ]; then
  V=$(grep -o '[0-9][0-9.]*[0-9]' .squidsquad/config.md 2>/dev/null | head -1)
  cat << LOGO

    ▗▄▄▄▄▖
   ▟██████▙
    ▐▌▀ ▀▐▌
  ▜██████▛▘
   ▐██████
    ▌▌▌▌▌▌
  S Q U I D S Q U A D   v${V:-?}  —  skill

LOGO
fi

INTERVAL=$(grep "Minutes" .squidsquad/config.md | grep -o '[0-9]*' | head -1)
INTERVAL=${INTERVAL:-10}

echo "[squidsquad] skill agent starting. loop interval: ${INTERVAL}min"
echo "[squidsquad] press Ctrl+C to stop"
echo ""

N=0
while true; do
  N=$((N + 1))
  echo "[squidsquad] ---- cycle $N started at $(date '+%H:%M:%S') ----"
  claude --dangerously-skip-permissions --verbose -p "Read .squidsquad/skill/CLAUDE.md for your instructions. Begin your Ralph Loop cycle now." 2>&1
  echo ""
  echo "[squidsquad] ---- cycle $N complete. sleeping ${INTERVAL}min ----"
  sleep $((INTERVAL * 60))
done
