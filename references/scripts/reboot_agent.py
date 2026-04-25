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
    """Spawn a new wrapper for a role using boot_remote logic.

    Returns (success, message).
    """
    boot_script, script_type = boot_remote._find_boot_script(clone_path, role)
    if boot_script is None:
        return False, (
            f"no boot script found at {clone_path}/.squidsquad/start-{role}.[sh|ps1]\n"
            f"Manual boot: cd {clone_path} && claude -p .squidsquad/{role}/CLAUDE.md"
        )

    # Verify PID is truly dead before spawning (double-start prevention)
    pid_file = Path(clone_path) / ".squidsquad" / role / ".pid"
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            if _is_process_alive(pid):
                return False, f"PID {pid} still alive — cannot spawn (would double-start)"
        except (ValueError, OSError):
            pass

    return boot_remote._spawn_terminal(clone_path, role, boot_script, script_type)


def reboot(role, timeout=DEFAULT_TIMEOUT, force=False):
    """Reboot an agent safely. Reboot == ensure running."""
    clone_path = _get_clone_path(role)
    squid = clone_path / ".squidsquad"
    pid_file = squid / role / ".pid"
    restart_file = squid / role / ".restart"
    stop_file = squid / role / ".stop"

    # Check .stop sentinel first — do not respawn stopped agents
    if stop_file.exists():
        print(f"{role}: explicitly stopped (.stop sentinel) — not respawning")
        return 0

    # Check if agent is running
    has_pid = pid_file.exists()
    pid = None
    pid_alive = False

    if has_pid:
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
            pid_alive = _is_process_alive(pid)
        except (ValueError, OSError):
            pass

    # Agent not running (no PID file, or PID is dead) → boot it
    if not pid_alive:
        reason = "no PID file" if not has_pid else f"PID {pid} dead"
        print(f"{role}: not running ({reason}) — booting...")
        success, msg = _spawn_wrapper(role, clone_path)
        if success:
            print(f"{role}: booted ({msg})")
        else:
            print(f"{role}: boot failed — {msg}", file=sys.stderr)
            return 1
        return 0

    # Agent is running — restart it
    # Write restart sentinel
    restart_file.write_text("reboot requested by reboot_agent.py", encoding="utf-8")

    if force:
        _kill_process(pid)
        # Wait briefly for process to die
        for _ in range(10):
            if not _is_process_alive(pid):
                break
            time.sleep(0.5)
        print(f"{role}: force killed (PID {pid}) — respawning...")
        success, msg = _spawn_wrapper(role, clone_path)
        if success:
            print(f"{role}: respawned ({msg})")
        else:
            print(f"{role}: respawn failed — {msg}", file=sys.stderr)
            return 1
        return 0

    # Wait for idle
    elapsed = 0
    while elapsed < timeout:
        state = _read_current_state(clone_path, role)
        if state.startswith("idle"):
            _kill_process(pid)
            # Wait briefly for process to die
            for _ in range(10):
                if not _is_process_alive(pid):
                    break
                time.sleep(0.5)
            print(f"{role}: went idle after {elapsed}s, killed PID {pid} — respawning...")
            success, msg = _spawn_wrapper(role, clone_path)
            if success:
                print(f"{role}: respawned ({msg})")
            else:
                print(f"{role}: respawn failed — {msg}", file=sys.stderr)
                return 1
            return 0
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Timeout — clean up sentinel, do NOT spawn
    try:
        restart_file.unlink()
    except OSError:
        pass
    print(f"{role}: timeout waiting for idle ({timeout}s) — agent is busy, no spawn",
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
        # Get all agent roles from config
        try:
            from config import get_agents
            agents = get_agents()
        except Exception:
            agents = ["pm", "skill"]

        exit_code = 0
        for agent in agents:
            role = agent['id'] if isinstance(agent, dict) else agent
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
