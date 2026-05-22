"""Reap orphaned ``claude.exe`` Agent-tool subagents per CONTEXT-9688.md (#9688).

When a SquidSquad agent invokes the Agent tool, Claude Code spawns ``cmd.exe`` →
``claude.exe`` for the subagent. When the subagent finishes, ``cmd.exe`` exits but
Windows does NOT propagate the teardown to the ``claude.exe`` grandchild. Across a
long task with several subagent calls the orphans accumulate (~500MB RAM observed
in #9398/#9574 work).

Per CONTEXT-9688.md ``Three claude.exe populations``:

  1. **Protected agent** — ``ParentProcessId`` matches some role's ``.claude-pid``
     (which stores the cmd.exe PID, NOT the claude.exe PID — see ARCHITECTURE.md).
  2. **Live subagent** — parent is alive but does not match any ``.claude-pid``.
     Spawned by the agent's Agent tool; legitimately in flight.
  3. **Orphan** — parent is dead. Safe to terminate.

This module is invoked from the end of ``cycle_post.py`` AND from the start of
``boot_remote.py``. It is a near-no-op on POSIX — Unix process-group teardown
handles the subagent exit so there are essentially no orphans to reap (D6).

CONTEXT lock summary:

  - **D1**: live parent ⇒ never kill (orphans only).
  - **D2**: sweep globally. Filter by npm-install path so the user's own Claude
    Code IDE / CLI sessions outside SquidSquad are never touched.
  - **D3**: if ANY role's ``.claude-pid`` is missing or its cmd.exe is dead,
    skip the ENTIRE cleanup run. Rather miss orphans than kill the wrong
    process during a respawn race.
  - **D4**: append every decision to ``.squidsquad/diagnostics/orphan-cleanup.jsonl``
    as JSONL. Never comment on the tracker.
  - **D5**: always on; no config flag.
  - **D6**: cross-platform; POSIX runs and exits silently.
  - **D7**: mock-based unit tests; the 7 cases in ``tests/test_orphan_cleanup_9688.py``.
  - **D8**: see ``docs/ARCHITECTURE.md`` for the process-tree diagram.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUID_DIR = REPO_ROOT / ".squidsquad"
DIAGNOSTICS_LOG = SQUID_DIR / "diagnostics" / "orphan-cleanup.jsonl"

# CONTEXT D2: only consider claude.exe processes whose CommandLine references
# the npm-installed binary. The user's own Claude Code CLI invocations from
# unrelated paths (a different repo, the IDE) must not be killed. The npm
# install path varies by Windows user but always ends with this fragment.
_NPM_PATH_FRAGMENT = r"\node_modules\@anthropic-ai\claude-code\bin\claude.exe"


def _is_windows() -> bool:
    # sys.platform is a compile-time constant; platform.system() calls
    # platform.uname() which on Python 3.12 Windows triggers a WMI query
    # that can hang (#9903).
    return sys.platform == "win32"


# ---------------------------------------------------------------------------
# Process listing
# ---------------------------------------------------------------------------


def _list_claude_processes() -> list[dict]:
    """Return ``claude.exe`` processes as ``{pid, ppid, cmdline}`` dicts.

    Returns ``[]`` if PowerShell is unavailable or the query fails. Best-effort —
    we never raise on the cleanup tail of cycle_post.
    """
    if not _is_windows():
        return []
    query = (
        "Get-CimInstance Win32_Process -Filter \"Name = 'claude.exe'\" | "
        "Select-Object ProcessId,ParentProcessId,CommandLine | "
        "ConvertTo-Csv -NoTypeInformation"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", query],
            capture_output=True, text=True, check=False, timeout=15,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []

    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    if len(lines) < 2:
        return []

    out: list[dict] = []
    for line in lines[1:]:
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
    """Split a 3-column CSV row whose last field may contain commas + quotes.

    PowerShell ``ConvertTo-Csv`` quotes every field and escapes embedded ``"``
    as ``""`` per RFC 4180. The pid/ppid columns are integers and never carry
    quotes; the CommandLine column legitimately can (e.g. quoted paths with
    spaces). Strip outer quotes, scan for the first two ``","`` separators,
    then collapse ``""`` → ``"`` in the CommandLine to recover the raw cmdline.
    """
    s = line.strip()
    if not (s.startswith('"') and s.endswith('"')):
        return None
    s = s[1:-1]
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
    """Cross-platform PID liveness probe.

    Mirrors ``process_utils.is_process_alive`` but kept local to keep this
    module's import surface minimal at cycle_post tail.
    """
    if pid is None or pid <= 0:
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


# ---------------------------------------------------------------------------
# Protected-set resolution (CONTEXT D2 + D3)
# ---------------------------------------------------------------------------


def _role_pid_files():
    """Return ``{role: Path(.claude-pid)}`` for every configured role.

    Walks the project's ``.local-config`` via ``boot_remote._parse_local_config``
    so each role's pid file is resolved against ITS OWN clone — agents in
    SquidSquad commonly run as separate clones (one per role), and skill's
    clone has only ``skill/.claude-pid`` locally. Reading the right
    ``.claude-pid`` per role is critical: comparing claude.exe PIDs against
    the wrong pid file would either miss protection (kill the live agent)
    or always-skip (D3 fires every run because pid files appear "missing").

    Empty return = ``.local-config`` unavailable or unreadable; caller treats
    that the same as "any role missing" and skips the sweep per D3.
    """
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        import boot_remote
        clones = boot_remote._parse_local_config()
    except (ImportError, SystemExit, Exception):
        return {}
    out = {}
    for role, clone_path in clones.items():
        out[role] = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
    return out


def _resolve_protected_pids(role_pid_files, processes):
    """Resolve protected ``claude.exe`` PIDs for every role.

    Returns ``(protected_pids, skipped_role_logs)``. Per CONTEXT D3: if ANY
    role has a missing ``.claude-pid`` OR its cmd.exe is dead OR no claude.exe
    child is found for the cmd.exe, the caller MUST skip the entire sweep.
    The caller checks whether ``skipped_role_logs`` is empty.
    """
    protected = set()
    skipped = []
    if not role_pid_files:
        skipped.append({
            "role": "<any>", "reason": "no roles discoverable via .local-config",
            "decision": "skipped",
        })
        return protected, skipped
    for role, pid_file in role_pid_files.items():
        if not pid_file.exists():
            skipped.append({
                "role": role, "reason": "missing .claude-pid",
                "decision": "skipped",
            })
            continue
        try:
            cmd_pid = int(pid_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            skipped.append({
                "role": role, "reason": "unparseable .claude-pid",
                "decision": "skipped",
            })
            continue
        if not _is_pid_alive(cmd_pid):
            skipped.append({
                "role": role, "cmd_pid": cmd_pid,
                "reason": "cmd.exe in .claude-pid not alive",
                "decision": "skipped",
            })
            continue
        # Find the claude.exe child of this cmd.exe.
        children = [p for p in processes if p["ppid"] == cmd_pid]
        if len(children) != 1:
            skipped.append({
                "role": role, "cmd_pid": cmd_pid,
                "child_count": len(children),
                "reason": "expected exactly one claude.exe child of cmd.exe",
                "decision": "skipped",
            })
            continue
        protected.add(children[0]["pid"])
    return protected, skipped


# ---------------------------------------------------------------------------
# Classification + kill (CONTEXT D1 + D2)
# ---------------------------------------------------------------------------


def _matches_npm_install(cmdline):
    """True if ``cmdline`` references the npm-installed claude.exe binary.

    Per CONTEXT D2 + Out-of-Scope §7: this filter keeps the cleanup confined
    to SquidSquad-spawned subagents and never touches the user's own Claude
    Code IDE / CLI sessions running from a different path.
    """
    if not cmdline:
        return False
    return _NPM_PATH_FRAGMENT.lower() in cmdline.lower()


def _classify(proc, protected):
    """Return ``(decision, reason)`` for one process. Pure — no kills here."""
    pid, ppid, cmd = proc["pid"], proc["ppid"], proc["cmdline"]
    if not _matches_npm_install(cmd):
        return "kept", "out of scope (not npm-installed claude.exe)"
    if pid in protected:
        return "kept", "protected agent (claude.exe child of a role cmd.exe)"
    if _is_pid_alive(ppid):
        return "kept", "live subagent (parent still alive)"
    return "killed", "orphan (parent dead)"


def _pid_is_claude_exe(pid):
    """#9937: re-verify that ``pid`` still names a ``claude.exe`` process.

    Windows is free to recycle a PID for any executable as soon as the
    original process exits. The snapshot taken by
    ``_list_claude_processes()`` at sweep start can become stale by the
    time ``_kill(pid)`` fires — if the orphan died naturally in the
    interim and a new unrelated process inherited that PID, our
    ``taskkill /F`` would terminate the innocent.

    Re-querying via ``tasklist /FI "PID eq <pid>"`` is cheap (~30-80ms)
    and closes the race. POSIX doesn't have the same reuse pattern at
    the time scales involved (PIDs are reused much later in the LRU
    cycle), but we still re-check via ``/proc/<pid>/comm`` where
    available — defense in depth costs almost nothing here.

    Best-effort: any failure (tasklist missing, /proc unreadable)
    returns ``False`` (i.e., skip the kill). Killing the wrong process
    is worse than missing an orphan once — the orphan will reappear
    on the next sweep, an innocent kill cannot be undone.
    """
    if pid is None or pid <= 0:
        return False
    if _is_windows():
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True, text=True, check=False, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        if result.returncode != 0 or not result.stdout.strip():
            return False
        # tasklist CSV format: "Image Name","PID","Session Name",...
        # The first column is the executable name. Strip outer quotes
        # and lowercase-compare for safety (Windows is case-insensitive).
        line = result.stdout.splitlines()[0].strip()
        if not line.startswith('"'):
            return False
        # Image name is everything up to the first '","' separator.
        end = line.find('","')
        if end < 0:
            return False
        image = line[1:end].lower()
        return image == "claude.exe"
    # POSIX: read /proc/<pid>/comm. Limited to Linux; on macOS /proc
    # doesn't exist and we fall through to False (POSIX orphans are
    # rare per CONTEXT-9688 D6, so a few skipped kills on macOS is
    # acceptable).
    try:
        with open(f"/proc/{pid}/comm", "r", encoding="utf-8") as f:
            return f.read().strip() == "claude"
    except (OSError, ValueError):
        return False


def _kill(pid):
    """Best-effort taskkill. Returns True on apparent success.

    #9937: re-verifies the target is still a ``claude.exe`` via
    :func:`_pid_is_claude_exe` before issuing the kill, so a PID
    recycled to an unrelated process between snapshot and kill is
    NOT terminated. The check costs one extra ``tasklist`` call per
    orphan (~30-80ms); orphan counts are typically 1-3 per sweep so
    the added latency is trivial vs the safety it buys.
    """
    if pid <= 0:
        return False
    if not _pid_is_claude_exe(pid):
        # PID either gone (race won the harmless way — orphan already
        # exited) or recycled to a non-claude process. Skip.
        return False
    if _is_windows():
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


# ---------------------------------------------------------------------------
# Logging (CONTEXT D4)
# ---------------------------------------------------------------------------


def _log_decision(record):
    """Append one JSON object as a line to the diagnostics log.

    Append-only; best-effort. A write failure must not block the cleanup
    itself — cleanup ran, the audit trail is just missing this entry.
    """
    record = dict(record)
    record.setdefault("timestamp", time.time())
    try:
        DIAGNOSTICS_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DIAGNOSTICS_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, separators=(",", ":")) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def sweep(invoked_by="manual", dry_run=False):
    """Run one orphan-cleanup sweep. Returns a summary dict.

    Cross-platform — on POSIX this returns immediately with a zero summary
    (the orphan accumulation pattern is Windows-specific, see D6). Caller
    passes ``invoked_by`` for log attribution: typically ``"cycle_post:<role>"``
    or ``"boot_remote:<role>"``.
    """
    summary = {
        "invoked_by": invoked_by,
        "platform": sys.platform,
        "kept": [], "killed": [], "skipped_roles": [],
        "skipped_run": False,
    }

    if not _is_windows():
        _log_decision({
            "invoked_by": invoked_by, "decision": "skipped",
            "reason": "non-windows platform; nothing to sweep",
        })
        return summary

    processes = _list_claude_processes()
    if not processes:
        return summary

    role_pid_files = _role_pid_files()
    protected, skipped_roles = _resolve_protected_pids(role_pid_files, processes)
    summary["skipped_roles"] = skipped_roles

    if skipped_roles:
        # D3: any role failing to resolve aborts the entire sweep.
        for entry in skipped_roles:
            _log_decision({"invoked_by": invoked_by, **entry})
        _log_decision({
            "invoked_by": invoked_by, "decision": "skipped",
            "reason": (f"{len(skipped_roles)} role(s) failed to resolve "
                       "protected pid; aborting sweep per CONTEXT-9688 D3"),
        })
        summary["skipped_run"] = True
        return summary

    own_pid = os.getpid()
    for proc in processes:
        if proc["pid"] == own_pid:
            continue
        decision, reason = _classify(proc, protected)
        _log_decision({
            "invoked_by": invoked_by,
            "pid": proc["pid"], "parent_pid": proc["ppid"],
            "decision": decision, "reason": reason,
        })
        if decision == "killed":
            if dry_run:
                summary["killed"].append(proc["pid"])
            elif _kill(proc["pid"]):
                summary["killed"].append(proc["pid"])
            else:
                summary["kept"].append(proc["pid"])
                _log_decision({
                    "invoked_by": invoked_by, "pid": proc["pid"],
                    "decision": "kept", "reason": "taskkill returned non-zero",
                })
        else:
            summary["kept"].append(proc["pid"])
    return summary


def main():
    invoked_by = "manual"
    dry_run = False
    args = sys.argv[1:]
    if "--dry-run" in args:
        dry_run = True
        args = [a for a in args if a != "--dry-run"]
    if args:
        invoked_by = args[0]

    result = sweep(invoked_by=invoked_by, dry_run=dry_run)
    if result["skipped_run"]:
        print(f"[orphan-cleanup] sweep skipped: "
              f"{len(result['skipped_roles'])} role(s) unresolved")
        return 0
    killed, kept = result["killed"], result["kept"]
    if not killed and not kept:
        print(f"[orphan-cleanup] no claude.exe processes found "
              f"({result['platform']})")
        return 0
    action = "would kill" if dry_run else "killed"
    print(f"[orphan-cleanup] {action} {len(killed)} orphan(s): "
          f"{sorted(killed)} (kept {len(kept)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
