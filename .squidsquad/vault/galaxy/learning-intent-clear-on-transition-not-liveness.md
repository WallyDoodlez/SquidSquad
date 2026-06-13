---
type: learning
tags: [harness, lifecycle, state-machine, concurrency, polling]
created: 2026-06-12
updated: 2026-06-12
owner: skill
status: active
confidence: high
source: observation
links: [squidsquad]
---

## Context

#11538: `POST /agents/{role}/restart` returned success but never restarted a wedged/non-cycling agent. The restart endpoint correctly set `intent=RESTARTING` + `intent_set_at`, yet within 5s the harness health poller (`HEALTH_POLL_INTERVAL=5s`) reset it back to `RUNNING`/`None`. That also disarmed the 60s force-kill safety net (scoped to STOPPING/RESTARTING), so the wedged agent could be neither restarted nor force-killed. The bug was a one-line missing guard.

## Content

**In a polling health/reconcile loop, clear an operator-set intent on a TRANSITION SIGNAL, not on a steady-state liveness condition.** The buggy code reset `RESTARTING→RUNNING` whenever the agent's PID was merely *alive* — but "alive" is the steady state *before* a restart completes, so the very next poll (5s later) undid the operator's intent before anything could act on it. The correct signal is `pid_changed` (a genuinely NEW PID = the old process died and a replacement booted) — proof the restart actually happened. The sibling STOPPING branch already did this; RESTARTING was missing the guard.

Two compounding failure modes to watch for whenever a poll mutates intent:
1. **Self-reversal**: a poll that clears intent on a condition true *before* the intended action runs will erase the intent every interval — the action never fires. Symptom: operator sees the intent flip back to default within one poll interval, and `intent_set_at` reads `None`.
2. **Disarmed safety net**: any timeout/safety mechanism scoped to that intent (here, the 60s force-kill) silently never engages once the intent is reset, because its guard no longer matches.

Corollary: a force-kill / timeout net keyed on a wall-clock `*_set_at` must also skip when a NEW process is detected (`pid_changed`) — the stale timestamp belongs to the *old* process; killing the freshly-booted replacement for it is wrong.

**Test lesson**: a single-poll unit test that pre-sets `intent_set_at` far in the past can mask this class of bug (the timeout fires in that artificial poll regardless). The distinguishing test is "same PID alive, intent JUST set → intent must NOT reset this poll." Verify a regression test actually fails against the pre-fix code (`git stash` the fix, run) before trusting it.
