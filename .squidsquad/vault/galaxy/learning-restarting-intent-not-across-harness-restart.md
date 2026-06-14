---
type: learning
tags: [harness, reboot, force-kill, intent, restart, gotcha]
created: 2026-06-14
updated: 2026-06-14
owner: skill-lead
status: active
confidence: high
source: observation
links: [learning-cycle-pre-preserves-code-wip, decision-reboot-kills-child]
---

# "Rebooting for no reason" had two distinct causes (#12244)

## Context

Operator reported agents "rebooting for no reason" — and, on closer look, a
*healthy working* agent getting killed and respawned repeatedly. RCA found two
independent causes, not one.

## Cause 1 — RESTARTING intent resurrected across a harness restart (the real killer)

The 60s force-kill safety net (`harness.py` `update_health`) kills a *live*
agent when `intent ∈ {STOPPING, RESTARTING}` and `intent_set_at` is >60s old.
`load_state` restored a saved RESTARTING intent + its stale timestamp as-is, so
an agent whose `claude.exe` outlived a harness restart got force-killed on the
**first** health poll (timestamp already >60s old), then auto-rebooted. Fixed by
resetting `RESTARTING→RUNNING` on `load_state` — RESTARTING is a transient
in-flight state owned by the harness session that issued it; it must not survive
a restart. STOPPING *is* preserved (an operator stop must survive a restart).

## Cause 2 — no respawn backoff on a fast-crashing agent

A Claude session/usage-limit exit-1 (or any fast crash) drove a tight respawn
loop, burning a fresh session per spawn. Note: thin_launcher's `Popen` does NOT
capture claude's stdout, so the "session limit" message is invisible to the
harness — message-parsing is not viable. Fixed with timing-based fast-death
backoff: N deaths within 60s of (re)spawn → exponential backoff (cap 30m) +
`status='crash-looping'` on /status.

## Implications for every role

- A reboot is no longer evidence of a stuck task by itself. Check whether the
  agent reaches `running` and whether commits advance — see
  [[learning-cycle-pre-preserves-code-wip]].
- `status='crash-looping'` on /status means the harness has paused respawns for
  that agent (repeated fast deaths — often a Claude session/usage limit). It
  resumes automatically after backoff; it is NOT a SquidSquad bug.
- A still-open hardening: `.claude-pid` can go stale/missing and mislead
  restart-time liveness detection — tracked in #12294.

## Changelog

- 2026-06-14 — Created by skill-lead. From #12244 P0+P2 (PR #12293).
