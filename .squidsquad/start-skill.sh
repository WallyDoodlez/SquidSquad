#!/bin/bash
cd "$(git rev-parse --show-toplevel)"

if [ -d .squidsquad ]; then
  V=$(grep -o '[0-9][0-9.]*[0-9]' .squidsquad/config.md 2>/dev/null | head -1)
  cat << LOGO

      ▗▄▖
     ▟█ █▙
    ▐█• •█▌
   ███████
   ▐█████▌
    ▐▌▐▌▐▌
  S Q U I D S Q U A D   v${V:-?}  —  skill

LOGO
fi

# Write role for statusline (not used for auto-boot — system prompt handles that)
echo "skill" > .squidsquad/.active-role

# Clear and initialize status bar state
rm -f .squidsquad/skill/current-state
echo "idle|Initializing..." > .squidsquad/skill/current-state

# Launch heartbeat in background
HB_INTERVAL=$(grep 'Heartbeat Interval Seconds' .squidsquad/config.md 2>/dev/null | grep -oE '[0-9]+')
HB_INTERVAL=${HB_INTERVAL:-10}
bash .squidsquad/heartbeat.sh "skill" "$HB_INTERVAL" &
HB_PID=$!
trap "kill $HB_PID 2>/dev/null" EXIT

claude --enable-auto-mode --append-system-prompt "SQUIDSQUAD_ROLE=skill" "start the loop"
