I've thoroughly analyzed the changed file `tests/integration/test_event_mode_e2e.py`, cross-referencing the production code in `references/scripts/harness.py` and `references/scripts/event_poll.py`. Here's my detailed assessment.

---

## Analysis

### Correctness — Eviction signal forwarding in `_serve_events` / `_serve_events_for_role`

The test handler's `_serve_events` (and `_serve_events_for_role`) faithfully mirrors production `GET /events` (harness.py:1493-1500) and `GET /events/for/{role}` (harness.py:1564-1568):

- Over-fetch `limit * 3` → call `get_since_with_eviction` → post-filter → trim to `limit` (oldest-first when `since` is set, newest-first otherwise) — matches harness.py:1466-1491 and harness.py:1531-1556.
- Eviction marker keys (`evicted`, `oldest_id`, `evicted_count_hint`) are forwarded identically — matches harness.py:1494-1500.
- The `get_since_with_eviction` eviction path (harness.py:539-551) returns `events = items[:limit]` (oldest-first) + `oldest_id = items[0].get("id")` + `evicted_count_hint = max(0, _total_emitted_count - len(items))` — the test exercises this exactly.

### Test `test_stale_cursor_logs_warning_and_advances` — trace-through

1. Cursor "evicted-before-the-deque-ever-saw-it" written to `working-state.md` — a value never present in any seeded event ID.
2. 1200 events seeded → deque retains last 1000 (e0200..e1199); `_total_emitted_count` ≥ 1200.
3. `event_poll.py` subprocess reads cursor from disk → sends `GET /events?since=evicted-before-the-deque-ever-saw-it&role=test-event-mode-e2e&limit=8`.
4. Server's `_serve_events` → `get_since_with_eviction` → cursor not found → eviction path: `events = items[:24]` (e0200..e0223), `oldest_id = "e0200"`, `evicted_count_hint ≥ 200`.
5. Trimmed to limit=8 → e0200..e0207 returned with eviction marker.
6. `event_poll.py` prints locked-format warning to stderr, re-anchors cursor to oldest_id ("e0200"), then emits e0200..e0207 to stdout, advancing cursor per-event to e0207.
7. Assertions: all pass for correct reasons.

### Test `test_eviction_then_next_poll_resumes_from_anchor` — trace-through

1. Cursor "stale-from-yesterday" + 1100 events seeded → deque retains e0100..e1099.
2. First poll (limit=5): eviction triggered, cursor advanced to e0104. Assertions check EVICTION presence and cursor position.
3. Second poll (limit=2000): cursor "e0104" found in deque → no eviction marker. Remaining 995 events (e0105..e1099) returned. All assertions pass.

### `_total_emitted_count` accumulation

The `setUp` method (line ~273) clears `_stream._events` but does **not** reset `_stream._total_emitted_count`. This is **explicitly acknowledged** in the test comment (lines ~770-774):

```python
# Count hint must be present and non-zero — the exact value is
# coarse (depends on lifetime emits across other tests sharing
# this class's EventStream, since _total_emitted_count is a
# lifetime counter; only `_events` is cleared between tests).
```

The test only asserts `evicted_count_hint > 0`. The accumulation can only **increase** the hint (it monotonically increments), never decrease it toward zero. Since each test independently seeds >maxlen events (1200 or 1100 into maxlen=1000), the hint is always ≥ 100 even in the first test of the class. No flakiness or false-pass risk.

### `_events` isolation

`setUp` clears `_events` under lock before each test writes its own cursor and seeds its own events. The two `TestEvictionGap` tests are fully independent — neither depends on the other's state.

---

## Verdict

**NO_FINDINGS**

The tests exercise the full eviction-signal pipeline end-to-end (EventStream → test server handler → event_poll subprocess → stderr/stdout assertions). All assertions are gated on specific, verifiable behavior:

- The locked-format stderr warning is substring-matched with the oldest retained ID as anchor and a comma after it (no false match on partial IDs).
- The count hint is regex-extracted and verified non-zero.
- Emitted event IDs are exact-matched to the expected slice of `retained_ids` (oldest-first order).
- Cursor advancement is verified against expected position.
- The second-poll "no eviction" guard uses `assertNotIn("EVICTION", ...)`.
- Exactly-one-warning guard uses `.count("EVICTION")`.

No assertion would pass if the eviction signal were not forwarded, if the cursor failed to advance, if events were emitted out of order, or if the second poll spuriously re-triggered eviction.