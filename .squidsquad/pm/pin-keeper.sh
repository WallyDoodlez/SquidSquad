#!/usr/bin/env bash
# PM pin-keeper: maintains skill's .harness-port=59999 so any reboot boots LOOP mode
# (stable) instead of event mode (#11586 slow loop). Pairs with lock-watchdog.
# Temporary until #11586 (event-mode arming) is fixed. Ops, not code.
PORT_FILE="/d/Dev/Dev/SquidSquad-2/.squidsquad/.harness-port"
LOG="$HOME/.squidsquad-pin-keeper.log"
for n in $(seq 1 900); do   # ~7.5h at 30s
  cur=$(cat "$PORT_FILE" 2>/dev/null)
  if [ "$cur" != "59999" ]; then
    printf '59999' > "$PORT_FILE"
    echo "$(date '+%H:%M:%S') re-asserted 59999 (was '$cur')" >> "$LOG"
  fi
  sleep 30
done
