#!/usr/bin/env python3
"""SquidSquad start_team.py — unified entry point for agent lifecycle.

Single script to start, reboot, or stop the entire squad or individual agents.
Replaces: start-squad.ps1/sh, boot_remote.py --all, reboot_agent.py.

Usage:
    python references/scripts/start_team.py --all              # Boot all agents
    python references/scripts/start_team.py --role skill       # Boot single agent
    python references/scripts/start_team.py --reboot skill     # Graceful restart
    python references/scripts/start_team.py --reboot --all     # Restart entire team
    python references/scripts/start_team.py --stop skill       # Stop agent
    python references/scripts/start_team.py --stop --all       # Stop all agents
    python references/scripts/start_team.py --help

Exit codes:
    0 — success
    1 — spawn/reboot failed
    2 — usage error
"""

import argparse
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"

# Import boot_remote for spawn/detection logic
sys.path.insert(0, str(SCRIPT_DIR))
import boot_remote


# ---------------------------------------------------------------------------
# Sentinel operations
# ---------------------------------------------------------------------------

def _write_stop_after_cycle(role, reason="reboot requested"):
    """Write .stop-after-cycle sentinel to trigger graceful restart."""
    role_dir = SQUIDSQUAD_DIR / role
    if not role_dir.exists():
        role_dir.mkdir(parents=True, exist_ok=True)
    sentinel = role_dir / ".stop-after-cycle"
    sentinel.write_text(reason, encoding="utf-8")


def _write_stop(role):
    """Write .stop sentinel to permanently stop an agent."""
    role_dir = SQUIDSQUAD_DIR / role
    if not role_dir.exists():
        role_dir.mkdir(parents=True, exist_ok=True)
    sentinel = role_dir / ".stop"
    sentinel.write_text("stopped by start_team.py", encoding="utf-8")


def _remove_stop(role):
    """Remove .stop sentinel to allow agent to run."""
    sentinel = SQUIDSQUAD_DIR / role / ".stop"
    if sentinel.exists():
        sentinel.unlink()


def _clean_stale_sentinels(role):
    """Clean stale .restart sentinels from previous system (migration)."""
    restart = SQUIDSQUAD_DIR / role / ".restart"
    if restart.exists():
        restart.unlink()
        print(f"  [{role}] Cleaned stale .restart sentinel")


def _is_agent_idle(role):
    """Check if agent is idle by reading current-state."""
    state_file = SQUIDSQUAD_DIR / role / "current-state"
    if not state_file.exists():
        return True  # No state file = not running = effectively idle
    try:
        content = state_file.read_text(encoding="utf-8").strip()
        return content.startswith("idle")
    except OSError:
        return True


def _wait_for_exit(role, timeout=300):
    """Wait for agent to exit after .stop-after-cycle is written."""
    print(f"  [{role}] Waiting for cycle to complete (timeout {timeout}s)...")
    start = time.time()
    while time.time() - start < timeout:
        # Check if .stop-after-cycle was consumed (agent exited)
        sentinel = SQUIDSQUAD_DIR / role / ".stop-after-cycle"
        if not sentinel.exists():
            # Sentinel consumed = agent exited and wrapper respawned
            print(f"  [{role}] Cycle complete, respawning...")
            return True
        time.sleep(5)
    print(f"  [{role}] Timeout waiting for cycle completion", file=sys.stderr)
    return False


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_boot(roles):
    """Boot agents that are not running."""
    results = []
    for role in roles:
        _clean_stale_sentinels(role)
        _remove_stop(role)
        r = boot_remote.boot_agent(role)
        results.append(r)
        status = "OK" if r["success"] else "FAIL"
        print(f"  [{role}] {r['action']} -- {status}: {r['message']}")
    return all(r["success"] for r in results)


def cmd_reboot(roles, force=False):
    """Gracefully reboot agents via .stop-after-cycle sentinel."""
    for role in roles:
        _clean_stale_sentinels(role)

        # Check if agent is running
        needs_boot, reason, _ = boot_remote._needs_boot(role)
        if needs_boot:
            print(f"  [{role}] Not running ({reason}). Booting fresh...")
            r = boot_remote.boot_agent(role)
            status = "OK" if r["success"] else "FAIL"
            print(f"  [{role}] {r['action']} -- {status}: {r['message']}")
            continue

        if force:
            print(f"  [{role}] Force reboot -- killing process...")
            # Import the kill logic from reboot_agent if available
            try:
                import reboot_agent
                reboot_agent._kill_agent(role)
            except (ImportError, AttributeError):
                pass
            time.sleep(2)
            r = boot_remote.boot_agent(role)
            status = "OK" if r["success"] else "FAIL"
            print(f"  [{role}] {r['action']} -- {status}: {r['message']}")
        else:
            print(f"  [{role}] Writing .stop-after-cycle sentinel...")
            _write_stop_after_cycle(role, "reboot via start_team.py")
            # Don't wait — wrapper handles respawn after agent finishes cycle

    return True


def cmd_stop(roles):
    """Stop agents by writing .stop sentinel."""
    for role in roles:
        print(f"  [{role}] Writing .stop sentinel...")
        _write_stop(role)
        # Also write .stop-after-cycle so agent exits at cycle end
        _write_stop_after_cycle(role, "stopped via start_team.py")
    return True


# ---------------------------------------------------------------------------
# Role resolution
# ---------------------------------------------------------------------------

def _get_all_roles():
    """Get all configured roles from boot_remote."""
    return boot_remote._get_all_roles()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="SquidSquad unified agent lifecycle management.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--role", help="Target a single agent role")
    group.add_argument("--all", action="store_true", help="Target all agents")

    action = parser.add_mutually_exclusive_group()
    action.add_argument("--reboot", nargs="?", const=True,
                        help="Graceful restart (write .stop-after-cycle)")
    action.add_argument("--stop", nargs="?", const=True,
                        help="Stop agent(s) permanently (write .stop)")

    parser.add_argument("--force", action="store_true",
                        help="Force immediate action (skip waiting)")

    args = parser.parse_args()

    # Determine roles
    if args.all:
        roles = _get_all_roles()
        if not roles:
            print("No agents configured.", file=sys.stderr)
            return 2
    elif args.role:
        roles = [args.role]
    elif isinstance(args.reboot, str):
        roles = [args.reboot]
    elif isinstance(args.stop, str):
        roles = [args.stop]
    else:
        # Default to --all
        roles = _get_all_roles()
        if not roles:
            parser.print_help()
            return 2

    print(f"[SquidSquad] Targeting: {', '.join(roles)}")

    # Determine action
    if args.stop is not None:
        success = cmd_stop(roles)
    elif args.reboot is not None:
        success = cmd_reboot(roles, force=args.force)
    else:
        success = cmd_boot(roles)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
