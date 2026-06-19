# QA-RESULTS-12511 — VERDICT: PASS (zero gaps) → pending-ship (DM)

**Verified 2026-06-19 01:31 (cy346) by verifier (qa).** PR #12867 · branch `squidsquad/task/12511`
@ `cc827aa8b`. type:issue · severity:high · auto-approved (bugs skip the approval gate). Append-only.

## AC walk — all PASS

| TC / AC | Result | Evidence |
|---------|--------|----------|
| **TC1 (AC1)** tests don't emit to live bus | PASS | A/B live-server proof (below): under pytest, an emit to the live harness port produces ZERO wire egress. |
| **TC2 (AC2)** guard suppresses tracker emit under test | PASS | Autouse `_block_live_harness_egress` fixture (tests/conftest.py) patches `urllib.request.urlopen`; suppresses any request whose URL contains `127.0.0.1:<live_port>` (port from `.harness-port`, default 7373), records it in `_SUPPRESSED_LIVE_EGRESS`, returns None. Regression TC1 asserts suppress+record. |
| **TC3 (AC3)** regression catches #999 repro | PASS | `test_12511_live_harness_egress_guard.py::TestForcedTransitionDoesNotLeak::test_emit_status_transition_is_suppressed` — emits the exact #999 `shipped→in-progress`; **RAN (not skipped)** because a live `.harness-port` is present; asserts the guard intercepted the POST (+1 suppression). |
| **TC4 (AC4-a)** no overblock | PASS | Regression TC2: emit to a NON-live port (7999) is delegated to real urlopen → raises URLError (NOT silently suppressed). Guard is live-port-scoped only. |
| **TC5 (AC4-b)** no-regression | PASS | Formerly-leaking files all green under guard: `test_12475_force_bypasses_legality` + `test_tracker` + `test_tracker_authority` = **163 passed**. `event_bus` own tests **26 passed** (unaffected). **Static gate PASS — 4589 gated, 0 fail/0 err** (2 listed known-failures pre-existing, #10360-blocked, not regressions). |

## Independent gold-standard — A/B live-server (verified on the wire)

Stood up a real HTTP listener on the live harness port (`.harness-port` = 28493 at run time):

- **CONTROL** — direct `event_bus.emit('status-transition','skill', {issue 999, shipped→in-progress})`
  via plain `python -c` (NO pytest guard): server received **2 live POSTs — `/events` AND
  `/hooks/activity`**. The leak reproduced live: emit reaches the production bus.
- **GUARDED** — the identical #999 emit run under pytest (TC3): server hit count stayed at **2 — zero
  new egress**. The guard suppressed it on the wire.

Conclusion: without the guard the emit hits the live bus; under the guard the identical emit produces
no wire egress. The fix eliminates the test→live-bus leak at the source. (Guard is path-agnostic /
port-scoped, so it catches both `/events` and the `/hooks/activity` heartbeat POST.)

## Independent-perspective notes

- Fix is **test-isolation only, no production-code change** (#12282 precedent) — correct: the defect
  is test hygiene, not runtime behavior. The guard is recurrence-proof (autouse → covers all current
  AND future transition tests), not a per-test patch.
- Why it doesn't break legitimate emits: integration tests run under unittest via `run_tests.py`
  (not pytest), so their intentional real-harness emits are untouched; event_bus's own tests use a
  different mechanism and a different/isolated port → 26 passed confirms no collateral.

## Non-gap observation (flagged to PM, not a blocker)

- Issue body's "**ideally** the harness rejects/ignores events for nonexistent issue numbers as a
  defense-in-depth" — worker explicitly DEFERRED + flagged to PM. This is an optional secondary
  hardening, NOT a core AC: removing the source (the leak) already kills the #999 flurry, which is the
  filed observed behavior. Correctly out of scope for #12511. PM to decide if a separate follow-up is
  wanted. NOT a zero-gap violation.

## Disposition

- Verdict comment posted to #12511 (clears unread-feedback guard) → transition **pending-test →
  pending-ship** (`--role verifier`).
- **Merge deferred to DM**: PR #12867 carries `Closes #12511` → a QA-merge would auto-close + skip DM.
  DM owns merge + ship. Ship counter NOT bumped (DM owns).
- Preserved permanently in `tests/`: `tests/conftest.py` guard + `tests/test_12511_live_harness_egress_guard.py`
  (both delivered by the worker's PR).
- No CQ (test-infra; no LLM-consumed instruction changed).
