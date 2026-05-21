"""Reap orphaned ``claude.exe`` processes left behind by Agent-tool subagents (#9688).

Windows-specific failure mode: when a SquidSquad agent invokes the Agent tool,
Claude Code spawns ``cmd.exe`` → ``claude.exe`` to run the subagent. When the
subagent finishes, the ``cmd.exe`` exits but Windows does not propagate the
teardown to the ``claude.exe`` grandchild (no Unix-style process-group
signalling). Across a long task with several Agent-tool calls (DeepSeek
reviews, comprehension runs, exploratory subagents) ~7 orphans accumulated
during the #9398/#9574 work and consumed ~500MB RAM + file handles.

This module is intended to be invoked from the end of ``cycle_post.py``. It is
also safe to invoke manually. It is a **no-op on POSIX** — Unix process-group
teardown handles the subagent exit, so there are no orphans to reap.

The cleanup logic deliberately keeps three protections:

1. **Self-protection** — never kill the live agent. The live PID is read from
   ``.squidsquad/<role>/.claude-pid`` (the harness's sole liveness signal,
   per thin_launcher and harness contract). The agent's parent chain
   ALWAYS includes that PID directly or indirectly.
2. **Clone-scoped** — only kill ``claude.exe`` processes whose command line
   references the current clone path. Other clones on the same machine are
   left alone.
3. **Parent-dead** — only kill processes whose parent PID no longer exists.
   A subagent with a live parent is still doing useful work; killing it
   would interrupt a real Agent-tool invocation mid-flight.

The detection uses ``Get-CimInstance Win32_Process`` (the same query PM used
in the #9688 reproduction recipe) rather than ``tasklist`` because tasklist
does not expose parent PIDs.
"""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUID_DIR = REPO_ROOT / ".squidsquad"

# WMI / CIM query that returns the four fields cleanup needs. Output format:
# one record per process as CSV, header on the first line. Reading the
# CommandLine field requires ``Get-CimInstance Win32_Process``; ``tasklist``
# does not surface it.
_PS_QUERY = (
    "Get-CimInstance Win32_Process -Filter \"Name = 'claude.exe'\" | "
    "Select-Object ProcessId,ParentProcessId,CommandLine | "
    "ConvertTo-Csv -NoTypeInformation"
)


def _is_windows() -> bool:
    return platform.system().lower() == "windows"


def _read_live_pid(role: str) -> int | None:
    """Return the live agent PID from ``.claude-pid`` or ``None`` if absent.

    A missing or unparseable pid file is treated as "no protected pid" — the
    cleanup still proceeds but with one less safety check. The other two
    protections (clone-scoped path match, parent-dead) still apply, so this
    failure mode does not threaten the live agent unless the pid file is
    missing AND a clone-matching process has a dead parent (which is the
    exact orphan scenario this script targets).
    """
    pid_file = SQUID_DIR / role / ".claude-pid"
    if not pid_file.exists():
        return None
    try:
        return int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None


def _list_claude_processes() -> list[dict]:
    """Return ``claude.exe`` processes as ``{pid, ppid, cmdline}`` dicts.

    Returns ``[]`` if PowerShell is unavailable or the query fails for any
    reason. We deliberately do not raise — orphan cleanup is best-effort,
    and a noisy crash on cycle_post tail would mask the actual cycle work.
    """
    if not _is_windows():
        return []
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", _PS_QUERY],
            capture_output=True, text=True, check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if len(lines) < 2:
        # Just the CSV header, no rows.
        return []

    # Skip the header. We hand-parse CSV instead of using the csv module
    # so PowerShell-emitted lines with embedded commas inside the
    # CommandLine field don't break us — Get-CimInstance quotes the
    # CommandLine, so a tolerant 3-field split survives commas in args.
    out: list[dict] = []
    for line in lines[1:]:
        # CSV: "pid","ppid","cmdline" (cmdline may itself contain commas).
        parts = _split_csv_three(line)
        if parts is None:
            continue
        pid_s, ppid_s, cmd = parts
        try:
            pid = int(pid_s)
            ppid = int(ppid_s)
        except ValueError:
            continue
        out.append({"pid": pid, "ppid": ppid, "cmdline": cmd})
    return out


def _split_csv_three(line: str) -> tuple[str, str, str] | None:
    """Split a 3-column CSV row that may have commas inside the last field.

    PowerShell ``ConvertTo-Csv`` quotes every field, so a strict left-to-right
    scan for the first two unescaped ``","`` separators is enough — anything
    after the second one is the CommandLine column, commas and all.

    PowerShell also escapes a literal ``"`` inside a field by doubling it
    (``""``) per RFC 4180. The pid / ppid columns are integers and never
    contain quotes, but the CommandLine column legitimately can — e.g.
    ``claude.exe --config "C:\\path with space"`` becomes
    ``"...,""C:\\path with space""..."`` in CSV. After extracting the
    raw CommandLine substring we collapse ``""`` back to ``"`` so callers
    get the original argv-ish string.
    """
    s = line.strip()
    if not (s.startswith('"') and s.endswith('"')):
        return None
    s = s[1:-1]  # strip outer quotes
    sep = '","'
    first = s.find(sep)
    if first < 0:
        return None
    second = s.find(sep, first + len(sep))
    if second < 0:
        return None
    pid_s = s[:first]
    ppid_s = s[first + len(sep):second]
    cmd = s[second + len(sep):].replace('""', '"')
    return pid_s, ppid_s, cmd


