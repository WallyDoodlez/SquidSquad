---
name: learning-human-override-must-make-the-mutation-idempotent-not-just-skip-the-gate
description: a "human override" flag that bypasses a state machine's legality check must ALSO make the resulting mutation robust to wrong caller-supplied current-state — set the target state by removing whatever state is ACTUALLY present, not the state the caller claimed; otherwise the override corrupts the very state it exists to fix
metadata:
  type: learning
type: learning
tags: [learning, tracker, state-machine, force-override, idempotency, deepseek, distributed-systems, 12475]
created: 2026-06-15
owner: skill
status: active
confidence: high
source: observation
links: [learning-activity-liveness-redispatch-must-not-reset-grace]
---

# A human-override flag must make the mutation idempotent, not just skip the gate

**Observed (#12475 — tracker.py `transition --force`).** The ask was narrow: make `--force` (the human override) bypass the legal-transition matrix so a human can walk a mis-transitioned task back (e.g. `approved -> planning`, which the forward-only matrix forbade). The obvious one-line fix — gate the legality check on `not force` — was correct but **incomplete**, and a DeepSeek review caught the gap before ship.

**The trap.** `transition(number, from_status, to_status, ...)` took the *current* status as a **caller-supplied argument** (`from_status`) and used it to build the label-remove (`gh issue edit --remove-label <from>`). While the legality matrix was enforced, it constrained which `(from, to)` pairs could even reach the mutation, so a wrong `from` was mostly caught upstream. Once `--force` removes that constraint, a wrong `from_status` flows straight to the remove — and GitHub **silently ignores a remove-label for a label not present**. Result: the add succeeds, the remove no-ops, and the issue ends up carrying **two `status:*` labels** — state corruption introduced by the very override meant to *repair* state. The override is most likely to be used exactly when state is already confused, which is when the caller is most likely to pass a wrong `from`.

**The rule.** When a flag lets a human bypass a guard and force a state transition, don't trust the caller's claim about the *current* state. Make the mutation **set the target state idempotently**: read the live state and remove whatever is actually there (all of it, except the target), then add the target — so the post-condition is "exactly the target state" regardless of what the caller claimed or what mess already existed. This also opportunistically *cleans* a pre-corrupted record.

**How to apply (any force/override path that mutates state keyed on caller-supplied current-state):**
- Bypassing the *check* is half the fix; the other half is making the *write* robust to the wrong inputs the bypass now admits.
- Set-by-reconciliation, not set-by-delta: under override, derive the remove-set from the LIVE state (`live - {target}`), don't apply the caller's claimed delta.
- Keep the non-override hot path unchanged (no extra round-trip) — the guard still guarantees the claimed current-state there.
- Scope the override precisely: bypass exactly the guards named (here: legality + authority + unread-feedback) and keep true safety invariants intact (ship-integrity gates: unmerged-PR, coverage). "Override everything" is rarely what's asked; "shipped" integrity is not the same class of guard as "legal edge".
- This is the sibling instinct to [[learning-activity-liveness-redispatch-must-not-reset-grace]]: the load-bearing correctness lives in a detail the happy-path test never exercises — front-load the standard adversarial review for the change's shape and confirm the test actually drives the risky path (not a fixture-default fallback that masquerades as the happy path).
