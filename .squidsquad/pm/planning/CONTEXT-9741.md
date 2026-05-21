# CONTEXT-9741 — Strip dispatch() from GET /events/for/{role}

**Issue**: #9741
**Phase**: 2 (Locked Decisions)
**Author**: pm-lead
**Date**: 2026-05-21
**Status**: pending → planned (after human approval of these locks)

> **AUTHORITATIVE SCOPE**: the GitHub issue body for #9741 + this CONTEXT-9741.md combined are the contract for skill at pickup.

---

## Scope

Remove the unconditional `dispatch()` call from `GET /events/for/{role}` so the endpoint is a pure filtered-read with no lifecycle side effects. Two tests in `tests/test_harness.py` that assert dispatch happens must invert their assertions in the same PR. No other behavioral changes ship in this PR.

---

## 1. Locked Decisions

### D1. Option A — Strip `dispatch()` from the endpoint

**Locked**: remove `harness.py:1674–1678` (the `dispatch()` call loop). The endpoint becomes a pure filtered-read.

Reasoning: the call is dead Phase 4 plumbing with no consumer. Stripping it stops `.event-state.json` growth and log spam at the root cause, not as suppression. Log spam disappears as a natural consequence of D1 — no separate mitigation needed.

### D2. Test assertion inversion — IN THIS PR

**Locked**: skill rewrites both tests in the same PR:
- `tests/test_harness.py:1951–1963` (`test_marks_dispatched`) — assertions must invert to verify dispatch does NOT happen.
- `tests/test_harness.py:1986–2002` (`test_does_not_redispatch_already_dispatched`) — same inversion; idempotency guard is irrelevant without dispatch, so the test verifies the endpoint does not touch `event_lifecycle` in-flight state.

PM defines the behavioral expectation only. Dev writes the rewritten test bodies.

### D3. `POST /events/{event_id}/complete` 410 behavior — KEEP AS-IS

**Locked**: the endpoint correctly returns 410 for events not in-flight. With dispatch stripped, all events are perpetually not-in-flight via this endpoint — that is accurate, not a bug. No changes to `harness.py:1688–1743`.

### D4. `event_bus.py:ack()` stub — OUT OF SCOPE

**Locked**: do not touch `event_bus.py:128–135`. Skill files a follow-up bug for the dead stub but does not modify `ack()` in this PR. Wiring is Phase 4 work.

### D5. Dispatch call removal style — CLEAN DELETE

**Locked**: delete lines 1674–1678 cleanly. No commented-out stub, no `# Phase 4: re-enable` marker. The CONTEXT document is the Phase 4 re-add instruction; inline comments add confusion.

---

## 2. Grounded File References

| File | Lines | Change |
|---|---|---|
| `references/scripts/harness.py` | 1674–1678 | Delete `dispatch()` call loop |
| `references/scripts/harness.py` | 628–644 | `EventLifecycleManager.dispatch()` — read-only context |
| `references/scripts/harness.py` | 665–686 | `_persist()` — no longer called per-poll after D1 |
| `references/scripts/harness.py` | 742–788 | `timeout_scan()` — no longer finds in-flight entries post-D1 |
| `references/scripts/harness.py` | 1688–1743 | `POST /events/{event_id}/complete` — no change (D3) |
| `references/scripts/event_bus.py` | 128–135 | `ack()` stub — no change (D4) |
| `tests/test_harness.py` | 1951–1963 | `test_marks_dispatched` — assertions invert |
| `tests/test_harness.py` | 1986–2002 | `test_does_not_redispatch_already_dispatched` — assertions invert |

---

## 3. Acceptance Criteria

- **AC-1**: `GET /events/for/{role}` returns filtered events for the role without calling `event_lifecycle.dispatch()`. Delivering events via this endpoint does not add any entry to `.event-state.json` in-flight, dispatched, dispatch-times, or retry-counts dicts.
- **AC-2**: After delivering N events via `GET /events/for/{role}`, `.event-state.json` shows zero new in-flight entries for that role (or the file is absent/empty if it was empty before).
- **AC-3**: The timeout scanner (`harness.py:742–788`) produces no "Event overdue" or "Event TIMED OUT" log lines for events delivered via `GET /events/for/{role}`.
- **AC-4**: `test_marks_dispatched` and `test_does_not_redispatch_already_dispatched` pass with inverted assertions — both now assert that delivery via the endpoint does NOT result in in-flight membership.
- **AC-5**: All other existing harness tests pass unmodified. No regression in timeout-scan tests (`tests/test_harness.py:1606–1748`), which test `EventLifecycleManager` in isolation and are unaffected by D1.
- **AC-6**: Skill files a follow-up bug for `event_bus.py:ack()` dead stub before marking this PR pending-test. Bug number referenced in PR description.

---

## 4. Out of Scope

- `event_bus.py:ack()` stub wiring — Phase 4. Skill files follow-up bug, does not touch the method.
- `POST /events/{event_id}/complete` changes — endpoint kept as-is (D3).
- Log-spam suppression config gates — moot after D1; root cause removed.
- `GET /events/in-flight/{role}` endpoint changes — still valid for other dispatch paths; no change needed.
- `timeout_scan()` config gating or removal — scanner runs but finds nothing; leave it dormant.
- Phase 4 lifecycle wiring (`_execute_transition`, `_execute_comment`).

---

## 5. Sequencing

**Tier 1** — this fix is a standalone, pre-event-flip cleanup. Parallel with other Tier 1 issues (#9740, #9742, #9744). No dependency on any in-flight task. Can ship in any order before the fleet reset.

Post-ship: no agent reboot needed. The dispatch call was a server-side side effect only; agents do not observe its removal.

---

## 6. Risk Notes

1. **Test inversion must cover both test bodies** — partial inversion (e.g., deleting one test, inverting the other) leaves an asymmetric regression signal. Both must be rewritten as positive assertions that dispatch does NOT happen.
2. **`_dispatched` / `_in_flight` drain window** — entries already persisted to `.event-state.json` before this ship will remain until the timeout window expires (default 10 min). QA should clear `.event-state.json` before verifying AC-2, or wait for the timeout window.
3. **No other `dispatch()` callsites** — confirmed by research: `harness.py:1678` and test code are the only callers. Deleting this block leaves `EventLifecycleManager.dispatch()` reachable only from tests. Low risk; method stays in place for Phase 4 re-add.
4. **`POST /events/{event_id}/complete` semantic state** — with dispatch stripped, the `/complete` endpoint can never find an in-flight event from polling-mode delivery. This is latent semantic incoherence, not a runtime error. Phase 4 re-adds dispatch alongside the ack consumer, restoring coherence. Document this in the PR description so reviewers understand the deliberate state.

---

## 7. Open Questions Resolved

| Q | Locked |
|---|---|
| Q1 (tests) | **Update with inverted assertions** — preserve regression coverage that dispatch does NOT happen |
| Q2 (`/events/in-flight/{role}` gate) | **No change** — endpoint is still valid for other dispatch paths; document-only |
| Q3 (`event_bus.py:ack()` stub) | **Leave in place; skill files follow-up bug** — cleanup is Phase 4 |
| Q4 (`.event-state.json` growth other paths) | **Confirmed none** — `dispatch()` in `harness.py:1678` is the sole callsite; file drains after timeout window |
| Q5 (delete clean vs commented stub) | **Clean delete** (D5) — CONTEXT is the Phase 4 re-add instruction |

---

## 8. Next Step

PM transitions #9741 `pending → planned`. Human reviews CONTEXT-9741.md. On approval, PM transitions `planned → approved`. Skill picks up.
