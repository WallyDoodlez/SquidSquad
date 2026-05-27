#!/usr/bin/env python3
"""Compare Popen(claude.cmd) vs Popen(resolved-claude.exe) process trees.

Feasibility check for docs/HARNESS-DIRECT-SPAWN.md §3.1: prove that
spawning the resolved claude.exe directly produces a process tree
where `Popen.pid` IS claude.exe, whereas spawning the .cmd shim
produces a process tree where `Popen.pid` is cmd.exe (or
short-lived) with claude.exe as a descendant.

If §3.1 holds, the descendant-walker (`_resolve_claude_exe_pid` +
`_win32_list_descendants` in thin_launcher.py, ~250 lines) can be
deleted: there's nothing to walk anymore because `Popen.pid` is
already what we want.

Run:
    python references/experiments/spawn_tree_test.py

Exits 0 if the demonstration is clean, non-zero otherwise.
"""

from __future__ import annotations

import ctypes
import shutil
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

# Import the resolver from the sibling file. The sys.path manipulation is
# fragile if these files are moved or run from a different cwd — catch the
# ImportError and give a clear message instead of letting the traceback fly.
sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    from resolve_claude import resolve_claude  # noqa: E402
except ImportError as e:
    print(f"FAIL: cannot import resolve_claude from {Path(__file__).parent}: {e}",
          file=sys.stderr)
    print("Ensure both files live in the same directory and the script "
          "is run with that directory accessible to Python.",
          file=sys.stderr)
    sys.exit(7)


# ---------- toolhelp32 process snapshot (Windows only) ----------

class _PROCESSENTRY32(ctypes.Structure):
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


def _snapshot_processes() -> dict[int, tuple[int, str]]:
    """Return {pid: (parent_pid, exe_name)} for all running processes."""
    TH32CS_SNAPPROCESS = 0x00000002
    INVALID_HANDLE = -1
    kernel32 = ctypes.windll.kernel32
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == INVALID_HANDLE:
        return {}
    try:
        entry = _PROCESSENTRY32()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32)
        procs: dict[int, tuple[int, str]] = {}
        if not kernel32.Process32First(snap, ctypes.byref(entry)):
            return {}
        while True:
            procs[entry.th32ProcessID] = (
                entry.th32ParentProcessID,
                entry.szExeFile.decode("utf-8", errors="replace"),
            )
            if not kernel32.Process32Next(snap, ctypes.byref(entry)):
                break
        return procs
    finally:
        kernel32.CloseHandle(snap)


def _descendants_of(procs: dict[int, tuple[int, str]], parent: int,
                    max_depth: int = 6) -> list[tuple[int, str, int]]:
    """BFS descendants. Returns list of (pid, exe_name, depth)."""
    out: list[tuple[int, str, int]] = []
    frontier = [parent]
    seen = {parent}
    depth = 0
    while frontier and depth < max_depth:
        next_frontier = []
        depth += 1
        for ppid in frontier:
            for pid, (this_parent, name) in procs.items():
                if this_parent == ppid and pid not in seen:
                    seen.add(pid)
                    out.append((pid, name, depth))
                    next_frontier.append(pid)
        frontier = next_frontier
    return out


# ---------- the actual experiment ----------

