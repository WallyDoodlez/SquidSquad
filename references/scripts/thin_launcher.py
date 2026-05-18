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
import platform
import shutil
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
VALID_EFFORT_LEVELS = {"low", "medium", "high", "max"}


def _get_effort_level(role):
    """Read per-agent effort level from config.md. Falls back to 'high'."""
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from config import get_field
        level = (get_field(f"effort-{role}") or "high").strip().lower()
        return level if level in VALID_EFFORT_LEVELS else "high"
    except (Exception, SystemExit):
        return "high"


def _is_process_alive(pid):
    """Check if a process with the given PID is still running. Cross-platform.

    Canonical version lives in ``process_utils.is_process_alive`` — kept
    local here to avoid importing extra modules at launcher startup
    (#8891). If you change the semantics there, mirror the change here.
    """
    if pid is None or pid <= 0:
        return False
    try:
        if platform.system().lower() == "windows":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True, text=True, check=False,
            )
            return str(pid) in result.stdout
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError, PermissionError):
        return False


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
            "Boot. Begin your first Ralph Loop cycle now.",
        ])

        proc = subprocess.Popen(
            cmd,
            cwd=clone_path,
            env=env,
        )
    except FileNotFoundError:
        print(f"[thin-launcher] ERROR: failed to execute '{claude_exe}'", file=sys.stderr)
        return 1

    # Write PID for harness monitoring. If the write fails (disk full,
    # permission denied, antivirus locking the .tmp), warn and continue —
    # claude is already running and we still need to reach proc.wait()
    # below. Otherwise the exception would unwind past the wait, leaving
    # claude as an orphan child without a pid file for the harness (#8879).
    try:
        _write_pid(clone_path, role, proc.pid)
    except OSError as e:
        pid_path = Path(clone_path) / ".squidsquad" / role / ".claude-pid"
        print(f"[thin-launcher] WARNING: could not write pid file "
              f"({pid_path}): {e}", file=sys.stderr)
    print(f"[thin-launcher] claude PID: {proc.pid}")

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
