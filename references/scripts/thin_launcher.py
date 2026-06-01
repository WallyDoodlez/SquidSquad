#!/usr/bin/env python3
"""SquidSquad Thin Launcher — one-shot agent bootstrapper (#4966).

Replaces the wrapper scripts (start-{role}.ps1/.sh). Starts claude in the
agent's clone directory, writes the PID for harness monitoring, and waits
for claude to exit. No respawn loop, no heartbeat, no sentinel file checks.

The harness owns all lifecycle decisions (restart, stop, crash recovery).

Usage:
    python references/scripts/thin_launcher.py <role> [--force]

Environment:
    SQUIDSQUAD_ROLE is set automatically by this script before starting claude.

Exit codes:
    0  — claude exited normally
    42 — claude exited with code 42 (context pressure / intent exit)
    1  — error (could not start claude)
    3  — refused: another agent of this role is already running in this clone (#8692)
"""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VALID_EFFORT_LEVELS = {"low", "medium", "high", "max"}

# Win32 constants for OpenProcess + GetExitCodeProcess (#9904)
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
_STILL_ACTIVE = 259

# Cached typed kernel32 binding for the Windows liveness probe (#10440).
# Mirrored from process_utils — see the note above _is_process_alive.
_CACHED_KERNEL32 = None

# #10101: poll budget for resolving the actual claude.exe descendant
# of the cmd.exe wrapper spawned by the npm shim on Windows.
_CLAUDE_EXE_RESOLVE_TIMEOUT_S = 5.0
_CLAUDE_EXE_RESOLVE_POLL_S = 0.1
# Bound BFS depth in the descendant walker (DS 10101 Finding 3). Real
# process trees from `cmd.exe → claude.exe` (or `cmd.exe → node.exe →
# claude.exe`) are depth ≤ 2; allow extra headroom for unforeseen
# wrapping layers without unbounded traversal.
_DESCENDANT_MAX_DEPTH = 5


