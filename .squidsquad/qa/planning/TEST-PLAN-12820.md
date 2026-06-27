# TEST-PLAN-12820 — qa clone .harness-port desync → permanent polling fallback

**Derived independently from issue #12820 (type:issue, medium, auto-approved) + skill's RCA — observed
behavior + root cause, not the worker's diff.** PR #12883 · branch `squidsquad/task/12820` · role:skill.

## Defect & root cause

`harness.py:find_free_port()` silently falls back to an ephemeral port when the desired port (7373)
is held. A SECOND harness started while the live one holds 7373 binds a random ephemeral port, writes
it to its clone's `.harness-port`, then exits → that port is dead. The qa clone is left pointing at a
dead ephemeral port → boot probe EXIT=7 → **permanent POLLING fallback** (event-mode qa unreachable).
Also causes the "qa inert/zombie" misdiagnosis (polling agents don't heartbeat the event bus).
**This is the root cause of qa's own stuck-in-polling condition every session.**

## Fix shape (skill)

Production path (no `--port`): probe canonical port via `GET /status`; a live harness there → refuse +
`exit(1)` (never bind ephemeral → never poison clones). Free / TIME_WAIT slot → claim canonical port
(uvicorn `SO_REUSEADDR` rebinds TIME_WAIT cleanly — supports the #12825 supervised restart). Explicit
`--port` (incl. `--port 0`) keeps the legacy ephemeral fallback for the integration test harness
(`real_harness` now passes `--port 0`).

## Test cases (derived ACs)

- **TC1 (AC1) — refuse 2nd production instance.** With a live harness already answering `/status` on
  the canonical port, a new production-path harness REFUSES (`exit(1)`) with a clear message — never
  binds an ephemeral port. Verify on the wire (real `/status` server, unmocked probe).
- **TC2 (AC2) — no clone poisoning.** The refuse path raises before `main()` writes/distributes the
  port → clone `.harness-port` files are never poisoned. (Structural: `_resolve_listen_port` raises
  prior to `state.port` assignment + port-file write.)
- **TC3 (AC3) — claim canonical when free + restart-safe.** Canonical port free → claim it (not
  ephemeral). `SO_REUSEADDR` handles a TIME_WAIT slot from a just-exited harness (the #12825
  supervised-restart relaunch).
- **TC4 (AC4) — test-harness path preserved.** Explicit `--port 0` takes the explicit branch and
  yields a real ephemeral port (not literal 0); the integration `real_harness` fixture spawns and
  self-writes its isolated `.harness-port`, read back correctly.
- **TC5 (AC5) — no-regression.** Full static gate green; harness/route-contract regression green;
  the load-bearing `real_harness` integration path green.
- **Independent gold-standard (live, unmocked):** drive the real `_resolve_listen_port` decision
  against a real harness-shaped `/status` server: (A) live peer → refuse; (B) free → claim; (C)
  `--port 0` → ephemeral.

## No comprehension test

harness.py (code) + integration fixture + unit tests; no LLM-consumed instruction changed → no CQ.

## Verdict rule

Zero-gap: every TC observable-PASS; the change set must introduce zero regressions (gate failures
attributable to #12820's diff, not orthogonal pre-existing issues).
