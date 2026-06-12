I've carefully reviewed all the changed files. Let me verify the key claims systematically:

1. **Deleted surface callers**: Grep confirms zero remaining references to `dispatch()`, `ack()`, `get_in_flight()`, `timeout_scan()`, `start_timeout_scanner()`, `stop_timeout_scanner()`, `_scan_loop`, `_in_flight`, `_dispatched`, `_dispatch_times`, `_retry_counts` in the changed production files (harness.py, cycle_pre.py) — only the docstring comment at `harness.py:1912` mentions the old `ack()` in explaining what was removed.

2. **Legacy state file loading**: `load()` at `harness.py:1054` reads `data.get("events", [])` and `data.get("cursors", {})` only. The old keys (`in_flight`, `dispatched`, `dispatch_times`, `retry_counts`) are never accessed — silently ignored as claimed. The legacy-load test at `test_harness.py:1735-1759` validates this: it creates a state file with all four legacy keys, calls `load()`, and confirms events + cursors restore correctly without `AttributeError`.

3. **Lock ordering**: The `advance_cursor()` method at `harness.py:931-990` acquires `EventLifecycleManager._lock` (outer) then calls `EventStream.has_event`/`find_positions` which acquire `EventStream._lock` (inner). `_persist()` at `harness.py:992-1012` does the same: `self._lock` → `self._stream.get_recent()`. `load()` at `harness.py:1055-1065` acquires `self._lock` for cursor restoration, releases it, then calls `self._stream.append()` (acquires `EventStream._lock` externally). No inversion — consistent outer→inner ordering.

4. **Constructor signature**: All callers in the changed files use `EventLifecycleManager(stream)` with a single argument — matches the new `__init__(self, stream: EventStream)` signature at `harness.py:905`. The global instantiation at `harness.py:1075` was updated. Test instantiations all use single-arg form.

5. **`_parse_cli_args` return type change**: The caller `main()` at `cycle_pre.py:1311` correctly unpacks the single return value. All `task_id` branches were removed. The `TestParseCliArgs` tests were updated to match the new signature.

6. **POST /events/{id}/complete → 410**: The endpoint at `harness.py:2129` unconditionally returns a 410 `JSONResponse` — no body parsing, no lifecycle access. Tests confirm 410 for both well-formed and empty bodies.

7. **GET /events/lifecycle drops in_flight**: The endpoint at `harness.py:2286-2297` returns only `stream_size` and `persisted`. Test `test_events_lifecycle_omits_in_flight` at `test_harness.py:1162-1170` confirms `in_flight` is absent.

8. **GET /events/in-flight/{role} removed**: Deleted entirely; route-contract entry at `test_harness_route_contract.py` was removed.

9. **Timeout scanner removed**: `start_timeout_scanner()` call removed from `lifespan` at `harness.py:1280` (previously followed `event_lifecycle.load()`).

10. **Test cleanup**: `TestGetEventsForRole.setUp` at `test_harness.py:2334-2337` no longer tries to clear `_in_flight`/`_dispatched`/`_dispatch_times` (those attributes don't exist); remaining tests in that class don't reference them. `TestCompleteEventEndpoint` no longer requires any lifecycle state setup.

No correctness defects, regressions, or integration issues found in the changed files.

```
NO_FINDINGS
```