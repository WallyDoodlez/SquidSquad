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

claude --dangerously-skip-permissions --system-prompt-file .squidsquad/skill/CLAUDE.md
