# Code Review — #7630 Event-Driven Architecture
## Model: Claude (fallback)

---

### Finding 1: _persist() disk write is outside self._lock — concurrent callers can clobber each other's .tmp file
- **Severity**: CRITICAL
- **File**: references/scripts/harness.py:481-496
- **Issue**: `_persist()` acquires `self._lock` to snapshot in-memory state, then releases the lock before the disk write (`tmp.write_text(...)` and `tmp.replace(...)`). Two concurrent callers — e.g. `ack()` from the health poller thread and `append()` from the FastAPI event thread — both write to the same `.event-state.json.tmp` path. The second write overwrites the first `.tmp` before the first `replace()` completes, producing a state file that either omits the first caller's updates or is half-written. The project's own pattern in `HarnessState.save_state()` (line 312-334) explicitly holds `self._lock` for the entire snapshot-and-write sequence, citing #7441 as the reason.
- **Fix**: Move `get_recent(200)` inside `with self._lock:` and keep the disk write inside the same lock block. The docstring concern about lock ordering (`self._lock` → `EventStream._lock`) is already the real ordering used by `load()`, so this is safe.

---

### Finding 2: stop-confirmed ack mutates agent.intent outside any lock
- **Severity**: CRITICAL
- **File**: references/scripts/harness.py:1066-1070
- **Issue**: When an ack event with `result == "stop-confirmed"` arrives, the handler does `agent = state.get_agent(role)` (acquires and releases `state._lock`), then mutates `agent.intent` outside any lock. The health poller thread runs concurrently and may read and overwrite `agent.intent` in `update_health()` between the `get_agent()` call and the mutation. Every other stop-intent path (e.g. `stop_agent`, `stop_all`, `_do_shutdown`) acquires `state._lock` before mutating intent, or calls `state.set_agent()` which does so. This code path is the only exception.
- **Fix**: Wrap the mutation in `with state._lock:` or use a pattern matching `stop_agent()` at line 1147-1150: acquire the lock, mutate, call `set_agent()`.

---

### Finding 3: ExternalActivityDetector dedup trim slices an unordered set — wrong issues are retained
- **Severity**: CRITICAL
- **File**: references/scripts/harness.py:1675-1676
- **Issue**: When `len(self._emitted_issues) > 500`, the trim is:
  ```python
  self._emitted_issues = set(list(self._emitted_issues)[-200:])
  ```
  Python sets are unordered. `list(some_set)` produces an arbitrary ordering that changes between Python versions and runs. The intent is to keep the 200 most recently added issue numbers, but `[-200:]` of an unordered list is 200 arbitrarily-selected entries. Issues that were trimmed away will be re-emitted the next poll cycle as if new, producing spurious duplicate `assigned-to` events for agents.
- **Fix**: Replace `_emitted_issues: set[int]` with `collections.OrderedDict[int, None]` (ordered insertion). On add: `self._emitted_issues[issue_num] = None`. On trim: `while len(self._emitted_issues) > 500: self._emitted_issues.popitem(last=False)`. This keeps the oldest 200 entries evicted first.

---

### Finding 4: event_poll.py exits with code 2 on harness-unreachable even in --wait loop mode — permanently kills the monitor
- **Severity**: CRITICAL
- **File**: references/scripts/event_poll.py:113-114
- **Issue**: In the `main()` loop, when `poll()` returns `None` (harness unreachable or any network error), the code calls `sys.exit(2)` unconditionally — even when `--wait` loop mode is active. The documented usage in `event-driven-workflow.md` runs `event_poll.py <role> --wait 30` as the background Monitor tool process. A single transient harness restart or network hiccup while in loop mode kills the entire polling process permanently. The Monitor tool would stop receiving events and the agent would never wake for new work.
- **Fix**: Guard the exit on whether loop mode is active:
  ```python
  if events is None:
      if wait is None:
          sys.exit(2)
      # Harness temporarily unreachable — log and retry
      print(f"ERROR: harness unreachable (will retry in {wait}s)", file=sys.stderr)
      time.sleep(wait)
      continue
  ```

---

