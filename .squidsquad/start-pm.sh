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
  S Q U I D S Q U A D   v${V:-?}  —  PM / QA

LOGO
fi

# Write role for statusline (not used for auto-boot — that uses system prompt)
echo "pm" > .squidsquad/.active-role

claude --permission-mode auto --append-system-prompt "SQUIDSQUAD_ROLE=pm" "start the loop"
