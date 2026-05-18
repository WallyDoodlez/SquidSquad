### Finding 1

- **File**: `references/scripts/harness.py`
- **Line**: ~1545 (inside `_emit_event` function body, last executable line before the function closes)
- **Severity**: error
- **Issue**: `_log_event(body)` references an undefined variable `body`. The local variable that holds the assembled event dict is named `event`, not `body`. This `NameError` will crash every invocation of `_emit_event` at runtime, silently killing the daemon threads that call it.
- **Evidence**: The function signature is `def _emit_event(event_type, role, payload=None, **extra):`. The event dict is built into local variable `event` (assigned at `event = {…}`). There is no `body` parameter, no `body` local, and no module-level `body`. The call should be `_log_event(event)`. All three call sites are affected:
  - `_do_merge` (merge endpoint background thread) — thread dies before the PR merge even starts; the merge never executes.
  - `ExternalActivityDetector._check_for_changes` — caught by `except Exception`, so the poller survives but every emission attempt fails.
  - `TrackerHandoffDispatcher._dispatch_next` — same, caught by exception handler.
- **Suggested fix**: Replace `_log_event(body)` with `_log_event(event)`.

```
-    _log_event(body)
+    _log_event(event)
```

---

### Finding 2

- **File**: `references/scripts/cycle_post.py`
- **Line**: ~468–483 (function definition `_do_restart_sentinel`) and throughout `main()`
- **Severity**: warning
- **Issue**: `_do_restart_sentinel` writes a `.restart` sentinel file (`SQUID_DIR / role / ".restart"`). This is a sentinel-file write that bypasses the harness HTTP API for lifecycle operations — directly contradicting CONTEXT-4792.md §5.6 ("Delete `_do_restart_sentinel` — Q16") and the harness sole-authority principle. The function is defined but **never called** in `main()`, making it dead code right now — however any future code path that calls it re-introduces a sentinel-based parallel control path.
- **Evidence**: CONTEXT-4792.md §5.6 item "Delete `_do_restart_sentinel` (`cycle_post.py:468-483`) — Q16." The function body calls `sentinel.write_text(reason)` with path `.squidsquad/<role>/.restart`. CONTEXT-4792.md §2 Q16 says "Delete stale-file parsers immediately. No backward-compat window." The function docstring itself says "DEPRECATED" but the deletion mandated by Q16 has not been performed.
- **Suggested fix**: Delete the entire `_do_restart_sentinel` function (lines ~468–483). The rest of the file does not call it. Its presence is a time-bomb for anyone who later wires it back into the call chain.

---

**Overall assessment**: Beyond Finding 1 (the `_log_event(body)` NameError) and Finding 2 (stale `_do_restart_sentinel` that CONTEXT-4792.md mandates deletion), the three files are clean with respect to the locked thin-harness principles. The harness's tracker-observation + dispatch surfaces (`TrackerHandoffDispatcher`, `ExternalActivityDetector`, `GET /events/for/{role}` bootup gating) are already captured by #8914. The sentinel cleanup gaps in `cycle_post.py` are covered by #8918. No additional violations of the "forge is source of truth," "no mid-task interruption," or harness sole-authority principles were found in these files.