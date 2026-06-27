---
name: learning-activity-liveness-redispatch-must-not-reset-grace
description: when liveness is "did the consumer act on dispatched work within a grace window" (not PID existence), a RE-dispatch of still-unacted work must NOT reset the grace clock — else a wedged consumer whose re-nudge cadence <= the grace window is never detected dead; advance the dispatch reference only when the consumer caught up (acted since the last dispatch)
metadata:
  type: learning
type: learning
tags: [learning, harness, liveness, progress-based, zombie, 12460, 12271, deepseek, distributed-systems]
created: 2026-06-15
owner: skill
status: active
confidence: high
source: observation
links: [learning-shell-out-provisioning-has-three-sharp-edges]
updated: 2026-06-15
---

# Activity-based liveness: a re-dispatch of unacted work must not reset the grace

**Observed (#12460 / #12271 slice d — progress-based agent liveness).** Replacing PID-existence liveness with "the consumer emitted an activity heartbeat within a grace window after work was dispatched to it" needs a **dispatch reference** (when was work last dispatched) to compare the heartbeat against — otherwise a legitimately idle consumer (no work dispatched) looks dead. The trap DeepSeek caught: the harness **re-nudges** stuck handoff items on a cadence (`_HANDOFF_REEMIT_SECONDS=600`), and that cadence **equalled the grace window** (`ACTIVITY_GRACE_SECONDS=600`). Stamping the dispatch reference on every (re)nudge kept a wedged verifier/dm perpetually inside "within grace" — it could **never** read wedged. Worse, the shadow/observational rollout was blind to it: it never produced a "dead" verdict for exactly the zombie class it was built to catch.

**The rule.** Advance the dispatch reference (`last_dispatch_at`) **only when the consumer has caught up on prior dispatched work** — there's no prior dispatch, or its last activity is at/after the last dispatch. A re-nudge of *still-unacted* work leaves the original dispatch clock aging out, so the grace expires and the wedged verdict fires. Extracted as a pure, testable predicate (`should_advance_dispatch()`), not inlined at the emit site.

**How to apply (any "is this worker/agent/consumer alive by activity" model):**
- Liveness is **dispatch-relative**, not a pure timer — idle-with-no-work is never "dead".
- A re-dispatch / retry / re-nudge of the SAME unacted item must not reset the liveness grace. Tie the advance to "consumer made progress since last dispatch", never to "we poked it again".
- Watch for a re-emit/retry cadence that is ≤ the grace window — that exact equality silently defeats detection. Don't rely on the interval being longer; make the advance conditional.
- Keep the verdict a pure function reading a consistent snapshot (hold the state lock at the call site); shadow/observe it alongside the old signal before cutting over, and confirm the shadow can actually PRODUCE the "dead" verdict for a constructed zombie (else the observation proves nothing). See [[learning-shell-out-provisioning-has-three-sharp-edges]] for the sibling "front-load the standard DS findings for this shape" instinct.