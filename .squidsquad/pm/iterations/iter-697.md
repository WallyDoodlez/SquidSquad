# Iteration 697 — cycle 2344 (overnight stabilization)

**When**: 2026-06-13 02:25
**Mode**: inline (operator-directed, then asleep — "resolve reboot + team in event mode")
**Type**: incident resolution + overnight handoff

## Delivered
1. **Reboot crash-loop RESOLVED** — true cause = stale `.claude/scheduled_tasks.lock` (dead holder PID) → claude exit-1 at startup (no transcript) → harness #4949 reboots → lock persists across reboots → loop. Cleared on skill + qa clones (backups: *.stale-bak). Confirmed by repro (skill stable 2+ min after clear vs exit-1 every ~60-80s).
2. **Crash-loop protected overnight** — operational lock-watchdog (`.squidsquad/pm/lock-watchdog.sh`, bg task bsj1gq479): clears stale locks across all clones every 60s for ~8h. Log: `~/.squidsquad-lock-watchdog.log`. Ops stall-recovery, not a code change.
3. **QA wrong-realm FIXED** — registered `qa → ../SquidSquad-qa` in `.local-config` (gitignored, persists locally). QA now runs in its OWN clone (pid 40328), no longer clobbering PM clone. `_get_clone_path('qa')` verified → D:\Dev\Dev\SquidSquad-qa.

## Partial / honest
- **Event mode**: DM = true event mode (event_poll armed). skill = boots event mode but never arms Monitor/event_poll → INERT (#10855/#11586 agent-side bug, not externally fixable). qa = loop mode (stable, cycles).
- Probe is contention-sensitive (5s curl times out under harness load → loop fallback); my own status-polling during boot windows contributed. Stopped thrashing.
- Full event mode needs the worker to fix its own arming — chicken/egg since skill is the broken one.

## Corrections logged this session
- #11601 (event_poll None→7373) was a SEPARATE latent bug, NOT the reboot cause (corrected on #11612). Still legitimately merged (PR #11639).
- Earlier "skill idle" / "second-cause context-pressure" reads were wrong; operator's exit-1 evidence cracked the real cause.

## Issues
- #11641 (role:skill) — durable: clear stale lock on spawn. FILED.
- #11640 (role:skill) — no-fallback clone resolution (fail, don't boot REPO_ROOT). FILED.
- #11612, #11601 CLOSED.
- Won't progress while skill inert — morning operator call on event-mode-inert (#11586).

## State at handoff
- All 4 agents running, pids stable over 40s, NONE crash-looping. Watchdog active.
- QA artifacts (QA-RESULTS-11538, TEST-PLAN-11538, iter-134) left untouched in PM clone (QA's deliverables from wrong-realm period; QA owns from own clone now).
