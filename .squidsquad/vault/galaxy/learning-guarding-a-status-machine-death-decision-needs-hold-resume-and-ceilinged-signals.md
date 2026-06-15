---
name: learning-guarding-a-status-machine-death-decision-needs-hold-resume-and-ceilinged-signals
description: To guard a one-shot death/reboot decision inside a status machine (where the trigger is a running→dead EDGE, not a level), you must mirror the existing hold/resume pattern — a dedicated holding status that the status-update block PRESERVES (doesn't relabel) plus a re-evaluation branch — because suppressing the edge once means it never re-fires; and any self-reported "I'm paused, don't kill me" signal needs BOTH a staleness ceiling AND a clock-skew guard so a never-cleared/future-stamped flag can't mask a genuine death forever
metadata:
  type: learning
type: learning
tags: [learning, harness, liveness, reboot, state-machine, 12458, 12271, 12244, self-hosting]
created: 2026-06-15
updated: 2026-06-15
owner: skill
status: active
confidence: high
source: observation
links: [learning-single-emit-wake-nudge-needs-bounded-reemit-and-must-bypass-time-filter, learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker, learning-claude-code-http-hooks-block-only-command-hooks-async]
---

# Guarding a status-machine death decision: hold/resume mirroring + ceilinged, skew-guarded signals

**Built (#12458, #12271 slice c):** a pause-aware guard on the harness reboot decision — a dead-PID agent is held instead of rebooted while a hook explains the silence (mid-tool-call / waiting / compacting / rate-limited). Two non-obvious traps, both surfaced by careful design + DS review.

**1. The death trigger is an EDGE, not a level — so suppressing it once kills it forever.** `update_health`'s reboot fires on `is_dead and was_alive` where `was_alive = prev_status == "running"`. That's a one-shot at the running→dead *transition*: the very next poll `prev_status` is no longer "running", so the branch never re-fires. If you intercept and suppress that one firing, the agent is stuck-not-rebooted permanently. The existing #12244 crash-loop backoff already solved this exact shape and is the template to MIRROR, not reinvent:
- A dedicated holding status (`"crash-looping"`, and now `"paused"`) that the status-update block **explicitly preserves** — i.e. it must be added to the "don't relabel to unknown/stalled" branch, or the machine silently overwrites it next poll.
- The holding status is NOT in the `is_dead` set, so the edge-triggered branch stays dormant.
- A **dedicated re-evaluation branch** (`elif status == "paused" and not alive ...`) that re-checks the condition each poll and releases (reboots) when it clears. Without this branch the hold is a black hole.
- Model the death candidate as `(fresh_death OR still-held)` so the same decision logic serves both the first transition and every held re-evaluation — factor it once, don't duplicate.

**2. Any self-reported "don't kill me" signal needs a staleness ceiling AND a clock-skew guard.** A pause flag the agent's own hooks set (in-flight deadline, compacting-since, waiting-since) is adversarial-input in the same sense as [[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]]: if the clearing hook never arrives (crash mid-tool-call, lost POST), the flag persists and would suppress reboot forever. Fixes:
- **Ceiling:** bound each hold by the longest LEGITIMATE duration of that state (tool_call_max, compact_max, wait_max). Past the ceiling the flag is stale → ignored → normal death path resumes. This is the load-bearing AC ("past the ceiling the agent is wedged").
- **Clock-skew guard:** express it as `0 <= age < MAX` (or for a future deadline, `0 < deadline - now <= MAX`). The lower bound rejects a future-stamped flag (NTP step backward, corrupt persisted state) that would otherwise read as an indefinite pause. DS review caught that the in-flight branch had only `now < deadline` while the others had the `0 <=` guard — an inconsistency that's exactly the indefinite-mask hole.
- **Preserve the no-regression invariant explicitly:** the genuine death (no pause signal) must reboot EXACTLY as before — `active_pause()` returns None immediately, so the guard is a no-op on that path. Test it directly AND keep the prior backoff suite green.

**Cross-cutting:** when a new backoff path coincides with an existing classification (here: a throttle StopFailure that's also a *graceful* exit), re-apply the existing contract ([[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]]: a graceful exit must not accumulate the crash streak). Back off (don't re-hit the limit) WITHOUT incrementing the streak. DS review caught this interaction too.

**How to apply:** before editing a status/liveness state machine, find the existing "hold then resume" precedent and mirror its three parts (holding status + preservation + resume branch); never suppress an edge-triggered decision without a re-trigger path. Give every self-reported suppression signal a ceiling + a `0 <=` skew guard. Make the high-blast-radius reboot-decision change at LOW context with mandatory per-change DS review — it caught two real errors here that the forward tests missed.
