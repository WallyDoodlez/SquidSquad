# RESEARCH-9741 — /events/for/{role} dispatch with no ack

**Issue**: #9741
**Phase**: 1 (Research)
**Author**: pm-research-agent
**Date**: 2026-05-21

---

## 1. Problem Statement

`GET /events/for/{role}` is the primary delivery endpoint for event-driven agents. On every successful response the handler calls `event_lifecycle.dispatch()` for each returned event. `dispatch()` marks the event in-flight, records a dispatch timestamp, and persists the full in-flight state to `.event-state.json`. A background `timeout_scan()` thread runs every 30 seconds and logs a retry/timeout message for any in-flight event that has not been acked within the configured timeout window (default 10 minutes, with configurable retry attempts).

The agent contract (`l1-base.md`, `cursor-management.md`) specifies cursor advancement as the only post-delivery action. There is no ack step. No caller in the codebase invokes `POST /events/{event_id}/complete` today. Result: every event delivered via `/events/for/{role}` accumulates in `.event-state.json` as an un-acked in-flight entry, generates log noise on every timeout-scan pass, and never gets cleaned up unless the harness restarts (at which point `load()` restores the same in-flight state from disk).

---

## 2. Code-Grounded Findings

### 2.1 Dispatch call site

`references/scripts/harness.py:1674–1678` — after filtering events for the role, the handler iterates the result set and calls `event_lifecycle.dispatch(eid, role, e)` for each event with a non-None `id`. This is unconditional; there is no config gate, no Phase 4 flag, no skip path.

### 2.2 EventLifecycleManager.dispatch()

`references/scripts/harness.py:628–644` — adds `event_id` to `self._in_flight[role]`, stores the full event dict in `self._dispatched`, records `time.time()` in `self._dispatch_times`, and calls `self._persist()`. The idempotency guard at line 638 (`if event_id in self._dispatched: return`) prevents double-dispatch across cursor re-polls, but it does not prevent the initial accumulation.

### 2.3 _persist() and .event-state.json growth

`references/scripts/harness.py:665–686` — writes `in_flight`, `dispatched`, `dispatch_times`, and `retry_counts` to `.event-state.json` on every `dispatch()` call (and every `ack()`, `timeout_scan()` that finds work). With no ack consumer, all four dicts grow monotonically. The `max_in_flight` cap (`harness.py:608`, default 50) prevents `_in_flight` per-role from exceeding 50 entries, but `_dispatched` and `_dispatch_times` are not separately bounded — they accumulate entries that were evicted from `_in_flight` due to the cap being hit, plus entries still awaiting timeout.

### 2.4 timeout_scan() noise path

`references/scripts/harness.py:742–788` — scans `_in_flight` every 30 seconds. For overdue events (default timeout: 10 minutes × `max_retries` before final expiry), it logs:
- `"Event <id> overdue for <role> (retry N/M)"` — emitted on every scan until max retries
- `"Event <id> TIMED OUT for <role> after M retries — escalating"` — final expiry

With the default `max_retries` from config, each delivered event generates multiple retry log lines before final expiry. After expiry the event is removed from `_in_flight` (and `_dispatch_times`, `_dispatched`, `_retry_counts`), so the growth is eventually bounded per event — but the log spam continues indefinitely as new events arrive from polling agents.

### 2.5 timeout_scanner is always running

`references/scripts/harness.py:1026–1027` — `event_lifecycle.load()` and `event_lifecycle.start_timeout_scanner()` are called unconditionally in the lifespan startup. The scanner cannot be disabled via config without harness changes.

### 2.6 No ack caller anywhere in the codebase

`event_bus.py:128–135` defines `ack(event_id, role)` which fires an `"ack"` event via `emit()`. The harness has no handler that maps a received `"ack"` event type back to `event_lifecycle.ack()`. The only ack path is `POST /events/{event_id}/complete` (`harness.py:1688–1743`), which calls `event_lifecycle.ack(event_id, role)` directly — but no agent, script, or test calls this endpoint in production code today.

### 2.7 `event_bus.py:ack()` is a dead stub

`references/scripts/event_bus.py:128–135` — `ack()` emits an event of type `"ack"` with `payload={"event_id": event_id}`. The harness event ingestion path (`POST /events`) receives this event and stores it in the stream, but there is no handler that translates an `"ack"` event type into `event_lifecycle.ack()`. The ack stub was written for the Phase 4 wiring but was never connected.

### 2.8 Tests that exercise the dispatch path

