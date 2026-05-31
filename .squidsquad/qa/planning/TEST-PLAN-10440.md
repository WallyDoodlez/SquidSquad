# TEST-PLAN-10440 — Win32 ctypes use_last_error + argtypes (process_utils + thin_launcher)

**Source**: issue #10440 body (Recommendation + DS round 1 toolhelp32 follow-up).
**Derived without reading the worker's diff.**

## Acceptance criteria

- **AC-1**: `process_utils._is_alive_win32` reads `ctypes.get_last_error()` (per-thread, thread-safe) instead of `kernel32.GetLastError()` (process-global, race-prone).
- **AC-2**: All Win32 funcs used by the liveness probe carry explicit `argtypes`/`restype`. Specifically: `OpenProcess` has `wintypes.HANDLE` restype (NOT default `c_int` which truncates 64-bit handles).
- **AC-3**: `_win32_kernel32` helper returns a cached typed binding; `WinDLL('kernel32', use_last_error=True)` is created exactly once.
- **AC-4**: `thin_launcher.py` mirrors the fix (per #8891 lockstep contract).
- **AC-5 (DS finding 1)**: `thin_launcher._win32_list_descendants` (toolhelp32 path) ALSO uses the typed binding; `INVALID_HANDLE_VALUE` switched from `-1` (broken on x64 under HANDLE restype) to `ctypes.c_void_p(-1).value`.
- **AC-6**: Dev tests cover the new shape (cache identity, argtypes inspection, `CloseHandle` always called on finally, `GetExitCodeProcess`-failure-treated-as-alive).

## Test Cases

### TC-1 (AC-1, AC-2): live `_win32_kernel32` inspection
- Probe: `OpenProcess.restype is wintypes.HANDLE` (c_void_p) — confirmed.
- `CloseHandle.argtypes == [c_void_p]`; `GetExitCodeProcess.argtypes == [c_void_p, LP_c_ulong]` — confirmed.

### TC-2 (AC-3): cache identity
- Probe: two calls to `_win32_kernel32()` return the same object — confirmed.

### TC-3 (live liveness): real PIDs return correct values
- Probe: `_is_alive_win32(os.getpid()) == True`, `_is_alive_win32(999999) == False` — confirmed.

### TC-4 (AC-4): `thin_launcher` mirror present
- Probe: `thin_launcher._win32_kernel32()` exists and `OpenProcess.restype is c_void_p` — confirmed.

### TC-5 (AC-5): toolhelp32 path typed
- Probe: `thin_launcher._win32_kernel32().CreateToolhelp32Snapshot.restype is c_void_p` — confirmed.

### TC-6 (AC-6): dev unit suite
- `pytest tests/test_process_utils.py tests/test_thin_launcher.py tests/test_thin_launcher_10101.py` → 74 passed, 2 skipped.

### TC-7 (canonical suite): `python tests/run_tests.py` → 52 passed / 2 skipped.

## Coverage matrix
- AC-1 → TC-1, TC-6
- AC-2 → TC-1, TC-6
- AC-3 → TC-2, TC-6
- AC-4 → TC-4, TC-6
- AC-5 → TC-5, TC-6
- AC-6 → TC-6

## Comprehension Questions
N/A — Python ctypes code only.

## Results
All TCs PASS. Note re race-warning DS finding 2: dev correctly documented and accepted because `WinDLL` is idempotent and the `argtypes/restype` assignments are identical writes to the same descriptors — benign race.
