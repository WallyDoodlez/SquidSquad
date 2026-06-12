Now I have enough context. Let me produce the findings.

---

```
### Finding 1

- **File**: references/scripts/event_poll.py
- **Line**: 241-246
- **Severity**: error
- **Issue**: Eviction + empty batch + missing/falsy `oldest_id` silently loops forever instead of failing fast (regression from deleted #9740 guard).
- **Evidence**: The old code at the end of `poll()` contained:
  ```python
  if evicted and not events:
      if not oldest_id:
          return None  # fatal — harness contract violation, CONTEXT-9740 D4
  ```
  This guard is deleted in the model-B migration. The new code (lines 241–246) falls through to:
  ```python
  next_since = str(oldest_id) if oldest_id else (since or "")
  ```
  When `oldest_id` is `None` (or any falsy value like `0`, `""`), `next_since` equals the stale input `since`. The `--wait` loop (line 319) then re-polls with the same stale `since`, gets the same eviction response, re-emits a NUDGE, and sleeps — repeating forever. The old code returned `None` (fatal), causing `main()` to `sys.exit(2)` and triggering harness auto-reboot. The test `test_eviction_with_empty_events_still_nudges` in `tests/test_eviction_signal.py` (line 311–328) explicitly codifies the looping behavior and asserts `next_since == "stale-cursor"`. Its docstring claims "the agent's recovery clears it", but this is incorrect: the agent's `ack-cursor` posts cannot affect `event_poll`'s private in-memory hwm. Only an `event_poll` restart (hwm reset) or the harness returning real events from the stale position can break the loop.

- **Suggested fix**: Add back a guard that returns `None` (fatal) when `evicted` is true, `events` is empty, and `oldest_id` is absent/falsy — matching the pre-#9740 behavior. Alternatively, advance the hwm to a sentinel (e.g., `"0"`) so the next poll re-anchors from the deque origin, allowing forward progress. The current "hold hwm unchanged" path creates an unbounded re-nudge loop with no escape hatch.

---

### Finding 2

- **File**: references/scripts/event_poll.py
- **Line**: 162
- **Severity**: warning
- **Issue**: `_newest_id` uses truthiness (`if eid:`) to check for event IDs, rejecting valid-but-falsy IDs like integer `0`.
- **Evidence**: At line 161–162:
  ```python
  eid = event.get("id")
  if eid:
      return str(eid)
  ```
  `dict.get("id")` returns the stored value or `None`. If the harness emits an event with `"id": 0` (integer zero, valid JSON), `eid = 0`, and `if 0:` evaluates to `False`, so that event is silently skipped for hwm anchoring even though `"0"` would be a perfectly valid `since` parameter. The same truthiness pattern is used on line 245 with `if oldest_id:`, which also rejects integer-0 anchors from the eviction recovery path. While event IDs in this codebase are conventionally strings (always truthy), the data comes from an external harness response and the type is not enforced. The `_newest_id` walk already has a guard `isinstance(event, dict)` — an analogous guard for the id value would be `if eid is not None`.

- **Suggested fix**: Change the condition to `if eid is not None:` (line 162) and `if oldest_id is not None:` (line 245). This accepts integer `0`, float `0.0`, and empty string `""` as valid anchors while still rejecting JSON `null` (which becomes Python `None`). This is consistent with the docstring's claim that "events without an id cannot move the hwm" — events with `"id": 0` DO carry an id and SHOULD move the hwm.

---

### Finding 3

- **File**: tests/test_feat_9742_retry_ceiling.py
- **Line**: 95-99
- **Severity**: warning
- **Issue**: `test_ceiling_message_includes_failure_count` does not inspect the return value of `poll()`, missing coverage for the `result is None` path.
- **Evidence**: The test at lines 95–99:
  ```python
  def test_ceiling_message_includes_failure_count(self, monkeypatch, stub_port, capsys):
      boom = urllib.error.URLError("connection refused")
      monkeypatch.setattr(event_poll.urllib.request, "urlopen",
                          lambda req, timeout=None: (_ for _ in ()).throw(boom))
      event_poll.poll("skill", sleep=lambda _: None, max_consecutive_failures=10)
      err = capsys.readouterr().err
      assert "10 consecutive" in err
      assert "giving up" in err
  ```
  The call `event_poll.poll(...)` returns `None` when the ceiling is hit, but the return value is discarded. The patched `urlopen` uses a generator-throw trick (`(_ for _ in ()).throw(boom)`) which raises immediately — but only once per `urlopen` call. If `poll()` somehow survived the ceiling (e.g., due to a bug in the consecutive-failure counter) and tried a 11th `urlopen`, the generator would be exhausted and raise `StopIteration`, crashing the test with an unrelated exception rather than failing the ceiling assertion. Storing the return value and asserting `result is None` (as done in `test_returns_none_after_max_consecutive_failures` at line 40–43) would provide a direct ceiling-path assertion and make the test robust to generator exhaustion.

- **Suggested fix**: Capture the return value and assert it is `None`:
  ```python
  result = event_poll.poll("skill", sleep=lambda _: None, max_consecutive_failures=10)
  assert result is None
  ```
  This pattern is already used in the sibling test at line 40–43, making this a minor inconsistency.

---

### Finding 4

- **File**: tests/test_event_poll.py
- **Line**: 224, 227
- **Severity**: warning
- **Issue**: No test exercises `_newest_id` with a falsy-but-valid id (e.g., `"id": 0`), leaving the truthiness-gap uncovered.
- **Evidence**: The two `_newest_id` tests cover (a) trailing id-less events skipped, newest valid id found (line 222–224) and (b) all events lack anchorable ids → empty string (line 226–227). Neither test includes an event with `{"id": 0}` or `{"id": ""}`. If the `if eid:` guard on line 162 were accidentally changed or if a harness started emitting numeric ids starting from 0, the hwm could silently fail to advance, causing re-nudge loops.

- **Suggested fix**: Add a test like:
  ```python
  def test_newest_id_accepts_zero_id(self):
      assert event_poll._newest_id([{"id": 0}, {"id": "e2"}]) == "e2"
  ```
  This would fail under the current `if eid:` truthiness check and force the fix from Finding 2. Alternatively (if the fix from Finding 2 is applied), it would serve as a regression test ensuring integer ids are not rejected.
```