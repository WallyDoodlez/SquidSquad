---
name: learning-graceful-restart-grace-timer-on-wedged-agent
description: Harness POST /agents/<role>/restart on a WEDGED idle event-mode agent isn't immediate — the agent never hits a cooperative-exit boundary, so the harness force-kills only after its grace timer (~2 min); flips intent=restarting + bootup=False but keeps the same pid until then. Wait for the new pid before escalating to OS-kill.
metadata:
  type: learning
type: learning
tags: [pm-judgment, pipeline-sentinel, lifecycle, harness, event-mode, stall-recovery]
created: 2026-06-18
updated: 2026-06-18
owner: pm
status: active
confidence: high
source: observation
links: [learning-stall-vs-deepwork-before-nudging, feedback_manual_agents, feedback_harness_sole_lifecycle, learning-restarting-intent-not-across-harness-restart]
---

# Graceful restart of a wedged idle agent waits for the harness grace timer (~2 min)

## Context

2026-06-18. skill was a CONFIRMED stall (inverse of [[learning-stall-vs-deepwork-before-nudging]] — all signals flat): alive pid, but last_activity 192m, 50 events backlogged past its cursor undrained, no commits. Its Monitor/wake path was wedged (the exact idle-stall #12506 fixes). It held critical-path #12506 in-progress (AC11 fix, compose-consumed code = skill domain, PM can't do it) and would not self-resume.

I requested `POST /agents/skill/restart`. Response was `{"success":true,"immediate":false,"message":"agent will exit after current cycle and reboot"}`. For ~2 min: `intent` flipped to `restarting`, `bootup_complete`→False, but the **pid stayed the same** — a wedged agent at Monitor idle-wait never reaches a cycle boundary to honor the cooperative exit. I briefly chased a `force:true` flag (not honored — endpoint is always graceful) before realizing the harness's own force-kill grace timer is what completes it. ~2 min in, skill respawned with a **new pid** and `intent=running`; on boot its `work_queue()` resumed #12506 (the boot backstop, independent of any wake event).

## The lesson

The graceful restart is reliable but **not instant** for a wedged/idle agent. Same-pid + intent=restarting for a minute or two is the EXPECTED in-between state, not a failed restart. The harness force-kills on its grace timer; the signal it worked is a **new pid**, not an immediate one.

## Refinement (2026-06-21) — the restart is INSTANT when current-state reads "idle"

The endpoint branches on the agent's `current-state` marker file: `immediate = current_state.startswith("idle")` (harness.py #8689). So there are TWO recovery speeds, not one:

- **current-state = "idle"** → endpoint returns `immediate:true` + `killed_pid:<old>` and kills the PID **right away**; new pid + `intent=running` in seconds (~6s observed). The ~2-min grace timer does NOT apply.
- **current-state ≠ "idle"** (working/inline/etc.) → graceful queued path, `immediate:false`, same-pid for ~2 min until the force-kill grace timer fires (the original lesson below).

**Stale-marker wrinkle (#12854):** the marker can LIE. 2026-06-21 qa was wedged at `intent=deploying` (blocked on an `AskUserQuestion` modal, never honored the deploy-signal, PID-alive 54 min, no auto-reboot — the #12271 gap), yet its `current-state` still read a stale `idle|`. That staleness routed the restart down the fast immediate-kill path — recovery in ~6s (`POST /agents/qa/restart` → `immediate:true, killed_pid:30604` → new pid 41892, `intent=running`). So a stale "idle" marker can *accelerate* recovery here, even though it's a defect elsewhere.

## How to apply

PM stall recovery, after confirming a real stall (flat liveness per [[learning-stall-vs-deepwork-before-nudging]]):

1. `POST http://127.0.0.1:7373/agents/<role>/restart`. Response tells you the path: `immediate:true` (PID killed now) vs `immediate:false` (graceful, ~2-min grace timer). Both are valid — driven by the `current-state` marker, not by failure.
2. **Re-poll `/status`.** Immediate path → expect a new `claude_pid` within seconds. Graceful path → wait ~2 min. Either way success = new `claude_pid` + `intent=running`. Don't re-request or chase a force flag in the gap — it's a no-op; the grace timer owns the kill on the graceful path.
   - **`boot_remote.py` is NOT the tool here** — it only spawns *dead* PIDs (singleton guard skips a live-but-wedged process). For wedged-ALIVE recovery use `POST /agents/<role>/restart`.
3. Only if the pid is STILL unchanged well past the grace window (~3-5 min) → escalate to OS force-kill of the agent's terminal tree (`taskkill /F /T` on terminal_pid, per [[decision-reboot-kills-child]] / orphan-claude hazard), letting auto-reboot respawn.
4. Confirm recovery by *liveness of the new pid* (last_activity ticking) + the agent picking its in-progress item back up — not just by the respawn.

*Open watch:* that graceful-restart can't promptly evict a wedged idle agent is a harness liveness gap (relates to #12271 redesign / [[feedback_harness_sole_lifecycle]]). Note, not yet filed — watch for recurrence as a pattern.

## Changelog

- 2026-06-18 — Created by pm-lead. From restarting wedged skill (pid 51776→23616) to unblock critical-path #12506.
- 2026-06-18 — Created by pm-lead. From restarting wedged skill (pid 51776→23616) to unblock critical-path #12506.
- 2026-06-21 — Refined by pm-lead. Added the `immediate:true` (current-state="idle") fast path vs the graceful ~2-min path, the #12854 stale-marker wrinkle, and the boot_remote-won't-work-on-wedged-alive note. From recovering wedged qa (pid 30604→41892, stuck intent=deploying 54 min; corroborated on #12271).
