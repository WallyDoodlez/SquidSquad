# TEST-PLAN-9331 — Harness eviction signal + event_poll.py detection

**Issue**: #9331
**Owner**: qa-lead
**Derived from**: GitHub issue body (Scope §1–3, Acceptance list) + `.squidsquad/pm/planning/CONTEXT-9331.md` (§3 Shape Contract + §4 Warning Format — both LOCKED).
**Unblocks**: #8999 §4.4 IT-EvictionGap.

## Scope

Verify the harness emits an eviction marker on its `/events` and `/events/for/{role}` endpoints when the caller's cursor predates the retained deque, and verify `event_poll.py` detects the marker, emits exactly one stderr warning per detection in the locked format, and re-anchors the cursor to `oldest_id` before processing events.

This is a CODE task (not LLM-consumed instructions) — per CONTEXT-9331 §5, no CQ specs required.

## Coverage Matrix

| AC (issue body) | TC IDs |
|---|---|
| `get_since` payload carries marker when evicted; unchanged when in deque | TC-01, TC-02, TC-03 |
| `event_poll.py` detects + emits warning to stderr once per detection | TC-04, TC-05 |
| Unit tests cover both | TC-06 |
| #8999 §4.4 IT-EvictionGap unblocked | TC-07 |

## Test Cases

### TC-01 — EventStream layer: evicted vs in-deque (CONTEXT-9331 §3)
- **Steps**: instantiate `EventStream(maxlen=5)`, append 20 events `live00…live19`, call `get_since_with_eviction('live02', limit=100)`; then call again with cursor `live17` (still in deque).
- **Expected**:
  - Evicted call → `events == ['live15'…'live19']`, `marker == {'oldest_id': 'live15', 'evicted_count_hint': 15}` (20 emitted − 5 retained).
  - In-deque call → `events` are the post-cursor slice, `marker is None`.

### TC-02 — HTTP `/events` endpoint passthrough
- **Steps**: spin up `harness.app` via `fastapi.testclient.TestClient`, replace `event_stream` with `EventStream(maxlen=10)`, append 30 events, GET `/events?since=live02&limit=100` (evicted) then GET `/events?since=live22&limit=100` (in-deque) then GET `/events?limit=100` (no cursor).
- **Expected**:
  - Evicted → response includes `"evicted": true, "oldest_id": "live20", "evicted_count_hint": 20`.
  - In-deque → response omits all three keys.
  - No cursor → response omits all three keys; `keys == ['events', 'total']`.

### TC-03 — HTTP `/events/for/{role}` endpoint passthrough
- **Steps**: same setup, GET `/events/for/skill?since=live02&limit=100` then `/events/for/skill?since=live22&limit=100`.
- **Expected**: same shape contract as TC-02; eviction fields present only on the evicted call.

### TC-04 — `event_poll.py` warning text (CONTEXT-9331 §4)
- **Steps**: feed `event_poll.py`'s `poll()` a mocked `_fetch_once` response payload `{events: [...], evicted: True, oldest_id: 'X', evicted_count_hint: 7}`; capture stderr.
- **Expected**: stderr contains exactly one line matching the locked format `[event_poll] EVICTION: cursor predates retained window — advancing to X, ~7 events evicted`. `EVICTION` substring appears exactly once.

### TC-05 — `event_poll.py` no-eviction quiet path
- **Steps**: feed `event_poll.py`'s `poll()` a payload that omits the `evicted` key; capture stderr.
- **Expected**: stderr contains no `EVICTION` substring.

### TC-06 — Unit-test coverage of both layers
- **Steps**: `python -m pytest tests/test_eviction_signal.py -v`.
- **Expected**: All tests pass. Coverage includes EventStream layer (no-cursor, in-deque, evicted, empty deque, head, oldest-first ordering, total_emitted counter, legacy wrapper), event_poll layer (locked format, no-warning when no `evicted` flag, no-warning when `evicted: false`, empty-events still warns, re-anchor when role filter drops all events, re-anchor then per-event advance).

### TC-07 — Live HTTP via real uvicorn (#8999 §4.4 unblock confidence)
- **Steps**: spin up `harness.app` via `uvicorn.Server` on a random port, replace `event_stream` with `EventStream(maxlen=5)`, append 20 events, call `event_poll._fetch_once` against `http://127.0.0.1:<port>/events/for/qa?since=live02&limit=10`.
- **Expected**: response is a dict with `evicted: True`, `oldest_id: 'live15'`, `evicted_count_hint: 15`. Confirms #8999 §4.4 IT-EvictionGap has observable behavior to assert against.

### TC-08 — Full repo test suite (regression gate)
- **Steps**: `python tests/run_tests.py`.
- **Expected**: exit 0; new `test_eviction_signal` module collected (per `tests/run_tests.py` change) and passes.

## Execution Log

| TC | Result | Notes |
|----|--------|-------|
| TC-01 | PASS | live run: evicted call returned marker `{oldest_id: live15, evicted_count_hint: 15}`; in-deque returned `marker == None` |
| TC-02 | PASS | TestClient: evicted has `evicted/oldest_id/hint`; in-deque has only `[events, total]`; no-cursor same |
| TC-03 | PASS | TestClient: `/events/for/skill` mirrors `/events` contract; eviction fields present only on evicted call |
| TC-04 | PASS | `test_eviction_warning_matches_locked_format` asserts the locked substring + `EVICTION` count == 1 |
| TC-05 | PASS | `test_no_warning_when_payload_lacks_evicted_flag` + `test_no_warning_when_evicted_explicitly_false` |
| TC-06 | PASS | 15/15 in `tests/test_eviction_signal.py` |
| TC-07 | PASS | real uvicorn server returned `dict {evicted: True, oldest_id: live15, evicted_count_hint: 15}` to event_poll._fetch_once |
| TC-08 | PASS | `python tests/run_tests.py` exit 0; integration "Ran 17 tests OK"; eviction_signal module included via tests/run_tests.py registration |

## Verdict

**PASS — zero gaps. All ACs observably satisfied at unit, TestClient, and live-uvicorn fidelity. The eviction marker contract (CONTEXT-9331 §3) and warning format (CONTEXT-9331 §4) are byte-precise. #8999 §4.4 IT-EvictionGap is now writable against real behavior.**
