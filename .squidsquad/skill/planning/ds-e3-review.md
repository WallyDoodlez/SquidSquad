### Finding 1

- **File**: references/scripts/l4_file_watcher.py
- **Line**: 216–225 (class `_Debouncer`, methods `schedule` and `_fire`)
- **Severity**: warning
- **Issue**: Race condition in `_Debouncer._fire` — when a new `schedule(key)` call arrives while the previous timer for `key` has already entered `_fire` but not yet acquired the lock, `_fire` pops **whichever timer is currently stored under `key`** from `_timers`, not necessarily the timer that invoked `_fire`. This causes two problems: (a) the new timer's entry is prematurely removed from `_timers` (so a subsequent `flush()` would miss it), and (b) the new timer will **still** fire its own `_fire` call later (it was already started), producing a duplicate callback invocation — violating the "coalesces to exactly one callback invocation per key" contract.

- **Evidence**: Trace through the interleaving:
  1. Timer T1 fires → enters `_fire("pm")` but pauses before acquiring `_lock`.
  2. Thread B calls `schedule("pm")` → acquires `_lock`, calls `T1.cancel()` (no-op because T1 is past waiting), creates T2, sets `_timers["pm"] = T2`, releases lock.
  3. T1 acquires lock, executes `self._timers.pop("pm", None)` → pops **T2**.
  4. T1 calls `self._callback("pm")`.
  5. Later, T2 fires → `_fire("pm")` → `_timers.pop("pm", None)` returns `None`, then calls `self._callback("pm")` **again**.
  
  Result: the callback fires twice instead of once.

- **Suggested fix**: Pass the timer identity to `_fire` and only pop if the stored timer matches. The standard pattern uses a generation counter or the timer object itself:

  ```python
  def schedule(self, key):
      with self._lock:
          entry = self._timers.get(key)
          gen = entry[0] + 1 if entry else 1
          if entry:
              entry[1].cancel()
          timer = threading.Timer(self._window, self._fire, args=(key, gen))
          timer.daemon = True
          self._timers[key] = (gen, timer)
          timer.start()

  def _fire(self, key, generation):
      with self._lock:
          entry = self._timers.get(key)
          if entry is None or entry[0] != generation:
              return  # stale — a newer schedule replaced us
          self._timers.pop(key, None)
      try:
          self._callback(key)
      except Exception as exc:
          print(...)
  ```

---

### Finding 2

- **File**: tests/test_l4_file_watcher_e3.py
- **Line**: 304–317 (method `TestChangeCallback.test_registry_read_per_change_call`)
- **Severity**: warning
- **Issue**: The `provider()` closure has an off-by-one logic error: `provider_calls.append(len(provider_calls))` records the length **before** the append, but then indexes with `registries[len(provider_calls) - 1]` using the length **after** the append. This causes the registries to be returned in **reverse order** — the first call returns `registries[-1]` (i.e. `_REGISTRY`, the 4-alias registry) instead of `registries[0]` (the 1-alias registry), and the second call returns `registries[0]`.

- **Evidence**: 
  - First call: `provider_calls` is `[]`, `len` → `0`, append `0` → `[0]`, returns `registries[0-1]` = `registries[-1]` = `_REGISTRY`.
  - Second call: `provider_calls` is `[0]`, `len` → `1`, append `1` → `[0,1]`, returns `registries[1-1]` = `registries[0]` = `{"pm": ("pm", None)}`.
  
  The comments claim the first call uses `registries[0]` (one alias) and the second uses `registries[1]` (two aliases), but the actual behavior is reversed. The test still passes because the total event count (3) is the same in either order — `1+2 = 2+1 = 3` — so the assertions remain satisfied by coincidence.

- **Suggested fix**: Correct the indexing so the registries are consumed in the intended order:
  ```python
  def provider():
      idx = len(provider_calls)
      provider_calls.append(idx)
      return registries[idx]
  ```
  Or, to make the test actually verify **which** registry was used (not just the count), assert the event aliases per call rather than just the total event count.