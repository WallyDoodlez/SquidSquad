#!/bin/bash
cd "$(git rev-parse --show-toplevel)"

# Parse --name flag (optional override for agent alias)
AGENT_NAME=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --name) AGENT_NAME="$2"; shift 2 ;;
    *) shift ;;
  esac
done

# Read alias from config if no --name override
if [ -z "$AGENT_NAME" ]; then
  AGENT_NAME=$(python references/scripts/config.py alias skill 2>/dev/null || echo "squidsquad-skill")
fi

if [ -d .squidsquad ]; then
  V=$(grep -o '[0-9][0-9.]*[0-9]' .squidsquad/config.md 2>/dev/null | head -1)
  cat << LOGO

      ▗▄▖
     ▟█ █▙
    ▐█• •█▌
   ███████
   ▐█████▌
    ▐▌▐▌▐▌
  S Q U I D S Q U A D   v${V:-?}  —  ${AGENT_NAME}

LOGO
fi

# Inject permissions from template into settings.json
bash .squidsquad/inject-permissions.sh

# Write role for statusline (not used for auto-boot — system prompt handles that)
echo "skill" > .squidsquad/.active-role

# Clear and initialize status bar state
rm -f .squidsquad/skill/current-state
echo "idle|Initializing..." > .squidsquad/skill/current-state

claude --dangerously-skip-permissions --session-name "$AGENT_NAME" --append-system-prompt "SQUIDSQUAD_ROLE=skill" "Skill dev - start the loop"
