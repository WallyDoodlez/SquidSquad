---
name: learning-single-emit-wake-nudge-needs-bounded-reemit-and-must-bypass-time-filter
description: A one-shot wake-nudge delivered to a poll-less (event-mode) consumer is a starvation risk — if that single nudge is missed (consumer busy, cursor gap, ack-without-action) or the item was already in the actionable state when the emitter (re)started, the work stalls forever; the fix is a bounded re-emit cadence that runs until the triggering condition clears AND deliberately bypasses any "updated-since-last-check" time filter, because a stuck item's updatedAt is in the past — the very thing that hides it
metadata:
  type: learning
type: learning
tags: [learning, harness, liveness, events, ead, delivery, reboot, 12442, 12342, 12418, self-hosting]
created: 2026-06-15
updated: 2026-06-15
owner: skill
status: active
confidence: high
source: observation
links: [learning-ead-status-routing-and-back-transition-dedup, learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]
---

# A single-emit wake-nudge to a poll-less consumer starves; re-emit on a bounded cadence and bypass the time filter

**Built (#12442):** the External Activity Detector (#12342) routes work by emitting an `assigned-to` wake nudge when an issue changes status. It emitted **exactly once per transition**, gated by `updatedAt > _last_check_epoch`. For terminal HANDOFF statuses (`pending-test → verifier`, `pending-ship → dm`) that single nudge is the *only* delivery path to an often **event-mode** agent — one that does not poll, so a missed nudge is never re-discovered. Observed: #12418 sat `pending-ship` 48 min until PM hand-injected a wake event.

**Two failure modes, one root shape:**
1. **Missed single nudge.** The consumer was busy mid-cycle, between drains, had a cursor gap, or acked-without-acting. There is no second nudge — `mark_emitted` records the status so later polls dedup it away. Starves.
2. **Startup blindness.** The item was ALREADY at the actionable status when the emitter (re)started. The detector resets `_last_check_epoch = now` on start, so the item's *old* `updatedAt` fails the `updated > last_check` time filter — and its `updatedAt` will never bump again until something acts on it, which is the thing that's stuck. Invisible forever.

**The fix — bounded re-emit that bypasses the time filter:**
- Re-emit the nudge on a bounded cadence (here 600s) **while the item remains in the actionable state**, until the status changes (which removes it from the open+pending query and naturally ends the re-emit). Idempotent: a wake nudge just makes the consumer re-check its queue; a redundant one is harmless.
- **Critically, the re-emit path must NOT consult the "updated since last check" time filter.** A stuck item's `updatedAt` is in the past *by definition* — gating re-emit on recency re-creates the exact blindness you're fixing. The cadence timer (`now - last_emit >= interval`) is the only gate.
- Scope the re-emit to consumers that **can't poll for themselves.** Here only the two handoff statuses (route to a *different* agent than the builder) get it; worker statuses (`approved`/`open`) keep single-emit because their worker is already looping its own queue. Don't broaden the blast radius to consumers that have their own discovery path.
- Keep the fast path: a fresh transition still emits immediately AND seeds the cadence timer, so the next poll within the interval doesn't double-fire, and a re-entry (back-transition) re-emits at once rather than waiting out the interval.

**How to apply:**
- Any time you deliver a one-shot signal to a consumer that does not independently re-poll, ask "what happens if this single delivery is lost?" If the answer is "starves forever," you need a bounded re-emit keyed off the *persisting condition*, not off the *change event*.
- Re-emit safety rests on **idempotency** — design the signal so a duplicate is a no-op (a wake nudge that triggers a re-check, not a command that mutates). Contrast the spam-resistance concern in [[learning-sessionend-presence-not-stop-reason-and-spam-resistant-breaker]]: a self-reported signal must not RESET a safety counter; a re-emitted wake nudge is fine precisely because it grants no leniency, it just re-asks.
- "Updated-since-last-check" filters are correct for *change* detection and wrong for *stuck-state* detection. If one routine does both, give the stuck-state path its own gate.
