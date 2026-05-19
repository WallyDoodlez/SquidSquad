Here is my review.

---

### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: 482–491
- **Severity**: warning
- **Issue**: The `get_since()` wrapper is documented as "back-compat" (line 485–489) but changes the return ordering when a `since_id` cursor is provided. The old contract (documented in the `test_event_bus_reader.py` mock at line 141–150) returned **newest-first** in all branches (`items[-limit:]`, `after[-limit:]`). The new `get_since_with_eviction` (and therefore `get_since`) returns **oldest-first** when a cursor is supplied (`after[:limit]` at line 531 for cursor-found, `items[:limit]` at line 536 for cursor-evicted). While oldest-first is the correct contract for "skim-then-advance" and the HTTP endpoints were re-written to match (lines 1482–1485 apply `[:limit]` for the `since` case), the `get_since()` wrapper's claim of back-compat is misleading. Any external caller holding a reference to `EventStream.get_since` and depending on newest-first ordering would silently break.
- **Evidence**: Compare `test_event_bus_reader.py` line 149 (`after[-limit:]` — newest-first) with `harness.py` line 531 (`after[:limit]` — oldest-first). The comment "Back-compat wrapper" on line 485 is incorrect.
- **Suggested fix**: Either (a) update the `get_since` docstring to explicitly document the ordering contract as oldest-first-when-cursor-provided, dropping the "back-compat" claim, or (b) if true back-compat is required, make `get_since` preserve the old newest-first ordering by slicing with `[-limit:]` instead of delegating to `get_since_with_eviction`.

---

### Finding 2

- **File**: `tests/test_eviction_signal.py`
- **Line**: 94–102
- **Severity**: warning
- **Issue**: No test verifies the oldest-first ordering for the **cursor-found** (non-eviction) path when the number of events after the cursor exceeds the limit. The test `test_cursor_in_deque_returns_no_marker` (line 94–102) uses `limit=100` with only 4 events after the cursor — the truncation branch `after[:limit]` is never exercised. Every other `get_since_with_eviction` call in the test suite also uses `limit=100`. The only limit-truncation test is `test_evicted_events_returned_oldest_first` (line 144–160), which covers the **eviction** case. A regression that reverts the cursor-found branch to `after[-limit:]` (newest-first, matching the old `get_since` behavior) would pass all existing tests undetected.
- **Evidence**: Search for `get_since_with_eviction.*limit=` in `tests/` — every call uses `limit=100` which exceeds the deque sizes in those tests. The cursor-found path's `after[:limit]` at `harness.py` line 531 is never reached with `len(after) > limit` in any test.
- **Suggested fix**: Add a test case: create a stream with e.g. 20 events, call `get_since_with_eviction("e05", limit=3)`, assert returned IDs are `["e06", "e07", "e08"]` (oldest 3 after cursor) and marker is `None`. This catches both ordering regressions and the no-marker contract.

---

### Finding 3

- **File**: `references/scripts/harness.py`
- **Line**: 648–679 (specifically 650 and 679)
- **Severity**: warning
- **Issue**: The `EventLifecycleManager.load()` idempotency guard (`self._loaded` flag) is read and written without holding `self._lock`. While `load()` is currently only called from one place (`_deferred_init` in the lifespan), the pattern is fragile: if a future refactor calls `load()` from multiple threads, both could pass the `if self._loaded: return` check (line 650–651) and enter the event-loading loop, causing duplicate events in the stream and an inflated `_total_emitted_count`. The `_loaded = True` assignment at line 679 also races with the check.
- **Evidence**: Compare with `dispatch()` and `ack()` which guard their critical sections with `with self._lock:`. The `_loaded` flag has no such protection. The comment "Idempotent" on line 649 is true only under the current single-caller assumption.
- **Suggested fix**: Either check-and-set `_loaded` inside `with self._lock:` at the top of `load()`, or document that `load()` is not thread-safe and must be called exactly once during startup (matching the actual usage).

---

All three findings are warnings, not errors. The core eviction-signal math (`_total_emitted_count - len(items)` at line 538–539), the `event_poll.py` re-anchor logic (lines 204–234), and the endpoint wiring (lines 1487–1494, 1558–1562) are correct. Thread safety of `EventStream` is sound (all mutations/reads of `_events` and `_total_emitted_count` are under `self._lock`). The tests in `test_eviction_signal.py` otherwise provide good coverage of the eviction marker paths.