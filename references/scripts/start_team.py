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
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"

# Import boot_remote for spawn/detection logic
sys.path.insert(0, str(SCRIPT_DIR))
import boot_remote


# ---------------------------------------------------------------------------
# Harness API communication (#4966)
# ---------------------------------------------------------------------------

def _discover_harness_port():
    """Discover harness port — default 7373 + .harness-port file."""
    port_file = SQUIDSQUAD_DIR / ".harness-port"
    if port_file.exists():
        try:
            return int(port_file.read_text(encoding="utf-8").strip())
        except (ValueError, OSError):
            pass
    return 7373


def _harness_api(method, path, timeout=5):
    """Call harness API. Returns (success, response_dict) or (False, None)."""
    port = _discover_harness_port()
    url = f"http://127.0.0.1:{port}{path}"
    try:
        req = urllib.request.Request(url, method=method)
        if method == "POST":
            req.add_header("Content-Type", "application/json")
            req.data = b"{}"
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return True, data
    except (urllib.error.URLError, OSError, json.JSONDecodeError, TimeoutError):
        return False, None


# Sentinel-file lifecycle removed in #4792. Stop/restart now flow exclusively
# through the harness API (POST /agents/<role>/stop|restart). If the harness
# is unreachable, those commands fail loudly rather than writing a stale
# `.stop` file that survived the harness restart and caused split-brain.


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


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_boot(roles):
    """Boot agents that are not running."""
    results = []
    for role in roles:
        r = boot_remote.boot_agent(role)
        results.append(r)
        status = "OK" if r["success"] else "FAIL"
        print(f"  [{role}] {r['action']} -- {status}: {r['message']}")
    return all(r["success"] for r in results)


def cmd_reboot(roles, force=False):
    """Gracefully reboot agents via harness API (#4966)."""
    for role in roles:
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
            try:
                import reboot_agent
                clone_path = boot_remote._get_clone_path(role)
                claude_pid, alive = reboot_agent._read_claude_pid(
                    Path(clone_path), role
                )
                if alive and claude_pid:
                    reboot_agent._kill_process(claude_pid)
                    print(f"  [{role}] Killed PID {claude_pid}")
            except (ImportError, OSError) as e:
                # #4792 Phase 2: reboot_agent._kill_process now swallows
                # ProcessLookupError on POSIX internally, so it can no
                # longer propagate out of the kill call. ProcessLookupError
                # is a subclass of OSError anyway — listing it was always
                # redundant.
                print(f"  [{role}] Kill failed: {e}")
            time.sleep(2)
            r = boot_remote.boot_agent(role)
            status = "OK" if r["success"] else "FAIL"
            print(f"  [{role}] {r['action']} -- {status}: {r['message']}")
        else:
            # Use harness API to set intent=restarting (#4966)
            ok, resp = _harness_api("POST", f"/agents/{role}/restart")
            if ok:
                print(f"  [{role}] Harness: restart requested (intent=restarting)")
            else:
                print(f"  [{role}] Harness unreachable — agent will continue until next cycle")

    return True


def cmd_stop(roles):
    """Stop agents via harness API (#4966).

    #4792: no more `.stop` sentinel fallback. If the harness is unreachable,
    the stop command fails — preferable to writing a stale sentinel that
    survives the harness restart and silently overrides next boot.
    """
    all_ok = True
    for role in roles:
        ok, resp = _harness_api("POST", f"/agents/{role}/stop")
        if ok:
            print(f"  [{role}] Harness: stop requested (intent=stopping)")
        else:
            print(
                f"  [{role}] Harness unreachable — cannot stop agent. "
                f"Start the harness first, then re-run this command."
            )
            all_ok = False
    return all_ok


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
                        help="Graceful restart via harness API")
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
