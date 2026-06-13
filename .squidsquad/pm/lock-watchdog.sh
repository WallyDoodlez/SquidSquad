#!/usr/bin/env bash
# PM operational watchdog: clears STALE .claude/scheduled_tasks.lock (dead holder PID)
# across agent clones, preventing the exit-1 startup crash loop from recurring
# overnight until #11641 (durable spawn-path fix) lands. Ops stall-recovery, not code.
LOG="$HOME/.squidsquad-lock-watchdog.log"
CLONES="/d/Dev/Dev/SquidSquad-2 /d/Dev/Dev/SquidSquad-qa /d/Dev/Dev/SquidSquad-3 /d/Dev/Dev/SquidSquad"
for n in $(seq 1 480); do   # ~8h at 60s
  for c in $CLONES; do
    lk="$c/.claude/scheduled_tasks.lock"
    [ -f "$lk" ] || continue
    pid=$(python -c "import json,sys; print(json.load(open(r'$(cygpath -w "$lk")'))['pid'])" 2>/dev/null)
    [ -z "$pid" ] && continue
    alive=$(powershell.exe -NoProfile -Command "if(Get-Process -Id $pid -ErrorAction SilentlyContinue){'1'}else{'0'}" 2>/dev/null | tr -d '\r')
    if [ "$alive" = "0" ]; then
      cp "$lk" "$lk.stale-bak" 2>/dev/null
      rm -f "$lk" && echo "$(date '+%H:%M:%S') CLEARED stale lock in $c (dead pid $pid)" >> "$LOG"
    fi
  done
  sleep 60
done
echo "$(date '+%H:%M:%S') watchdog finished 8h run" >> "$LOG"