def _is_pid_alive(pid: int) -> bool:
    """Cross-platform PID liveness check.

    Mirrors ``process_utils.is_process_alive`` but kept local so this module
    has zero project imports — orphan cleanup runs at the tail of cycle_post
    where extra import surface is least welcome (the cycle is already trying
    to wrap up).
    """
    if pid <= 0:
        return False
    if _is_windows():
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, check=False, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return str(pid) in result.stdout
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def _matches_clone(cmdline: str, clone_path: Path) -> bool:
    """True if ``cmdline`` references ``clone_path`` (this repo).

    Path match is **boundary-aware**: a plain substring test would
    false-positive sibling clones whose path is a superset of this one
    (e.g., this clone ``D:\\Dev\\SquidSquad-2`` would match a command
    line referencing ``D:\\Dev\\SquidSquad-2-other``, and orphan cleanup
    would happily kill the sibling's claude.exe). Reject that class by
    requiring the next character after the clone path to be either a
    path separator, a quote, or end-of-string — anything that signals
    the path ended HERE rather than continuing into a different
    directory name.
    """
    if not cmdline:
        return False
    needle = str(clone_path).lower()
    haystack = cmdline.lower()
    idx = 0
    while True:
        idx = haystack.find(needle, idx)
        if idx < 0:
            return False
        after = idx + len(needle)
        # End-of-string, path separator, or quote = legitimate match.
        # Anything else = the path continues (sibling clone) and is a
        # false positive we must reject.
        if after == len(haystack) or haystack[after] in ('\\', '/', '"', "'", ' '):
            return True
        idx = after


def find_orphans(role: str, clone_path: Path | None = None,
                 live_pid: int | None = None) -> list[dict]:
    """Return the list of orphan ``claude.exe`` processes safe to kill.

    Parameters are injectable for testing — defaults use this clone's
    real ``.claude-pid`` and ``REPO_ROOT``.
    """
    if not _is_windows():
        return []
    if clone_path is None:
        clone_path = REPO_ROOT
    if live_pid is None:
        live_pid = _read_live_pid(role)

    processes = _list_claude_processes()
    if not processes:
        return []

    # Build a set of every PID we can see so the "parent dead" check is
    # cheap. We then ALSO fall back to ``_is_pid_alive`` for parents not
    # in the snapshot, because the parent of an orphan claude.exe is
    # usually a ``cmd.exe`` — not a ``claude.exe`` — and won't appear
    # in the Name='claude.exe' query result.
    live_claude_pids = {p["pid"] for p in processes}

    own_pid = os.getpid()
    orphans: list[dict] = []
    for proc in processes:
        pid, ppid, cmd = proc["pid"], proc["ppid"], proc["cmdline"]

        # Self-protect: never kill the live agent or ourselves.
        if live_pid is not None and pid == live_pid:
            continue
        if pid == own_pid:
            continue

        # Clone-scoped: only touch processes that are clearly from this clone.
        if not _matches_clone(cmd, clone_path):
            continue

        # Parent-dead test: parent isn't another claude.exe we just listed,
        # AND a direct liveness probe says the PID is gone. Both conditions
        # required — a parent that's a *live* cmd.exe (i.e. an Agent-tool
        # invocation still in flight) would pass the first check but fail
        # the second, and we should leave it alone.
        parent_in_snapshot = ppid in live_claude_pids
        if parent_in_snapshot:
            continue
        if _is_pid_alive(ppid):
            continue

        orphans.append(proc)
    return orphans


def kill_orphan(pid: int) -> bool:
    """Best-effort kill of a single PID. Returns True on apparent success."""
    if pid <= 0:
        return False
    if _is_windows():
        # /F = force, /PID = target, no /T because we already pruned the
        # tree by listing all claude.exe processes — killing children
        # individually keeps the kill scoped.
        try:
            result = subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                capture_output=True, text=True, check=False, timeout=10,
            )
            return result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False
    try:
        os.kill(pid, 9)
        return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


def cleanup(role: str, dry_run: bool = False) -> dict:
    """Find orphans for ``role`` and (unless dry-run) kill them.

    Returns a summary dict with ``killed`` (list of PIDs), ``skipped``
    (list of PIDs that were detected but refused the kill), and
    ``platform`` (the OS, for caller logging).
    """
    found = find_orphans(role)
    summary = {
        "platform": platform.system().lower(),
        "found": [p["pid"] for p in found],
        "killed": [],
        "skipped": [],
    }
    if dry_run or not found:
        return summary
    for proc in found:
        if kill_orphan(proc["pid"]):
            summary["killed"].append(proc["pid"])
        else:
            summary["skipped"].append(proc["pid"])
    return summary


def main():
    if len(sys.argv) < 2:
        print("Usage: orphan_cleanup.py <role> [--dry-run]", file=sys.stderr)
        return 1
    role = sys.argv[1]
    dry_run = "--dry-run" in sys.argv[2:]
    result = cleanup(role, dry_run=dry_run)
    found, killed, skipped = result["found"], result["killed"], result["skipped"]
    if not found:
        print(f"[orphan-cleanup] no orphans for {role} on {result['platform']}")
        return 0
    action = "would kill" if dry_run else "killed"
    print(f"[orphan-cleanup] {role}: found {len(found)} orphan(s) "
          f"({sorted(found)}); {action} {sorted(killed)}; "
          f"skipped {sorted(skipped)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