def _get_effort_level(role):
    """Read per-agent effort level from config.md. Falls back to 'high'."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        level = (get_field(f"effort-{role}") or "high").strip().lower()
        return level if level in VALID_EFFORT_LEVELS else "high"
    except (Exception, SystemExit):
        return "high"


def _get_interval():
    """Read iteration interval (minutes) from config.md. Falls back to '30' (#9725).

    Used to construct the spawn /loop prompt so freshly spawned agents register
    a recurring loop on their first turn rather than running one inline cycle
    and stalling (CONTEXT-9725 §2).
    """
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        val = get_field("interval")
        if val is None:
            return "30"
        s = str(val).strip()
        return s if s else "30"
    except (Exception, SystemExit):
        return "30"


def _is_process_alive(pid):
    """Check if a process with the given PID is still running. Cross-platform.

    Canonical version lives in ``process_utils.is_process_alive`` — kept
    local here to avoid importing extra modules at launcher startup
    (#8891). If you change the semantics there, mirror the change here.

    Windows path uses Win32 ``OpenProcess`` / ``GetExitCodeProcess`` via
    ``ctypes`` (instant, kernel-direct). We do NOT shell out to
    ``tasklist`` — on some Windows systems it takes 20+ s and wedges
    the harness (#9904). Uses ``sys.platform`` not ``platform.system()``
    to dodge the Python 3.12 Windows WMI hang (#9903).

    Built on ``WinDLL(..., use_last_error=True)`` + explicit
    ``argtypes``/``restype`` (#10440). The default ``windll.kernel32``
    lets an interleaved Python operation reset the per-thread last-error
    slot before ``GetLastError`` is read, making the ACCESS_DENIED-vs-
    INVALID_PARAMETER branch unreliable.
    """
    if pid is None or pid <= 0:
        return False
    if sys.platform == "win32":
        import ctypes  # noqa: F401  — kept in the win32 branch per #8891
        kernel32 = _win32_kernel32()
        handle = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return ctypes.get_last_error() == 5  # ACCESS_DENIED → exists
        try:
            exit_code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return exit_code.value == _STILL_ACTIVE
            return True
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def _win32_kernel32():
    """Return a typed ``WinDLL('kernel32', use_last_error=True)`` (#10440).

    Sibling of ``process_utils._win32_kernel32`` — kept local here to
    avoid importing process_utils at launcher startup (#8891). If you
    change the semantics there, mirror the change here.

    This binding also types the toolhelp32 functions that
    ``_win32_list_descendants`` uses (CreateToolhelp32Snapshot,
    Process32First, Process32Next) — same #10440 ABI-correctness fix
    for HANDLE width, same use_last_error guarantee.

    Thread-safety: the check-then-set pattern below races under the GIL
    (two threads can both observe None and both write). The race is
    benign — ``ctypes.WinDLL`` is idempotent for the same DLL name and
    the ``argtypes``/``restype`` assignments are identical assignments
    to the same function descriptors. Different cache writers produce
    equivalent typed bindings; no caller observes a partially-typed
    descriptor.
    """
    global _CACHED_KERNEL32
    if _CACHED_KERNEL32 is not None:
        return _CACHED_KERNEL32
    import ctypes
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.OpenProcess.restype = wintypes.HANDLE
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.CloseHandle.restype = wintypes.BOOL
    k.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    k.GetExitCodeProcess.restype = wintypes.BOOL
    # toolhelp32 (used by _win32_list_descendants). Restype on
    # CreateToolhelp32Snapshot must be HANDLE so the INVALID_HANDLE_VALUE
    # comparison works with the full 64-bit pointer width on x64.
    k.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    k.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    # Process32First/Next take (HANDLE, LPPROCESSENTRY32). The struct
    # pointer goes through as ``c_void_p`` so we don't need to import
    # the PROCESSENTRY32 layout here.
    k.Process32First.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k.Process32First.restype = wintypes.BOOL
    k.Process32Next.argtypes = [wintypes.HANDLE, ctypes.c_void_p]
    k.Process32Next.restype = wintypes.BOOL
    _CACHED_KERNEL32 = k
    return k


def _check_singleton(clone_path, role):
    """Return a live PID if another agent of this role is already running here.

    Reads `.squidsquad/<role>/.claude-pid` and verifies the recorded process
    is still alive. Stale pid files (process exited without cleanup) return
    None — the new boot is allowed and will overwrite the file (#8692).
    """
    pid_file = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None
    if pid == os.getpid():
        # Defensive: our own PID shouldn't be there, but if it is, treat as stale.
        return None
    return pid if _is_process_alive(pid) else None


def _resolve_claude_exe_pid(wrapper_pid, claude_exe_used,
                            _now=None, _sleep=None, _list_children=None):
    """Resolve the actual claude.exe descendant PID, given the wrapper PID
    that Popen returned (#10101).

    Background: on Windows installs via npm, ``shutil.which("claude")``
    returns ``claude.CMD`` — a 7-line cmd shim that invokes the real
    ``node_modules\\@anthropic-ai\\claude-code\\bin\\claude.exe`` and
    exits. ``Popen(claude.CMD).pid`` is therefore the cmd.exe wrapper,
    not the claude.exe we need for singleton enforcement. The wrapper
    exits in seconds; claude.exe outlives it by hours. When the wrapper
    dies, ``.claude-pid`` (if it recorded the wrapper PID) becomes stale
    and singleton check returns "no agent alive" forever after — even
    though claude.exe is still running. Result: duplicate claude.exe on
    next thin_launcher invocation.

    This function polls the wrapper's descendant tree for a claude.exe
    process and returns its PID. Falls back to ``wrapper_pid`` if the
    descendant cannot be found within the timeout (preserves the prior
    behavior so we never write nothing).

    No-op when the launched executable was already claude.exe directly
    (i.e., no shim involved) — that's the Linux/macOS path and any
    Windows install that exposes claude.exe on PATH. ``claude_exe_used``
    is the path returned by ``shutil.which("claude")``; if it already
    ends in ``.exe``, return ``wrapper_pid`` unchanged.

    Args injected for tests: ``_now`` (clock source), ``_sleep`` (sleep
    impl), ``_list_children`` (process-tree walker that returns a list
    of ``{"pid": int, "name": str}`` dicts for a given parent PID).
    """
    # Fast path: trust the wrapper PID directly when we know we didn't
    # go through a shim.
    # - ``None`` claude_exe_used: we don't know what was launched; don't
    #   burn 5s polling for a descendant that may not exist.
    # - non-Windows + .exe / extensionless: POSIX shells launch claude
    #   directly, no shim involved.
    #
    # On Windows we always walk the descendant tree regardless of the
    # extension (DS 10101 Finding 4): npm currently ships .cmd shims,
    # but the PATHEXT-resolved shim could also be .bat / .ps1 / .vbs /
    # .com, and a non-shim .exe rarely matches Popen's child PID when
    # CMD interpretation is involved. The cost is ~one toolhelp snapshot
    # (sub-ms) on the happy path; the upside is the stale-wrapper bug
    # cannot recur silently if Anthropic ever ships a non-.cmd shim.
    if claude_exe_used is None:
        return wrapper_pid
    if sys.platform != "win32" and not claude_exe_used.lower().endswith(
            (".cmd", ".bat", ".ps1")):
        return wrapper_pid

    # Cross-platform claude.exe descendant lookup. We use Win32 toolhelp via
    # ctypes on Windows (no subprocess shell-out — matches the #9904 posture
    # of avoiding tasklist). On non-Windows the shim case doesn't arise in
    # practice, but the same poll loop with a Linux-flavored child walker
    # keeps the function pure for tests.
    sleep_fn = _sleep if _sleep is not None else time.sleep
    now_fn = _now if _now is not None else time.monotonic
    list_children = _list_children if _list_children is not None else (
        _win32_list_descendants if sys.platform == "win32"
        else _posix_list_descendants
    )

    deadline = now_fn() + _CLAUDE_EXE_RESOLVE_TIMEOUT_S
    while now_fn() < deadline:
        try:
            descendants = list_children(wrapper_pid)
        except Exception:
            descendants = []
        for entry in descendants:
            name = (entry.get("name") or "").lower()
            if name == "claude.exe" or name == "claude":
                return entry.get("pid", wrapper_pid)
        sleep_fn(_CLAUDE_EXE_RESOLVE_POLL_S)

    # Timeout: claude.exe didn't appear under wrapper in budget. Preserve
    # the prior behavior — write the wrapper PID and let singleton fail
    # closed (false-positive-stale is the old failure mode; at least
    # we're no worse off than before this fix).
    print(
        f"[thin-launcher] WARNING: could not resolve claude.exe descendant "
        f"of wrapper PID {wrapper_pid} within "
        f"{_CLAUDE_EXE_RESOLVE_TIMEOUT_S}s (#10101); recording wrapper PID. "
        f"Singleton enforcement may misbehave if the wrapper exits before "
        f"the next thin_launcher invocation.",
        file=sys.stderr,
    )
    return wrapper_pid


def _win32_list_descendants(parent_pid):
    """Return all descendants of `parent_pid` on Windows via toolhelp32.

    Implementation note: builds the full process snapshot then walks the
    tree from `parent_pid`. CreateToolhelp32Snapshot is in-process and
    avoids the WMI / tasklist hangs documented in #9903 / #9904.

    Uses the same ``_win32_kernel32()`` typed binding as
    ``_is_process_alive`` (#10440) so handle values aren't truncated to
    ``c_int`` and ``INVALID_HANDLE_VALUE`` compares correctly on x64.
    """
    import ctypes
    from ctypes import wintypes

    TH32CS_SNAPPROCESS = 0x00000002
    # x64: INVALID_HANDLE_VALUE is ``((HANDLE)(LONG_PTR)-1)`` —
    # ``0xFFFFFFFFFFFFFFFF`` as an unsigned. ``c_void_p(-1).value`` gives
    # us that on both 32- and 64-bit Python, so the comparison works
    # regardless of pointer width.
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
        return []

    try:
        entry = PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
        # Build {pid: (parent_pid, name)} map.
        procs = {}
        if not kernel32.Process32First(snap, ctypes.byref(entry)):
            return []
        while True:
            procs[entry.th32ProcessID] = (
                entry.th32ParentProcessID,
                entry.szExeFile.decode("utf-8", errors="replace"),
            )
            if not kernel32.Process32Next(snap, ctypes.byref(entry)):
                break
    finally:
        kernel32.CloseHandle(snap)

    # Walk descendants of parent_pid (BFS). claude.exe is typically a
    # direct child of the cmd.exe shim, sometimes one hop deeper through
    # an intermediate node.exe wrapper. Capped at _DESCENDANT_MAX_DEPTH
    # to bound traversal on pathological process trees (DS 10101 F3).
    out = []
    frontier = [parent_pid]
    seen = {parent_pid}
    depth = 0
    while frontier and depth < _DESCENDANT_MAX_DEPTH:
        next_frontier = []
        for ppid in frontier:
            for pid, (parent, name) in procs.items():
                if parent == ppid and pid not in seen:
                    seen.add(pid)
                    out.append({"pid": pid, "name": name})
                    next_frontier.append(pid)
        frontier = next_frontier
        depth += 1
    return out


def _posix_list_descendants(parent_pid):
    """Return all descendants of `parent_pid` on POSIX via /proc.

    Reserved for future use — the shim-wrapper bug doesn't occur on
    Linux/macOS today because shutil.which("claude") returns the
    binary directly. Implemented for symmetry + future-proofing.
    """
    out = []
    proc_dir = Path("/proc")
    if not proc_dir.is_dir():
        return out
    # Build pid → (ppid, name) map from /proc/<pid>/stat.
    # OSError on individual /proc entries (race with process exit) is
    # expected and skipped per-entry. We do NOT swallow programming
    # errors at the function level (DS 10101 F1) — let them propagate
    # to the resolver, which retries on the next poll.
    procs = {}
    try:
        entries = list(proc_dir.iterdir())
    except OSError:
        return out
    for entry in entries:
        if not entry.name.isdigit():
            continue
        try:
            stat = (entry / "stat").read_text(encoding="utf-8")
        except OSError:
            continue
        # stat format: pid (comm) state ppid ...
        # comm can contain spaces and parens; use rfind on ')'.
        close = stat.rfind(")")
        if close < 0:
            continue
        open_paren = stat.find("(")
        if open_paren < 0:
            continue
        comm = stat[open_paren + 1:close]
        rest = stat[close + 2:].split()
        if len(rest) < 2:
            continue
        try:
            pid = int(entry.name)
            ppid = int(rest[1])
        except ValueError:
            continue
        procs[pid] = (ppid, comm)
    # BFS descendants, depth-capped per DS 10101 F3 (same as the
    # Windows walker; symmetric implementation).
    frontier = [parent_pid]
    seen = {parent_pid}
    depth = 0
    while frontier and depth < _DESCENDANT_MAX_DEPTH:
        next_frontier = []
        for current in frontier:
            for pid, (ppid, name) in procs.items():
                if ppid == current and pid not in seen:
                    seen.add(pid)
                    out.append({"pid": pid, "name": name})
                    next_frontier.append(pid)
        frontier = next_frontier
        depth += 1
    return out


def _write_pid(clone_path, role, pid):
    """Write claude PID for harness monitoring. Atomic write."""
    pid_file = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
    pid_file.parent.mkdir(parents=True, exist_ok=True)
    tmp = pid_file.with_suffix(".tmp")
    tmp.write_text(str(pid), encoding="utf-8")
    tmp.replace(pid_file)


def _clear_pid(clone_path, role):
    """Remove PID file on exit."""
    pid_file = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
    try:
        pid_file.unlink(missing_ok=True)
    except OSError:
        pass


def main():
    if len(sys.argv) < 2:
        print("Usage: thin_launcher.py <role> [--force]", file=sys.stderr)
        return 1

    role = sys.argv[1]
    force = "--force" in sys.argv[2:]

    # Resolve clone path — CWD should be the clone root (set by harness/boot_remote)
    clone_path = os.getcwd()

    # Singleton enforcement (#8692): refuse to boot if another agent of the
    # same role is already running in this clone. Concurrent agents race on
    # shared state files (working-state.md, CLAUDE.md, .backlog-cache) and
    # produce divergent local commits. The harness already gates this via
    # boot_remote._needs_boot, but anyone invoking thin_launcher.py directly
    # (manual relaunch, scripts) bypasses that — so we re-check here. Use
    # --force only for recovery when you're certain the PID file is stale.
    existing_pid = _check_singleton(clone_path, role)
    if existing_pid is not None and not force:
        print(
            f"[thin-launcher] REFUSED: another '{role}' agent is already running "
            f"in {clone_path} (PID {existing_pid}). Stop it first, or pass --force "
            f"if you are certain the .claude-pid file is stale.",
            file=sys.stderr,
        )
        return 3

    # Set environment
    env = os.environ.copy()
    env["SQUIDSQUAD_ROLE"] = role

    # Read per-agent effort level from config (#5573)
    effort = _get_effort_level(role)
    print(f"[thin-launcher] Starting claude for {role} in {clone_path} (effort={effort})")

    # Suppress account-level MCP plugins so built-in deferred tools (Monitor)
    # are always available (#7630). --strict-mcp-config alone = no external MCP.
    # If mcp-agents.json exists, also pass --mcp-config for future per-agent servers.
    mcp_config = Path(clone_path) / ".squidsquad" / "mcp-agents.json"

    # Resolve claude executable. shutil.which honors PATHEXT, so it finds
    # .cmd/.ps1 shims from npm installs on Windows (which CreateProcessW
    # alone cannot resolve from a bare "claude" arg).
    claude_exe = shutil.which("claude")
    if claude_exe is None:
        print("[thin-launcher] ERROR: 'claude' not found on PATH", file=sys.stderr)
        return 1

    try:
        cmd = [claude_exe, "--strict-mcp-config"]
        if mcp_config.exists():
            cmd.extend(["--mcp-config", str(mcp_config)])
        cmd.extend([
            "--append-system-prompt", f"SQUIDSQUAD_ROLE={role}",
            "--name", f"squidsquad-{role}",
            "--effort", effort,
            "--dangerously-skip-permissions",
            # #9725: spawn prompt IS the /loop registration. The agent's first
            # turn registers the recurring schedule; subsequent cycles fire via
            # cron, not via a stalled-in-Step-1 inline cycle. See CONTEXT-9725.
            f"/loop {_get_interval()}m execute one Ralph Loop cycle",
        ])

        proc = subprocess.Popen(
            cmd,
            cwd=clone_path,
            env=env,
        )
    except FileNotFoundError:
        print(f"[thin-launcher] ERROR: failed to execute '{claude_exe}'", file=sys.stderr)
        return 1

    # Resolve the actual claude.exe descendant PID before recording (#10101).
    # If we launched through the npm cmd shim on Windows, proc.pid is the
    # cmd.exe wrapper, not claude.exe — recording the wrapper makes singleton
    # check fail as soon as the wrapper exits (which it does in seconds).
    # No-op on the non-shim path (Linux/macOS, or any Windows install that
    # exposes claude.exe directly on PATH).
    claude_pid = _resolve_claude_exe_pid(proc.pid, claude_exe)

    # Write PID for harness monitoring. If the write fails (disk full,
    # permission denied, antivirus locking the .tmp), warn and continue —
    # claude is already running and we still need to reach proc.wait()
    # below. Otherwise the exception would unwind past the wait, leaving
    # claude as an orphan child without a pid file for the harness (#8879).
    try:
        _write_pid(clone_path, role, claude_pid)
    except OSError as e:
        pid_path = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
        print(f"[thin-launcher] WARNING: could not write pid file "
              f"({pid_path}): {e}", file=sys.stderr)
    if claude_pid != proc.pid:
        print(f"[thin-launcher] claude PID: {claude_pid} "
              f"(wrapper {proc.pid} resolved via descendant walk #10101)")
    else:
        print(f"[thin-launcher] claude PID: {claude_pid}")

    # Wait for claude to exit — keeps terminal open
    try:
        exit_code = proc.wait()
    except KeyboardInterrupt:
        # Ctrl+C in terminal — let claude handle it
        try:
            exit_code = proc.wait(timeout=30)
        except subprocess.TimeoutExpired:
            proc.kill()
            exit_code = 1

    # Clean up PID file
    _clear_pid(clone_path, role)

    print(f"[thin-launcher] claude exited with code {exit_code}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
