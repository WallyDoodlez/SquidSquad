---
type: learning
description: When a verifier re-verifies an item it previously rejected, the unread-feedback transition guard flags the verifier's OWN prior reject comment as unaddressed and BLOCKS the pending-test->pending-ship transition; --force is the correct override because that feedback IS the reject the worker just addressed
tags: [verifier, tracker, transition, re-verification, reject-loop]
---

# Re-verify transition is blocked by your own prior reject — use --force

On a reject loop (`pending-test -> in-progress -> pending-test`), when the verifier
re-verifies and tries `tracker.py transition <N> pending-test pending-ship`, the
**unread-feedback guard blocks it**:

```
BLOCKED: #<N> has unread feedback from: verifier-lead (qa) (<timestamp>).
Read and address before transitioning. Use --force to override.
```

The "unread feedback" is the **verifier's OWN prior reject comment**. The guard can't
tell that the agent transitioning now is the same one that filed the reject, and that
the reject is precisely what the re-verification just confirmed addressed.

**Resolution:** `--force` is the correct, intended override here — you have read and
addressed that feedback (it was your reject; the worker's fix closed it; your
re-verification proved it). This is exactly the legitimate use of `--force`
(bypasses legality + authority + unread-feedback).

**Guardrail:** only force past *your own* already-resolved reject. If the unread
feedback is from a *different* party (PM, human, another agent) you have NOT yet
read, do NOT force — read and address it first. The check that makes forcing safe is
"is this the feedback I already acted on?", not "is the transition inconvenient?".

Related: [[learning-ead-status-routing-and-back-transition-dedup]] (the wake-routing
side of the same reject loop — dedup by last-status-per-issue so QA actually re-wakes
on the resubmit).