`tests/test_harness.py:1951–1963` — `test_marks_dispatched` explicitly asserts that `GET /events/for/skill` calls `event_lifecycle.dispatch()` and that the event appears in `get_in_flight("skill")`. This test **will break under Option A (strip dispatch)** — the assertion at line 1963 (`self.assertIn("e3", event_lifecycle.get_in_flight("skill"))`) would fail.

`tests/test_harness.py:1986–2002` — `test_does_not_redispatch_already_dispatched` pre-dispatches an event and verifies the idempotency guard holds after a second poll. This test also asserts in-flight membership and **breaks under Option A**.

No test exercises the ack or timeout paths against the `/events/for/{role}` endpoint. The timeout-scan tests (`tests/test_harness.py:1606–1748`) test `EventLifecycleManager` in isolation, not the HTTP endpoint.

### 2.9 `/events/{event_id}/complete` is a live but uncalled endpoint

`harness.py:1688–1743` — the endpoint is registered with FastAPI and responds to real HTTP requests. It calls `_execute_transition` and `_execute_comment` helpers which are Phase 4 side-effect executors. No guard prevents an agent from calling it today if it had the event_id. The endpoint returns 410 Gone for events not in-flight — which would always be the case if dispatch were stripped (Option A). This creates a semantically incoherent state: the `/complete` endpoint exists but dispatching is stripped, so it can never find an in-flight event.

---

## 3. Options A/B/C

These map to the issue body's Options 3/1/2 respectively, re-labeled for clarity.

### Option A — Strip dispatch() from the endpoint (issue Option 3, PM-preferred)

Remove lines 1674–1678 of `harness.py` (the `dispatch()` call loop). The `/events/for/{role}` endpoint becomes a pure filtered-read with no lifecycle side effects.

**What breaks**:
- `tests/test_harness.py:1951–1963` (`test_marks_dispatched`) — asserts in-flight tracking happens; must be updated or deleted.
- `tests/test_harness.py:1986–2002` (`test_does_not_redispatch_already_dispatched`) — same breakage; the idempotency guard is irrelevant without dispatch.
- `POST /events/{event_id}/complete` becomes semantically broken: it tries to ack an event that was never dispatched, always returns 410 Gone. The endpoint is not called today, so this is a latent semantic inconsistency, not a runtime regression.
- `GET /events/in-flight/{role}` (`harness.py:1746–1750`) will always return an empty list for events delivered via `/events/for/{role}`. Currently this is also vacuously true (all events time out eventually), so no behavioral regression in practice.

**What improves**:
- `.event-state.json` stops accumulating in-flight entries from agent poll cycles.
- No timeout log spam from un-acked events.
- No disk writes on every poll cycle (the `_persist()` call per dispatched event is eliminated).
- Code is simpler: the Phase 4 lifecycle path is dormant by construction, not by accident.

**Hidden dependency risk**: Low. The `dispatch()` call in the endpoint was added as Phase 4 plumbing before Phase 4 was wired. No downstream system reads or acts on in-flight state today except the timeout scanner (which generates the spam). Stripping it does not break any agent behavior.

**Test update required**: Yes — two tests in `tests/test_harness.py` assert the dispatch side effect and must be updated to assert that dispatch does NOT happen, or be removed.

### Option B — Document as intentionally dormant, strip timeout-scanner logging (issue Option 1)

Add a comment to the dispatch call noting Phase 4 deferral. Add a config gate (or hardcoded check) in `timeout_scan()` to suppress logging when no acks are expected. Leave dispatch() call in place.

**What breaks**: Nothing — purely additive.

**What improves**: Log spam stops. `.event-state.json` still grows (dispatch still fires), but silently.

**Downsides**: Root cause not fixed. State file continues to grow. The Phase 4 fiction persists — in-flight tracking runs but never resolves. Future contributors will still be confused. Requires modifying `timeout_scan()` to suppress logging, which adds a new `event-driven-ack-enabled` (or similar) config field, or hardcodes the suppression.

### Option C — cursor-advance-as-implicit-ack (issue Option 2)

`event_poll.py` POSTs to `POST /events/{event_id}/complete` after advancing the cursor. The harness acks the event, cleaning up in-flight state normally.

**What breaks**: Nothing directly, but introduces new complexity:
- `event_poll.py` needs to know the event_id of the event whose cursor just advanced. Currently cursor advancement is per-event (line 244-252 of event_poll.py), so the event_id is available. However, the ack POST must reach the harness — adding a second outbound HTTP call per event, doubling the network surface of the polling loop.
- `event_bus.py:ack()` is a stub that emits an `"ack"` event but does NOT call `POST /events/{event_id}/complete`. Using `event_bus.ack()` would not work; `event_poll.py` must call the harness endpoint directly.
- `POST /events/{event_id}/complete` (`harness.py:1688–1743`) was designed for Phase 4 side-effect execution (transitions, comments, commits). Using it as a pure ack channel imports the full Phase 4 machinery into a polling concern — semantic overloading.
- The `/complete` endpoint also executes `_execute_transition` and `_execute_comment` from the request body. A cursor-advance ack would send an empty `transitions`/`comments` list, which is fine today — but the coupling is fragile.

