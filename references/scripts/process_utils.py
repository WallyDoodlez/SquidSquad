"""Shared OS-process helpers (#8891).

Cross-platform process liveness used by boot_remote, health_check, and
reboot_agent. thin_launcher.py keeps its own copy of this logic to avoid
importing this module (and indirectly any heavier deps) at boot — see
the comment there. If you change the semantics here, mirror the change
in thin_launcher.py:_is_process_alive (and, for the image-verification
helpers below, thin_launcher.py:_image_name_for_pid /
_is_claude_process_alive).
"""

import ctypes
import os
import sys
from pathlib import Path


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
    # toolhelp32 (used by image_name_for_pid, #12294). Same #10440 ABI
    # fix as thin_launcher: CreateToolhelp32Snapshot.restype MUST be
    # HANDLE so INVALID_HANDLE_VALUE compares correctly at full pointer
    # width on x64; Process32First/Next take (HANDLE, LPPROCESSENTRY32)
    # passed as c_void_p so we don't import the struct layout here.
    k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    k.Process32First.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k.Process32First.restype = wintypes.BOOL
    k.Process32Next.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k.Process32Next.restype = wintypes.BOOL
    _CACHED_KERNEL32 = k
    return k


# Executable image names that identify a SquidSquad agent's claude process.
# npm/Windows installs run ``claude.exe``; a direct POSIX binary reports
# ``claude``. Compared case-insensitively against the OS-reported image name.
_CLAUDE_IMAGE_NAMES = ("claude.exe", "claude")


def image_name_for_pid(pid):
    """Return the lowercased executable image name for a live PID, or None.

    ``None`` means *undetermined* — the PID was not found in the process
    snapshot, the snapshot failed, or the platform offers no cheap image
    lookup. Callers MUST treat ``None`` as "could not verify" and fall
    back to plain liveness, never as "not our process" — mis-reading an
    undetermined image as a non-match would reclaim a live agent we
    simply couldn't inspect (#12294 AC2 safety).

    Windows uses the same in-process CreateToolhelp32Snapshot path as
    ``thin_launcher._win32_list_descendants`` (no ``tasklist`` shell-out —
    #9904). POSIX reads ``/proc/<pid>/comm`` (Linux); platforms without
    ``/proc`` (macOS) return ``None`` (undetermined).
    """
    if pid is None or pid <= 0:
        return None
    if sys.platform == "win32":
        return _image_name_win32(pid)
    try:
        comm = Path(f"/proc/{pid}/comm").read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return comm.lower() or None


def _image_name_win32(pid):
    """Win32 image-name lookup via toolhelp32. Returns lowercased name or None."""
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE_VALUE = ctypes.c_void_p(-1).value

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize", wintypes.DWORD),
            ("cntUsage", wintypes.DWORD),
            ("th32ProcessID", wintypes.DWORD),
            ("th32DefaultHeapID", ctypes.c_void_p),
            ("th32ModuleID", wintypes.DWORD),
            ("cntThreads", wintypes.DWORD),
            ("th32ParentProcessID", wintypes.DWORD),
            ("pcPriClassBase", wintypes.LONG),
            ("dwFlags", wintypes.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    kernel32 = _win32_kernel32()
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap is None or snap == INVALID_HANDLE_VALUE:
        return None
    try:
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        if not kernel32.Process32First(snap, ctypes.byref(entry)):
            return None
        while True:
            if entry.th32ProcessID == pid:
                # `or None`: an empty image name is "undetermined", not a
                # non-match — keep parity with the POSIX path so AC2's
                # fallback-to-liveness contract has no loophole (DS-12294-c1).
                return entry.szExeFile.decode(
                    "utf-8", errors="replace").lower() or None
            if not kernel32.Process32Next(snap, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snap)
    return None


def is_claude_process_alive(pid):
    """Return True iff ``pid`` is a live process whose image is claude (#12294).

    Image-verified liveness. A bare ``is_process_alive`` can be fooled by
    a recycled PID now owned by an unrelated process (the stale/recycled
    ``.claude-pid`` failure mode), so we trust a PID as "our agent" only
    when it is alive AND its image name is claude.

    When the image cannot be determined (``image_name_for_pid`` returns
    ``None`` — snapshot failure, or a platform without a cheap image
    lookup), fall back to plain liveness so a live agent we merely
    couldn't inspect is never mis-reclaimed (#12294 AC2). The recycled-PID
    reclaim (AC3) therefore depends on a working image lookup, which is the
    case on the Windows deployment target.
    """
    if not is_process_alive(pid):
        return False
    img = image_name_for_pid(pid)
    if img is None:
        return True
    return img in _CLAUDE_IMAGE_NAMES
