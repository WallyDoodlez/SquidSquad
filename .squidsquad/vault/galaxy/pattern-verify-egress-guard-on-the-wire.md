---
name: pattern-verify-egress-guard-on-the-wire
description: Verify a test-isolation/egress guard on the wire (A/B live-server — control without the guard leaks, guarded is silent) rather than trusting the guard's own suppression-record assertions.
metadata:
  type: pattern
type: pattern
tags: [testing, verification, test-isolation, egress, qa, craft]
created: 2026-06-19
---

# Pattern — Verify a test-isolation / egress guard ON THE WIRE, not by its own assertions

**Validated 2026-06-19 (#12511 verification).**

## When to use

A fix in the **test-isolation-leak family** (#12282 / #12342 / #12511 …) — a guard that stops tests
from mutating or emitting to live runtime state (the live event bus, config.md, the harness port).
The guard's own regression test typically asserts "the guard recorded a suppression" — which proves
the *guard's bookkeeping*, not that **no bytes left the process**. Don't take that as sufficient.

## The technique — A/B live-server

Stand up a real listener on the exact resource the leak would hit, then compare control vs guarded:

1. Resolve the live target the guard keys on (e.g. `.harness-port`) and bind a throwaway HTTP server
   there that appends each received request to a log.
2. **CONTROL** — trigger the leaking path WITHOUT the guard (run the emit via plain `python -c`, i.e.
   outside pytest so the autouse fixture never loads). The server SHOULD receive the POST(s) — this
   proves the leak path is real, reachable, and that your listener captures it. (If control shows
   nothing, your harness is wrong — fix it before trusting the guarded run.)
3. **GUARDED** — trigger the identical path under the guard (run the same emit under pytest). The
   server hit count must NOT increase — zero wire egress.

The delta between CONTROL (n POSTs) and GUARDED (0 new) is the proof, independent of any assertion
the worker wrote. For #12511 this also surfaced that `event_bus.emit` hits TWO endpoints
(`/events` + `/hooks/activity`) — a port-scoped guard catches both, which a path-specific assertion
might have missed.

## Why it matters

It is the live-system embodiment of the role's independent-verification rule: a guard that "records a
suppression" can still be wrong (wrong port resolution, wrong needle, a second egress path) and its
self-test would stay green. Watching the wire catches all of that. Pairs with running the
formerly-leaking test files under the new guard (they must still pass) and confirming the guard does
NOT overblock a non-live port.

Related: [[learning-suite-exit-code-not-proof-of-all-pass]] (same skepticism — don't trust a green
signal that doesn't actually exercise the thing).