**What improves**: In-flight state is properly managed. Phase 4 lifecycle infrastructure gets its first real exercise (regression coverage).

**Downsides**: Highest complexity of the three options. Requires changes to `event_poll.py`, new HTTP call per event, and a meaningful test surface expansion. Premature: Phase 4 side-effect execution is not wired end-to-end; using the `/complete` endpoint for ack-only pulls it into production before it's hardened.

---

## 4. Recommended Option + Reasoning

**Option A (strip dispatch)** is the correct pre-event-flip fix.

Reasoning:
1. The dispatch call was Phase 4 forward-plumbing added before Phase 4 was designed end-to-end. It has no consumer. Stripping it removes dead weight, not live functionality.
2. The acceptance criteria in #9741 are purely negative: no in-flight accumulation, no timeout log spam. Option A satisfies both directly and permanently.
3. Option B silences symptoms without fixing the cause; Option C introduces premature Phase 4 wiring before the side-effect execution path (`_execute_transition`, `_execute_comment`) is hardened and tested.
4. The two breaking tests (`test_marks_dispatched`, `test_does_not_redispatch_already_dispatched`) assert the side effect that is being removed. They should be updated to assert the inverse (dispatch does NOT happen), which is the correct regression signal going forward.
5. `/events/{event_id}/complete` returning 410 when called without a preceding dispatch is semantically coherent: the endpoint says "event not in-flight," which is accurate. When Phase 4 is wired, dispatch is re-added alongside the ack consumer, and the endpoint resumes working as designed.

The risk surface is small: two tests to update, no agent behavior change, no config change needed.

---

## 5. Open Questions for PM/Human Before Phase 2 Locks

**Q1**: Should the two breaking tests be **updated** (assert dispatch does not happen) or **deleted** entirely?
- Update preserves regression coverage for the "endpoint does not accidentally re-introduce dispatch"; delete is cleaner if the dispatch behavior is considered purely Phase 4 territory.

**Q2**: Should the `GET /events/in-flight/{role}` endpoint (`harness.py:1746–1750`) be gated or documented as Phase 4 only after Option A lands?
- Currently returns empty list for events delivered via `/events/for/{role}` (since dispatch is stripped). It still works for events dispatched via other paths (if any). Document-only vs. remove vs. gate behind config flag.

**Q3**: Should the `event_bus.py:ack()` stub be removed or left in place?
- It emits an `"ack"` event that the harness stores but ignores. It is harmless but misleading. Option A doesn't require touching it, but cleanup is cheap.

**Q4**: Is stripping dispatch sufficient to stop `.event-state.json` growth entirely, or are there other paths that write in-flight state?
- From the code: `dispatch()` is the only path that adds entries to `_in_flight`/`_dispatched`. `ack()` and `timeout_scan()` remove entries. With no dispatch callers remaining, the in-flight dictionaries will drain to empty after the harness processes the timeout window for entries loaded from disk on startup, then stay empty. Confirmed: no other callsite calls `event_lifecycle.dispatch()` except `harness.py:1678` and test code.

**Q5**: Should the dispatch call be preserved as a commented-out stub with a `# Phase 4: re-enable when ack is wired` marker, or deleted cleanly?
- A comment preserves intent for Phase 4; a clean delete avoids confusion. Preference is a Phase 2 lock.

---

## 6. Out-of-Scope Notes

- **Phase 4 lifecycle wiring** (`_execute_transition`, `_execute_comment`, `POST /events/{event_id}/complete`) is out of scope. This fix is pre-event-flip only; Phase 4 re-adds dispatch when a real ack consumer exists.
- **`event_bus.py:ack()` functional wiring** — making `ack()` actually call `POST /events/{event_id}/complete` is Phase 4 work, not this bug.
- **`timeout_scan()` config gating** — no config changes needed under Option A; the scanner continues running but finds nothing to scan after in-flight drains.
- **`GET /events/in-flight/{role}` endpoint removal** — not required for the bug fix; if removed it should be a separate PR.
- **DM PR-merge-wait label-check gap** (AUDIT-A Risk 6) — separate issue, different fix surface.
- **Cursor re-anchor race** (AUDIT-A Risk 1) — separate issue (#9741 is Risk 2 only).
