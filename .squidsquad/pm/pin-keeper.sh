#!/usr/bin/env bash
# PM pin-keeper: maintains LOOP-mode pin (.harness-port=59999) on pinned agent
# clones so any reboot boots LOOP mode (stable) instead of event mode (#11586
# slow loop). Pairs with lock-watchdog. Temporary until #11586 fixed. Ops, not code.
PORT_FILES=(
  "/d/Dev/Dev/SquidSquad-2/.squidsquad/.harness-port"   # skill
  "/d/Dev/Dev/SquidSquad-3/.squidsquad/.harness-port"   # dm
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
