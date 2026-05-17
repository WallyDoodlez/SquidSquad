# QA Results — #7630 Event-Driven Agent Architecture (Phase 4)

## Summary

**Verdict**: PASS — all PR acceptance criteria verified, all CRITICAL code review findings fixed.

**Scope**: This verification covers the Phase 4 PR (#8620) acceptance criteria. The full 28-TC test plan covers the entire epic (Phases 1-4); infrastructure-dependent TCs (requiring live harness + Monitor tool) are documented as HUMAN-REQUIRED below.

## Test Suite Results

- **Full test suite** (`python tests/run_tests.py`): 17 tests, all PASS
- **Harness tests** (`pytest tests/test_harness.py`): 38 tests, all PASS
- **Total**: 55 tests, 0 failures

## Acceptance Criteria Verification

### AC-1: Config gate (event-driven yes/no, defaults to no)
- **Result**: PASS
- **Evidence**: `config.py` line 70: `"event-driven": ("Event Driven", "Enabled")`, line 156: defaults to `"no"`. `python references/scripts/config.py get event-driven` returns `no`.

### AC-2: GET /events/for/{role} marks events dispatched
- **Result**: PASS
- **Evidence**: `harness.py:1126` ��� endpoint filters by `payload.target_role` or role's `reacts-to` types, calls `event_lifecycle.dispatch()` for each returned event. Verified via unit tests (TestEventDrivenPhase4 class) and manual lifecycle test.

### AC-3: POST /events/{id}/complete replaces ack-via-event
- **Result**: PASS
- **Evidence**: `harness.py:1176` — endpoint acks event in lifecycle manager, executes transitions and comments, returns 410 for stale events. Verified via direct Python invocation: dispatch → ack → double-ack returns False.

### AC-4: event_poll.py --target filters by payload.target_role
- **Result**: PASS
- **Evidence**: `event_poll.py:82-87` — when `target_mode=True`, uses `/events/for/{role}` endpoint instead of legacy `/events?role=`.

### AC-5: Sub-skill template updated with Monitor invocation pattern
- **Result**: PASS
- **Evidence**: `references/sub-skills/common/event-driven-workflow.md` exists (60+ lines), documents config gate, Monitor tool invocation, event types, processing flow, and completion API.

## E2E Lifecycle Verification (without HTTP server)

Tested directly via Python:
1. EventStream.append() — event stored ✓
2. EventLifecycleManager.dispatch() — event marked in-flight ✓
3. EventLifecycleManager.ack() — event cleared from in-flight ✓
4. Double ack — returns False (simulates 410) ✓
5. Dedup guard — same event dispatched twice = 1 in-flight ✓
6. In-flight cap (max_in_flight=2) — enforced, extras dropped ✓

## Code Review Critical Findings (all FIXED)

| # | Finding | Status | Evidence |
|---|---------|--------|----------|
| 1 | _persist() disk write outside lock | FIXED | harness.py:489 — entire snapshot+write inside `with self._lock:` |
| 2 | stop-confirmed mutates intent outside lock | FIXED | harness.py:1078 — wrapped in `with state._lock:` |
| 3 | ExternalActivityDetector set slice | FIXED | harness.py:1729 — now `dict[int, None]` with FIFO eviction |
| 4 | event_poll.py exits in --wait mode | FIXED | event_poll.py:133-138 — retries with sleep when `wait` is set |

## Test Plan TCs — Execution Status

### Executable TCs (verified this cycle):
- Smoke: harness imports OK, EventLifecycleManager API correct ✓
- Smoke: config gate defaults to `no` ✓
- Smoke: event-driven-workflow.md exists in sub-skills ✓
- TC-P3 (partial): In-flight dedup verified via unit test ✓
- TC-P4 (partial): Thread safety — 38 test_harness.py tests pass including concurrent scenarios ✓

### HUMAN-REQUIRED TCs (need running harness infrastructure):
- TC-P1: Event bus disk persistence survives harness restart — needs live harness
- TC-P2: Clone event bus discovery — needs sibling clone + running harness
- TC-2-01 through TC-2-08: Full event lifecycle with HTTP — needs harness + Monitor tool
- TC-3-01 through TC-3-03: Template migration — needs compose deploy-all with event-driven:yes
- TC-R01 through TC-R03: Regression tests �� needs full team running
- TC-RC01 through TC-RC03: Race conditions — needs concurrent processes
- TC-WIN01 through TC-WIN04: Windows-specific — needs live harness on Windows
- TC-FM01 through TC-FM03: Failure modes — needs deliberate crash injection

These TCs verify behaviors beyond the PR's Phase 4 scope (full epic infrastructure) and require human-operated testing environments.

## Verdict

**PASS** for Phase 4 PR scope. All acceptance criteria met. All critical findings fixed. Unit tests comprehensive. E2E lifecycle verified at the API level.

Infrastructure-dependent TCs (full harness + Monitor tool) are documented but not blocking — they test epic-level integration beyond this specific PR's deliverables.