def _spawn_and_snapshot(label: str, argv: list[str]) -> dict:
    """Popen the given argv, immediately snapshot process tree, report.

    Uses `--help` (not `--version`) so the process produces enough stdout
    to stay alive past the snapshot window. `--version` exits in <100ms
    on modern hardware, which can race the first toolhelp32 sample.

    Note on DETACHED_PROCESS + conhost: passing DETACHED_PROCESS does
    suppress conhost for the direct child (Test A's claude.exe). But
    when the direct child is itself a console host (Test B's cmd.exe
    shim), it spawns its own grandchild console — so we DO observe a
    `conhost.exe` descendant in Test B. That asymmetry is informative,
    not a bug — it directly mirrors why thin_launcher needed the
    descendant walker in the first place.
    """
    print(f"\n=== {label} ===")
    print(f"  argv: {argv}")

    # Use creationflags to detach so the test script doesn't inherit
    # the wrapper console (would clutter output).
    DETACHED_PROCESS = 0x00000008
    proc = subprocess.Popen(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=DETACHED_PROCESS,
    )
    spawn_pid = proc.pid
    print(f"  Popen.pid = {spawn_pid}")

    # Snapshot multiple times — first one may catch the spawn before
    # claude.exe has appeared as a descendant.
    found_at = None
    descendants_seen: list = []
    self_seen: tuple[int, str] | None = None
    for attempt in range(20):  # up to ~400ms total
        time.sleep(0.02)
        procs = _snapshot_processes()
        if spawn_pid in procs:
            self_seen = (procs[spawn_pid][0], procs[spawn_pid][1])
            descendants_seen = _descendants_of(procs, spawn_pid)
            found_at = attempt
            # If we have any descendants, we've got enough data
            if descendants_seen or attempt > 3:
                break
        elif self_seen is not None:
            # We saw it earlier and now it's gone; that's fine
            break

    # Let the process complete and capture output
    try:
        out, err = proc.communicate(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()

    if self_seen is None:
        print(f"  ** WARNING: spawn pid {spawn_pid} never appeared in snapshots "
              f"(may have exited before first sample)")
        self_exe = "<not captured>"
        parent_pid = -1
    else:
        parent_pid, self_exe = self_seen
        print(f"  spawn process: pid={spawn_pid}, exe={self_exe}, parent={parent_pid}")

    print(f"  found at snapshot attempt: {found_at}")
    print(f"  descendants of Popen.pid:")
    if descendants_seen:
        for pid, name, depth in descendants_seen:
            indent = "    " + "  " * depth
            print(f"{indent}pid={pid}, exe={name}, depth={depth}")
    else:
        print("    (none captured)")

    flag = argv[-1] if argv else "?"
    print(f"  {flag} stdout: {out.decode('utf-8', 'replace').strip()[:120]!r}")
    print(f"  exit code: {proc.returncode}")

    return {
        "label": label,
        "spawn_pid": spawn_pid,
        "self_exe": self_exe,
        "descendants": descendants_seen,
        "is_claude_directly": "claude.exe" in self_exe.lower(),
        "has_claude_descendant": any("claude.exe" in n.lower() for _, n, _ in descendants_seen),
    }


def main() -> int:
    if sys.platform != "win32":
        print("This experiment is Windows-specific (toolhelp32). "
              "Equivalent on POSIX would use /proc.")
        return 0

    # Locate both paths
    shim_path = Path(shutil.which("claude") or "")
    if not shim_path.exists():
        print(f"FAIL: shim claude.cmd not found on PATH")
        return 1

    real_exe, _, _ = resolve_claude()
    print(f"shim path: {shim_path}")
    print(f"resolved : {real_exe}")

    # Test B: spawn via the shim (what subprocess.Popen does today
    # if you give it `shutil.which('claude')`). Use --help: longer
    # stdout than --version, gives the snapshot loop more time.
    test_b = _spawn_and_snapshot("Test B: Popen(claude.cmd) — CURRENT BEHAVIOR",
                                  [str(shim_path), "--help"])

    # Test A: spawn the resolved .exe directly (what §3.1 proposes)
    test_a = _spawn_and_snapshot("Test A: Popen(claude.exe) — PROPOSED",
                                  [str(real_exe), "--help"])

    # Verdict
    print("\n=== Verdict ===")
    print(f"Test B (shim):  Popen.pid was {test_b['self_exe']}  "
          f"{'(claude.exe descendant: ' + str(test_b['has_claude_descendant']) + ')'}")
    print(f"Test A (direct): Popen.pid was {test_a['self_exe']}")

    if test_a["is_claude_directly"] and not test_b["is_claude_directly"]:
        print("\n[OK] §3.1 demonstrated: direct spawn gives Popen.pid=claude.exe,")
        print("     shim spawn gives Popen.pid=cmd.exe (or similar wrapper).")
        print("     The descendant-walker in thin_launcher.py becomes unnecessary")
        print("     under the direct-spawn path.")
        return 0
    elif test_a["is_claude_directly"] and test_b["is_claude_directly"]:
        print("\n[INCONCLUSIVE] Both paths produced Popen.pid=claude.exe directly.")
        print("     The shim's cmd.exe may have already exec'd into claude before")
        print("     the first snapshot. Re-run, or trust Test A as proof.")
        print("     (Non-zero exit so CI does NOT treat this as success.)")
        return 3
    else:
        print("\n[UNEXPECTED] Direct spawn did NOT give claude.exe as Popen.pid.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
