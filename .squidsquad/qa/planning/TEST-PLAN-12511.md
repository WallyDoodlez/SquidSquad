# TEST-PLAN-12511 — Test-isolation leak: force-transition tests emit to the LIVE event bus

**Derived independently from issue #12511 (type:issue, severity:high, auto-approved) — observed
behavior + "Suggested AC direction", not from the worker's diff.**
PR #12867 · branch `squidsquad/task/12511` · role:skill.

## Defect

`tracker.transition(...)` / `tracker.add_comment(...)` → `event_bus.emit(...)` discovers the dev
box's live `.harness-port` (default 7373) and fires a real `POST /events`. Unit tests exercising
transitions therefore leak illegal `status-transition` events for fixture issues (#999 etc.) onto
the PRODUCTION bus → every event-mode agent is spuriously woken (wasted wake/token + noise that
masks real events; cross-linked to the #12837 anchorless-eviction liveness risk). Forge state
is unaffected (#999 isn't real). Same family as #12282.

## Test cases (derived ACs)

- **TC1 (AC1) — tests don't emit to the live harness.** A transition/emit executed under pytest
  produces ZERO egress on the wire to the live harness port. Verify on the wire, not just by
  assertion.
- **TC2 (AC2) — guard suppresses `tracker.py` emit under test.** An autouse guard intercepts
  `urllib.request.urlopen` and suppresses any request to the live harness port; records the
  suppression for inspection. Returns None (event_bus.emit is fire-and-forget → invisible to caller).
- **TC3 (AC3) — regression catches the #999 repro.** A test that emits the exact #999
  `status-transition` (`shipped→in-progress`) is intercepted by the guard; runs (not skips) when a
  live `.harness-port` is present.
- **TC4 (AC4-a) — no overblock.** The guard must NOT suppress egress to a NON-live port (delegates
  to real urlopen → URLError), so isolated-harness tests and event_bus's own tests are unaffected.
- **TC5 (AC4-b) — no-regression.** Formerly-leaking test files still pass under the guard;
  event_bus's own tests pass; full static gate green. Integration tests (unittest via run_tests.py)
  keep their intentional real-harness emits (the pytest fixture doesn't touch them).
- **Independent gold-standard (A/B live-server):** stand up a real HTTP listener on the live port.
  CONTROL (direct emit, no pytest guard) → server receives the live POST(s). GUARDED (same emit
  under pytest) → server receives nothing. Proves the fix on the wire, independent of worker assertions.

## Out of scope (flagged, not a gap)

- Issue body's "and **ideally** the harness rejects/ignores events for nonexistent issue numbers as
  a defense-in-depth" — an explicit optional hardening, worker-deferred + flagged to PM. Removing
  the source (the leak) already kills the #999 flurry; the harness-side validation is a separate
  follow-up for PM to decide. NOT a core AC → not a zero-gap blocker.

## No comprehension test

Test-infra only (tests/conftest.py + a regression test); no LLM-consumed instruction changed → no CQ.

## Verdict rule

Zero-gap: every TC observable-PASS. The observed defect (#999 flurry from test egress) must be
fully eliminated at the source.
