Now I have a thorough understanding of the fix and the surrounding code. Let me trace through all four verification questions systematically:

**Question 1 — Correctness of `([], None)` on empty deque:**

When the deque is empty and the cursor is stale, `get_since_with_eviction` returns `([], None)`. In both HTTP endpoints (line 3052, line 3131), `eviction is not None` is `False`, so no `evicted`/`oldest_id` fields appear in the response JSON. In `event_poll.poll()` (line 283-284): `evicted = bool(payload.get("evicted"))` → `False`, `oldest_id = None`. The fatal guard (line 304) is `if evicted and not clean and not oldest_id:` → `False and ...` → does not fire. No nudge is emitted (line 325: `if clean or evicted:` → `False`). The `next_since` computation (lines 330-335) falls through to `next_since = str(oldest_id) if oldest_id else (since or "")` → `since or ""` (preserves the stale cursor). Back in `main()` (line 410-411): `if not events: time.sleep(http_timeout)` → sleeps. On next poll with the same stale cursor, if an event has since landed, `get_since_with_eviction` returns a marker with a valid `oldest_id` from the non-empty deque, agent gets a NUDGE, re-anchors — no events lost.

This is correct. The stale-cursor-against-empty-deque is a benign "nothing to deliver" state.

**Question 2 — Could `oldest_id` be `None` when marker IS emitted?**

The guard `if not items: return [], None` at line 1460 ensures the marker-building code at lines 1462-1468 only executes when `items` is non-empty. Line 1463: `oldest_id = items[0].get("id")`. Since all event creation paths (`_emit_event` at ~line 2387, `receive_event` at ~line 2980) guarantee every event has a non-empty `id` string, `items[0].get("id")` always returns a truthy string. No path exists where a marker is emitted with a falsy `oldest_id`.

**Question 3 — Busy-looping or event loss?**

No busy-looping: `event_poll.main()` sleeps for `http_timeout` between empty polls (line 411). No event loss: when the deque is empty, there are no events to lose. When events arrive, the re-anchor path through the eviction marker delivers them.

**Question 4 — Regression-test adequacy:**

`test_empty_deque_with_evicted_cursor_suppresses_marker` at line 145 in `test_eviction_signal.py` directly tests the exact scenario (empty deque + stale cursor → null marker). `test_eviction_marker_oldest_id_is_never_none` at line 162 tests the contract that emitted markers always carry a real id. `test_eviction_empty_no_anchor_is_fatal` at line 331 verifies the event_poll fatal guard is preserved as the backstop. Coverage is adequate.

NO_FINDINGS