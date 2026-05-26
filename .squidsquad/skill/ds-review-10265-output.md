Here are my findings:

```
### Finding 1

- **File**: tests/integration/test_event_mode_e2e.py
- **Line**: 230
- **Severity**: warning
- **Issue**: The class annotation `_port_backup: bytes | None` is stale — it was part of the old backup/restore path that is now fully removed. The annotation is never backed by an assignment in `setUpClass` (the `cls._port_backup = ...` line was deleted), and nothing reads it (the `tearDownClass` restore branch was deleted). In Python, a bare annotation without assignment does NOT create a class attribute — it only populates `__annotations__`, so `cls._port_backup` would raise `AttributeError` if accessed.
- **Evidence**: The diff removed both the assignment in setUpClass (`cls._port_backup = (cls._port_file.read_bytes() ...)`) and the consumption in tearDownClass (`if cls._port_backup is not None: ...`), but left the annotation at line 230. Grep confirms `_port_backup` is not referenced anywhere else.
- **Suggested fix**: Delete line 230 (`_port_backup: bytes | None`).

### Finding 2

- **File**: tests/integration/test_event_mode_e2e.py
- **Line**: 344–374 (`test_live_squidsquad_harness_port_untouched`)
- **Severity**: warning
- **Issue**: The isolation test verifies correctness by asserting `live_port_value != self._port`. This check cannot distinguish between "SQUIDSQUAD_DIR isolation is broken and the test clobbered the live file" and "the live harness happens (coincidentally) to be running on the same ephemeral port the test randomly picked." If the live harness is on the same port, the test fails with a misleading message that falsely claims isolation is broken — a false-positive caused by a port collision, not a code defect.
- **Evidence**: `_find_free_port()` binds to port 0, which the OS assigns from the ephemeral range (typically 49152–65535). The harness default is 7373 (hardcoded in harness.py line 69), so practical collision probability is near zero. However, the harness can be started on any port, and the test's logic does not account for the coincidence case. The assertion message explicitly states "SQUIDSQUAD_DIR isolation is broken" as the only interpretation.
- **Suggested fix**: Snapshot the live file's content and/or `st_mtime` *before* `setUpClass` runs, then assert the snapshot matches the current live file after setUpClass. A simpler alternative: also assert that the live file's path (`.squidsquad/.harness-port`) is NOT under the test's isolated `_squid_dir`, which would catch the clobber case without the coincidence risk — but the existing `test_test_port_file_is_in_isolated_tmpdir` already covers this, so the port-value check could be replaced by an mtime-before-vs-after comparison.

### Finding 3

- **File**: tests/integration/test_event_mode_e2e.py
- **Line**: 248 (within `setUpClass`)
- **Severity**: warning
- **Issue**: `tempfile.mkdtemp(prefix="sq-e2e-")` creates a directory at line 248. If any subsequent line in `setUpClass` raises (e.g., `EventStream(maxlen=1000)` at line 256, `_find_free_port()` at line 257, or `ThreadingHTTPServer` at line 259), `tearDownClass` is never called by `unittest` — the tmpdir leaks. There are four statements between `mkdtemp` and the first operation that could fail, and no try/finally or atexit registration protects against a leak in the partial-setup window.
- **Evidence**: Python's `unittest` only calls `tearDownClass` when `setUpClass` completes without exception. Lines 249–264 include filesystem I/O (`mkdir`, `write_text`), object construction, and a `bind()` call — any of which can raise. The old code had the same class of risk (port backup could be orphaned), but the tmpdir leak is persistent until OS-level temp cleanup.
- **Suggested fix**: Either move `mkdtemp` to the very last setup step (minimizing the window), or wrap the mid-setup in `try: ... except: shutil.rmtree(cls._squid_tmpdir, ignore_errors=True); raise` so a failed setup still cleans up, or register an `atexit` handler immediately after `mkdtemp`.

### Finding 4

- **File**: references/scripts/event_bus_reader.py, references/scripts/event_poll.py
- **Line**: 28 (event_bus_reader.py), 50 (event_poll.py) — `import os` inside `_resolve_squid_dir()`
- **Severity**: warning
- **Issue**: The new `_resolve_squid_dir()` functions contain `import os` as a local import inside the function body. The docstring claims the code "Matches the pattern in harness._resolve_squidsquad_dir and event_bus._resolve_squid_dir" — but both of those reference files import `os` at the module level (harness.py:26, event_bus.py:14). The inner import contradicts the stated pattern. It is functionally harmless (Python caches module imports) but creates drift between the four files that now ostensibly share the same SQUIDSQUAD_DIR resolution contract.
- **Evidence**: harness.py line 26: `import os` at module level. event_bus.py line 14: `import os` at module level. event_bus_reader.py: no `import os` at module level; it appears inside `_resolve_squid_dir` at line 28. event_poll.py: same pattern at line 50. If a future maintainer copies the "pattern" from event_bus_reader.py into a new file, they'll replicate the local import rather than the module-level one.
- **Suggested fix**: Move `import os` to the module-level imports in both `event_bus_reader.py` and `event_poll.py`, matching what `harness.py` and `event_bus.py` already do. Remove the `import os` from inside `_resolve_squid_dir()`.
```