### Finding 5: EventLifecycleManager.load() calls self._stream.append() inside self._lock — inconsistent lock order vs _persist()
- **Severity**: MEDIUM
- **File**: references/scripts/harness.py:512-514
- **Issue**: `load()` acquires `self._lock` then calls `self._stream.append(event)` inside that block, which acquires `EventStream._lock`. This establishes lock order: `self._lock` → `EventStream._lock`. But `_persist()` deliberately acquires `EventStream._lock` first (`get_recent()` outside `self._lock`) then `self._lock`. The two lock orderings are opposite and will deadlock if both paths run concurrently on overlapping locks. Currently safe only because `load()` runs at startup before the poller and event threads start. Once the deferred-init thread starts background activity while `load()` is still running (a real risk since `_deferred_init` calls both `state.load_state()` and `event_lifecycle.load()` sequentially with no barrier), this window exists.
- **Fix**: In `load()`, move the `self._stream.append(event)` calls outside `with self._lock:` — collect `events_to_load` from the parsed data, release the lock, then append them to the stream. This matches the ordering used by `_persist()`.

---

### Finding 6: dispatch() is never called — in-flight tracking, timeout escalation, and ack() are functionally inert
- **Severity**: MEDIUM
- **File**: references/scripts/harness.py:445-453
- **Issue**: `EventLifecycleManager.dispatch()` has no callers anywhere in the codebase. Neither `POST /events`, `_emit_event()`, nor any other path calls it. As a result, `_in_flight`, `_dispatched`, and `_dispatch_times` are always empty, `ack()` always returns `False`, `timeout_scan()` never finds anything to escalate, and `GET /events/in-flight/{role}` always returns empty. The Phase 2 lifecycle machinery described in the task (#7630 2-3, 2-6, 2-7) is wired up structurally but is never activated.
- **Fix**: Either wire `dispatch()` into the `POST /events` handler when an event is targeted at a role (requires a `target_role` field in events), or add a clear code comment that `dispatch()` is Phase 4 plumbing and intentionally dormant. Without this, the timeout scanner thread consumes CPU scanning empty dicts, and the ack protocol silently does nothing.

---

### Finding 7: event-driven-workflow.md and cycle-runner are both included in dev's includes.yml — contradictory operating mode directives in composed CLAUDE.md
- **Severity**: MEDIUM
- **File**: references/roles/dev/includes.yml:4-5 and references/sub-skills/common/event-driven-workflow.md:38-42
- **Issue**: `includes.yml` includes `common/cycle-runner` (line 4) and `common/event-driven-workflow` (line 5). `cycle-runner` defines the full Ralph Loop with `cycle_pre.py`/`cycle_post.py`. `event-driven-workflow.md` explicitly states: "No cycle_pre.py / cycle_post.py" and "No /loop — the harness delivers events; you don't poll." The composed CLAUDE.md therefore contains both sets of directives. An agent cannot determine which operating mode to use without external context. The two modes are mutually exclusive: Ralph Loop polls on a timer; event-driven waits for harness dispatch. Including both creates ambiguity that the agent must resolve probabilistically.
- **Fix**: Separate these into distinct role variants, or add a top-level `## Operating Mode` directive (driven by a config flag) that explicitly selects one mode and suppresses the other. At minimum, add a precedence comment in `event-driven-workflow.md` stating it supersedes `cycle-runner` when both are included.

---

### Finding 8: TestBootAgentLock mock parameters — _spawn_terminal 3-tuple is correct, but no test covers the None terminal_pid path in boot_agent()
- **Severity**: LOW
- **File**: tests/test_boot_remote.py:334, 347, 388
- **Issue**: The 3-tuple mock patterns `(True, "spawned", 12345)`, `(False, "failed", None)`, and `(True, "spawned", 12345)` are all correctly structured — they match the `(success, message, terminal_pid)` return signature of `_spawn_terminal`, `_spawn_windows`, `_spawn_macos`, and `_spawn_linux`. No structural bug. However, the test `test_clears_sentinel_on_spawn_failure` passes `(False, "failed", None)` — the `None` terminal_pid — and the test only asserts `result["success"] is False` and `mock_clear.assert_called_once()`. It does not assert that `result.get("terminal_pid")` is `None`, which means a regression that accidentally sets `terminal_pid` to a non-None value on failure would not be caught.
- **Fix**: Add `assert result.get("terminal_pid") is None` to `test_clears_sentinel_on_spawn_failure` to verify the failure path does not leak a stale PID.
