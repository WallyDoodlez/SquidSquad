#!/usr/bin/env bash
# PM pin-keeper: maintains LOOP-mode pin (.harness-port=59999) on agent clones so
# any reboot boots LOOP mode (functional) instead of event mode (INERT — #10855).
# Reboot loop itself is fixed (#11587+#11641 on main); this only dodges the inert
# event-mode state. Temporary until #10855 (inert boot) fixed. Ops, not code.
PORT_FILES=(
  "/d/Dev/Dev/SquidSquad-2/.squidsquad/.harness-port"    # skill
  "/d/Dev/Dev/SquidSquad-3/.squidsquad/.harness-port"    # dm
  "/d/Dev/Dev/SquidSquad-qa/.squidsquad/.harness-port"   # qa
)
LOG="$HOME/.squidsquad-pin-keeper.log"
for n in $(seq 1 1440); do   # ~12h at 30s
  for PORT_FILE in "${PORT_FILES[@]}"; do
    cur=$(cat "$PORT_FILE" 2>/dev/null)
    if [ "$cur" != "59999" ]; then
      printf '59999' > "$PORT_FILE"
      echo "$(date '+%H:%M:%S') re-asserted 59999 in $PORT_FILE (was '$cur')" >> "$LOG"
    fi
  done
  sleep 30
done
