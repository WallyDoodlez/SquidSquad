# Working State

- **Task**: cycle 2335 (inline) — quiet hold; #11538 fixed by skill → pending-test; awaiting operator on R2 + event-mode
- **Status**: pipeline healthy; 2 threads await operator (R2 design Qs, event-mode approach)
- **Last Processed Event ID**: 3e50e129c8e74594
- **Quiet cycles**: 0

## Event-mode investigation (operator goal: squad → event mode)

- **"2 skill agents" = NOT real** — Claude desktop app processes (WindowsApps Electron, --type). Named squidsquad agents: 1 each (pm/qa/dm/skill).
- **DM "restart into event mode"**: harness restart endpoint failed again (#11538). Force-killed DM 46736 → harness auto-respawned (boot_agent) → new PID 45212, clean. BUT landed **loop mode** (ran cycle 412, no event_poll). DM clone HAS #11512 fix → not a stale-launcher issue.
- **Root finding**: event_poll is spawned by the AGENT arming Monitor (event mode), NOT by boot_agent (boot_remote has no event_poll spawn). Reboot/respawn → loop mode. Only **qa** is event-mode — reached via **in-session switch** (commit 1ec4c89d: killed /loop cron, armed Monitor on operator request), NOT a reboot.
- **Implication**: start.sh reboot likely WON'T reach event mode (same boot_agent path). Only in-session switch works today; doesn't scale.
- **Filed #11586** (high, skill): fresh-boot→event-mode path broken; +doc/impl drift (HARNESS-ARCH §7.2 says harness spawns event_poll, impl has agent-via-Monitor). Cluster with #11538/#11512.

## Open threads (operator)

1. **R2 #11537 dep-provisioning** (status:planning) — research done (RESEARCH-INSTALLER-DEPROV-11537.md). 3 design Qs pending operator: (Q1) provision at install-time vs start.sh vs both; (Q2) confirm claude/gh-auth stay instruct; (Q3) scope system-tools+pkgs vs pkgs-only. PM recs: install-time primary / yes / full-scope. Then write section (own branch) + file impl to skill.
2. **Event mode**: how to proceed — in-session-switch each agent (manual, works) vs wait for #11586 fix. Operator's call.

## Pipeline (clean)

- pending-ship empty; pending-test #10855 (QA). DM cycling (loop, cycle 412). All agents 1-each, healthy.

## Incident follow-ups (this session)
- #11538 (harness restart ineffective), #11586 (event-mode not reached on boot), #11511 (merge-flap), #10540 (batch-drain), #11570 (#11053 Phase 2), #11519 (clones deadwood, shipped).

## Context
healthy.
