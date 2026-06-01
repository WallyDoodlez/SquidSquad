"""Shared OS-process helpers (#8891).

Cross-platform process liveness used by boot_remote, health_check, and
reboot_agent. thin_launcher.py keeps its own copy of this logic to avoid
importing this module (and indirectly any heavier deps) at boot — see
the comment there. If you change the semantics here, mirror the change
in thin_launcher.py:_is_process_alive.
"""

import ctypes
import os
import sys


# Win32 constants for OpenProcess + GetExitCodeProcess (#9904)
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259

# Cached typed kernel32 binding. See ``_win32_kernel32`` for the why.
_CACHED_KERNEL32 = None


def is_process_alive(pid):
    """Return True if a process with this PID is currently running.

    Cross-platform. On Windows we use the Win32 ``OpenProcess`` /
    ``GetExitCodeProcess`` APIs via ``ctypes`` — a direct kernel call
    that returns instantly. We do NOT shell out to ``tasklist``: on
    some Windows systems ``tasklist`` takes 20+ seconds per invocation
    (it traverses WMI under the hood), which compounds to >100 s when
    health_check probes 4 agents in a row and wedges the harness
    watchdog (#9904).

    POSIX uses ``os.kill(pid, 0)``, which only does the permission /
    existence check without delivering a signal.

    Uses ``sys.platform`` (compile-time constant) rather than
    ``platform.system()`` — the latter calls ``platform.uname()`` →
    ``_win32_ver`` → ``_wmi_query`` on Python 3.12 Windows and hangs
    indefinitely (#9903).

    Rejects ``None`` and any non-positive PID: ``os.kill(0, 0)`` would
    target the calling process group, and negative PIDs mean process
    groups too — both unsafe to treat as "is this specific process
    alive?".
    """
    if pid is None or pid <= 0:
        return False
    if sys.platform == "win32":
        return _is_alive_win32(pid)
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def _is_alive_win32(pid):
    """Win32 OpenProcess-based liveness check. Returns False on any error.

    Uses ``WinDLL(..., use_last_error=True)`` so the per-thread last-error
    slot is captured by ctypes immediately after each Win32 call (#10440):
    the default ``windll.kernel32`` doesn't, and any Python operation
    between the call and a follow-up ``GetLastError`` can reset the
    slot — making the ACCESS_DENIED-vs-INVALID_PARAMETER branch
    unreliable. Explicit ``argtypes``/``restype`` on the three Win32
    functions force the HANDLE to a full 64-bit pointer instead of the
    ``c_int`` default (32-bit signed) — ABI-correct on x64 and a no-op
    on x86.
    """
    kernel32 = _win32_kernel32()
    handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        # ERROR_INVALID_PARAMETER (87) means the PID is unknown to the OS
        # (process never existed or was reaped). ERROR_ACCESS_DENIED (5)
        # means the process exists but we can't open it — still alive.
        return ctypes.get_last_error() == 5
    try:
        exit_code = ctypes.c_ulong()
        if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
            return exit_code.value == _STILL_ACTIVE
        return True
    finally:
        kernel32.CloseHandle(handle)


def _win32_kernel32():
    """Return a ``WinDLL('kernel32', use_last_error=True)`` with the
    three Win32 functions used by ``_is_alive_win32`` typed explicitly.

    Lazily constructed so the import + signature setup don't fire on
    POSIX. Cached on the module to avoid re-typing on every call (the
    ``WinDLL`` handle and the ``argtypes`` assignments are idempotent
    but allocating fresh objects every call is wasteful).
    """
    global _CACHED_KERNEL32
    if _CACHED_KERNEL32 is not None:
        return _CACHED_KERNEL32
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k.GetExitCodeProcess.restype = wintypes.BOOL
    _CACHED_KERNEL32 = k
    return k
