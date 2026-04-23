#!/usr/bin/env python3
"""SquidSquad reboot_agent — safe agent restart via sentinel.

Writes .restart sentinel then waits for the agent to go idle before killing.
The wrapper detects the sentinel on exit and respawns.

Usage:
    python references/scripts/reboot_agent.py <role>
    python references/scripts/reboot_agent.py skill
    python references/scripts/reboot_agent.py --all
    python references/scripts/reboot_agent.py skill --timeout 300
    python references/scripts/reboot_agent.py skill --force

Exit codes:
    0 — reboot initiated (or agent not running)
    1 — timeout (agent busy, sentinel cleaned up)
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


def _get_clone_path(role):
    """Get the clone path for a role from .local-config."""
    local_config = SQUID_DIR / ".local-config"
    if not local_config.exists():
        return REPO_ROOT  # Single-clone setup

    for line in local_config.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith(f"- **{role}**:"):
            path = line.split(":", 1)[1].strip()
            return Path(path)
    return REPO_ROOT


def _is_process_alive(pid):
    """Check if a process is alive."""
    if sys.platform == "win32":
        result = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
            capture_output=True, text=True, check=False,
        )
        return str(pid) in result.stdout
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False


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


def reboot(role, timeout=DEFAULT_TIMEOUT, force=False):
    """Reboot an agent safely."""
    clone_path = _get_clone_path(role)
    squid = clone_path / ".squidsquad"
    pid_file = squid / role / ".pid"
    restart_file = squid / role / ".restart"

    # Check if agent is running
    if not pid_file.exists():
        print(f"{role}: not running (no PID file)")
        return 0

    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        print(f"{role}: invalid PID file")
        return 0

    if not _is_process_alive(pid):
        print(f"{role}: not running (PID {pid} dead)")
        return 0

    # Write restart sentinel
    restart_file.write_text("reboot requested by reboot_agent.py", encoding="utf-8")

    if force:
        _kill_process(pid)
        print(f"{role}: force reboot initiated (PID {pid})")
        return 0

    # Wait for idle
    elapsed = 0
    while elapsed < timeout:
        state = _read_current_state(clone_path, role)
        if state.startswith("idle"):
            _kill_process(pid)
            print(f"{role}: reboot initiated (PID {pid}, went idle after {elapsed}s)")
            return 0
        time.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Timeout — clean up sentinel
    try:
        restart_file.unlink()
    except OSError:
        pass
    print(f"{role}: timeout waiting for idle ({timeout}s) — agent is busy", file=sys.stderr)
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
            sys.path.insert(0, str(SCRIPT_DIR))
            from config import get_agents
            agents = get_agents()
        except Exception:
            agents = ["pm", "skill"]

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
