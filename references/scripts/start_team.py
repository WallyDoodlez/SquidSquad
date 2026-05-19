#!/usr/bin/env python3
"""SquidSquad start_team.py — backward-compatible operator shim.

Per CONTEXT-4792.md §5.7, this script is now a thin delegate over
`squidsquad_cli.py`, which is the canonical operator entry point (Q1). The
familiar `start_team.py --all` / `--reboot` / `--stop` CLI surface is
preserved so existing muscle memory keeps working (Q11), but each command
dispatches into `squidsquad_cli` so there is a single source of truth for
agent lifecycle.

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
    1 — at least one delegated command failed
    2 — usage error
"""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUIDSQUAD_DIR = REPO_ROOT / ".squidsquad"

sys.path.insert(0, str(SCRIPT_DIR))
import boot_remote
import squidsquad_cli


def _get_all_roles():
    """Get all configured roles from boot_remote."""
    return boot_remote._get_all_roles()


def cmd_boot(roles):
    """Boot agents by delegating to `squidsquad_cli.cmd_start` per role."""
    all_ok = True
    for role in roles:
        rc = squidsquad_cli.cmd_start(role)
        if rc != 0:
            all_ok = False
    return all_ok


def cmd_reboot(roles, force=False):
    """Restart agents by delegating to `squidsquad_cli.cmd_restart` per role.

    The `--force` flag is preserved on the CLI surface for backward
    compatibility (Q11) but is now a no-op: the harness `/restart` endpoint
    handles idle-kill (#8689) and the new 60s force-kill safety net (#4792
    §3.3 Q7) covers stuck cases, so an operator-driven SIGKILL fallback is
    no longer needed.
    """
    if force:
        print("[start_team] --force is a deprecated no-op; "
              "harness force-kill safety net (#4792) handles stuck agents.")
    all_ok = True
    for role in roles:
        rc = squidsquad_cli.cmd_restart(role)
        if rc != 0:
            all_ok = False
    return all_ok


def cmd_stop(roles):
    """Stop agents by delegating to `squidsquad_cli.cmd_stop` per role."""
    all_ok = True
    for role in roles:
        rc = squidsquad_cli.cmd_stop(role)
        if rc != 0:
            all_ok = False
    return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="SquidSquad operator shim — delegates to squidsquad_cli.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    group = parser.add_mutually_exclusive_group()
    group.add_argument("--role", help="Target a single agent role")
    group.add_argument("--all", action="store_true", help="Target all agents")

    action = parser.add_mutually_exclusive_group()
    action.add_argument("--reboot", nargs="?", const=True,
                        help="Graceful restart via harness API")
    action.add_argument("--stop", nargs="?", const=True,
                        help="Stop agent(s)")

    parser.add_argument("--force", action="store_true",
                        help="Deprecated no-op (kept for muscle-memory).")

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

    if args.stop is not None:
        success = cmd_stop(roles)
    elif args.reboot is not None:
        success = cmd_reboot(roles, force=args.force)
    else:
        success = cmd_boot(roles)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
