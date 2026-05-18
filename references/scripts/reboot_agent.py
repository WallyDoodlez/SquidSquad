#!/usr/bin/env python3
"""SquidSquad reboot_agent — safe agent restart via sentinel.

Reboot == ensure running. If agent is alive, restart it safely. If agent
is dead, boot it. Uses boot_remote spawn logic for all respawns, ensuring
a single unified lifecycle path.

Usage:
    python references/scripts/reboot_agent.py <role>
    python references/scripts/reboot_agent.py skill
    python references/scripts/reboot_agent.py --all
    python references/scripts/reboot_agent.py skill --timeout 300
    python references/scripts/reboot_agent.py skill --force

Exit codes:
    0 — reboot/boot completed successfully
    1 — timeout (agent busy, sentinel cleaned up, no spawn)
    2 — usage error
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUID_DIR = REPO_ROOT / ".squidsquad"

DEFAULT_TIMEOUT = 300  # 5 minutes
POLL_INTERVAL = 2  # seconds

# Import boot_remote for unified clone-path resolution and spawn logic
sys.path.insert(0, str(SCRIPT_DIR))
import boot_remote


def _get_clone_path(role):
    """Get the clone path for a role. Uses boot_remote's unified resolution."""
    return boot_remote._get_clone_path(role)


def _is_process_alive(pid):
    """Check if a process is alive."""
    return boot_remote._is_process_alive(pid)


def _kill_process(pid):
    """Kill a process."""
    if sys.platform == "win32":
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], check=False,
                       capture_output=True)
    else:
        os.kill(pid, signal.SIGINT)


def _read_current_state(clone_path, role):
    """Read the agent's current-state file."""
    state_file = clone_path / ".squidsquad" / role / "current-state"
    try:
        return state_file.read_text(encoding="utf-8").strip()
    except (FileNotFoundError, OSError):
        return ""


def _spawn_wrapper(role, clone_path):
    """Spawn agent via boot_remote.boot_agent() (#5344).

    Delegates to boot_remote which prefers thin launcher (#4966) and
    falls back to legacy wrapper scripts. Returns (success, message).
    """
    result = boot_remote.boot_agent(role)
    return result["success"], result["message"]


def _read_claude_pid(clone_path, role):
    """Read the claude subprocess PID from .claude-pid.

    Returns (pid, alive) tuple. pid is None if file missing or unreadable.
    """
    claude_pid_file = clone_path / ".squidsquad" / role / ".claude-pid"
    if not claude_pid_file.exists():
        return None, False
    try:
        pid = int(claude_pid_file.read_text(encoding="utf-8").strip())
        return pid, _is_process_alive(pid)
    except (ValueError, OSError):
        return None, False


def _kill_and_respawn(role, clone_path, pid, pid_label):
    """Kill a process and respawn the agent via boot_remote (#6406)."""
    squid = clone_path / ".squidsquad"
    _kill_process(pid)
    for _ in range(10):
        if not _is_process_alive(pid):
            break
        time.sleep(0.5)
    if _is_process_alive(pid):
        print(f"{role}: WARNING — {pid_label} PID {pid} still alive after kill",
              file=sys.stderr)
        return 1
    # Clean up stale PID files
    for f in [squid / role / ".pid", squid / role / ".claude-pid"]:
        try:
            f.unlink()
        except OSError:
            pass
    print(f"{role}: {pid_label} killed — respawning...")
    success, msg = _spawn_wrapper(role, clone_path)
    if success:
        print(f"{role}: respawned ({msg})")
    else:
        print(f"{role}: respawn failed — {msg}", file=sys.stderr)
        return 1
    return 0


def reboot(role, timeout=DEFAULT_TIMEOUT, force=False):
    """Reboot an agent safely. Reboot == ensure running.

    Architecture (#6406): kill the process and respawn via boot_remote.
    thin_launcher.py does not watch sentinel files — always use kill+respawn.
    The --force flag controls immediate kill vs wait-for-idle.
    """
    clone_path = Path(_get_clone_path(role))
    squid = clone_path / ".squidsquad"
    pid_file = squid / role / ".pid"

    # #4792: previously checked `.stop` sentinel here to decline reboots of
    # explicitly-stopped agents. That check now lives in harness state
    # (intent=stopping/stopped). reboot_agent.py is a local utility and does
    # not coordinate with harness intent — operators should use the harness
    # API (POST /agents/<role>/stop) to stop, then reboot_agent will succeed
    # only when intent is back to running (next /start or /restart resets it).

    # Check if launcher is running
    launcher_pid = None
    launcher_alive = False
    if pid_file.exists():
        try:
            launcher_pid = int(pid_file.read_text(encoding="utf-8").strip())
            launcher_alive = _is_process_alive(launcher_pid)
        except (ValueError, OSError):
            pass

    # Launcher not running → boot fresh
    if not launcher_alive:
        reason = "no PID file" if not pid_file.exists() else f"launcher PID {launcher_pid} dead"
        print(f"{role}: not running ({reason}) — booting...")
        success, msg = _spawn_wrapper(role, clone_path)
        if success:
            print(f"{role}: booted ({msg})")
        else:
            print(f"{role}: boot failed — {msg}", file=sys.stderr)
            return 1
        return 0

    # Launcher is alive — kill and respawn
    claude_pid, claude_alive = _read_claude_pid(clone_path, role)

    if not claude_alive:
        # Claude not running but launcher is — kill launcher and respawn
        return _kill_and_respawn(role, clone_path, launcher_pid, "launcher")

    if force:
        # Immediate kill — don't wait for idle
        return _kill_and_respawn(role, clone_path, claude_pid, "claude")

    # Wait for idle, then kill and respawn
    elapsed = 0
    while elapsed < timeout:
        state = _read_current_state(clone_path, role)
        if state.startswith("idle"):
            return _kill_and_respawn(role, clone_path, claude_pid, "claude")
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Timeout — agent is busy, do NOT kill
    print(f"{role}: timeout waiting for idle ({timeout}s) — agent is busy, no kill",
          file=sys.stderr)
    return 1


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Safely reboot a SquidSquad agent")
    parser.add_argument("role", nargs="?", help="Agent role to reboot")
    parser.add_argument("--all", action="store_true", help="Reboot all agents")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                        help=f"Timeout in seconds (default: {DEFAULT_TIMEOUT})")
    parser.add_argument("--force", action="store_true", help="Skip idle wait, kill immediately")

    args = parser.parse_args()

    if args.all:
        # Get all agent roles from config.md via boot_remote, ensure PM included
        roles = set(boot_remote._get_all_roles())
        roles.add("pm")  # PM always rebooted — config may omit the explicit line
        agents = sorted(roles)

        exit_code = 0
        for role in agents:
            rc = reboot(role, timeout=args.timeout, force=args.force)
            if rc != 0:
                exit_code = rc
        return exit_code

    if not args.role:
        parser.print_usage()
        return 2

    return reboot(args.role, timeout=args.timeout, force=args.force)


if __name__ == "__main__":
    sys.exit(main())
