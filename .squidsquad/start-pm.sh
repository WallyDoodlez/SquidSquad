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
  S Q U I D S Q U A D   v${V:-?}  —  PM / QA

LOGO
fi

# Write role for statusline (not used for auto-boot — system prompt handles that)
echo "pm" > .squidsquad/.active-role

# Clear and initialize status bar state
rm -f .squidsquad/pm/current-state
echo "idle|Initializing..." > .squidsquad/pm/current-state

claude --enable-auto-mode --append-system-prompt "SQUIDSQUAD_ROLE=pm" "start the loop"
