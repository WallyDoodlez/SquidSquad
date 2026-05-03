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


def reboot(role, timeout=DEFAULT_TIMEOUT, force=False):
    """Reboot an agent safely. Reboot == ensure running.

    Architecture: kill the claude subprocess (.claude-pid), NOT the wrapper
    (.pid). The wrapper stays alive, detects claude exit, reads .restart
    sentinel, and respawns claude automatically.
    """
    clone_path = _get_clone_path(role)
    squid = clone_path / ".squidsquad"
    pid_file = squid / role / ".pid"
    restart_file = squid / role / ".restart"
    stop_file = squid / role / ".stop"

    # Check .stop sentinel first — do not respawn stopped agents
    if stop_file.exists():
        print(f"{role}: explicitly stopped (.stop sentinel) — not respawning")
        return 0

    # Check if wrapper is running
    wrapper_pid = None
    wrapper_alive = False
    if pid_file.exists():
        try:
            wrapper_pid = int(pid_file.read_text(encoding="utf-8").strip())
            wrapper_alive = _is_process_alive(wrapper_pid)
        except (ValueError, OSError):
            pass

    # Wrapper not running → boot fresh
    if not wrapper_alive:
        reason = "no PID file" if not pid_file.exists() else f"wrapper PID {wrapper_pid} dead"
        print(f"{role}: not running ({reason}) — booting...")
        success, msg = _spawn_wrapper(role, clone_path)
        if success:
            print(f"{role}: booted ({msg})")
        else:
            print(f"{role}: boot failed — {msg}", file=sys.stderr)
            return 1
        return 0

    # Wrapper is alive — kill the claude subprocess, let wrapper respawn
    claude_pid, claude_alive = _read_claude_pid(clone_path, role)

    if not claude_alive:
        if force:
            # Force mode: kill the wrapper and respawn fresh — sentinel approach
            # won't work if wrapper is stuck or not checking sentinels
            print(f"{role}: wrapper alive but claude not running"
                  f" — force-killing wrapper PID {wrapper_pid}")
            _kill_process(wrapper_pid)
            for _ in range(10):
                if not _is_process_alive(wrapper_pid):
                    break
                time.sleep(0.5)
            if _is_process_alive(wrapper_pid):
                print(f"{role}: WARNING — wrapper PID {wrapper_pid}"
                      " still alive after kill", file=sys.stderr)
                return 1
            # Clean up stale PID files so _spawn_wrapper doesn't reject
            for f in [pid_file, squid / role / ".claude-pid"]:
                try:
                    f.unlink()
                except OSError:
                    pass
            try:
                restart_file.unlink()
            except OSError:
                pass
            print(f"{role}: wrapper killed — respawning...")
            success, msg = _spawn_wrapper(role, clone_path)
            if success:
                print(f"{role}: respawned ({msg})")
            else:
                print(f"{role}: respawn failed — {msg}", file=sys.stderr)
                return 1
            return 0
        # Non-force: write sentinel so wrapper respawns on its next check
        restart_file.write_text(
            "reboot requested by reboot_agent.py", encoding="utf-8")
        print(f"{role}: wrapper alive but claude not running"
              " — restart sentinel written")
        return 0

    # Write restart sentinel BEFORE killing so wrapper sees it on claude exit
    restart_file.write_text("reboot requested by reboot_agent.py", encoding="utf-8")

    if force:
        _kill_process(claude_pid)
        for _ in range(10):
            if not _is_process_alive(claude_pid):
                break
            time.sleep(0.5)
        if _is_process_alive(claude_pid):
            print(f"{role}: WARNING — claude PID {claude_pid} still alive after kill",
                  file=sys.stderr)
        else:
            print(f"{role}: killed claude PID {claude_pid} — wrapper will respawn")
        return 0

    # Wait for idle, then kill claude subprocess
    elapsed = 0
    while elapsed < timeout:
        state = _read_current_state(clone_path, role)
        if state.startswith("idle"):
            _kill_process(claude_pid)
            for _ in range(10):
                if not _is_process_alive(claude_pid):
                    break
                time.sleep(0.5)
            if _is_process_alive(claude_pid):
                print(f"{role}: WARNING — claude PID {claude_pid} still alive after kill",
                      file=sys.stderr)
            else:
                print(f"{role}: went idle after {elapsed}s, killed claude PID {claude_pid}"
                      " — wrapper will respawn")
            return 0
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Timeout — clean up sentinel, do NOT kill
    try:
        restart_file.unlink()
    except OSError:
        pass
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
        # Get all agent roles from config.md via boot_remote (includes PM)
        agents = ["pm"] + boot_remote._get_all_roles()

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
