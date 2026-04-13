#!/usr/bin/env python3
"""SquidSquad capability availability checker.

Reads a role manifest's `requires_sub_skills` field and checks whether
each referenced capability is available at runtime.

Usage:
    python scripts/capability_check.py <role>     # check capabilities for a role
    python scripts/capability_check.py --help

Provider checks:
  - mcp: checks that the capability manifest exists (MCP server assumed configured)
  - builtin: always available
  - cli: checks if the command exists via shutil.which
  - http: checks that the capability manifest exists (endpoint assumed reachable)

Semantics:
  - any_of: exit 0 if at least one capability is available
  - all_of: exit 0 if all capabilities are available
  - empty {}: exit 0 immediately (no capabilities required)

Exit codes:
  0 — all required capabilities available (or none required)
  1 — one or more required capabilities missing
  2 — usage error or manifest not found
"""

import shutil
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:
    print(
        "ERROR: PyYAML is required for capability checks.\n"
        "Install it with:  pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(2)


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
ROLES_DIR = REPO_ROOT / "references" / "roles"
CAPABILITIES_DIR = REPO_ROOT / "references" / "sub-skills" / "capabilities"


def _load_yaml(path):
    """Load a YAML file, return parsed data or None."""
    try:
        text = path.read_text(encoding="utf-8")
        return yaml.safe_load(text)
    except (OSError, yaml.YAMLError):
        return None


def check_capability(cap_id):
    """Check if a single capability is available.

    Returns (available: bool, reason: str).
    """
    manifest_path = CAPABILITIES_DIR / cap_id / "manifest.yaml"
    if not manifest_path.exists():
        return False, "manifest not found"

    data = _load_yaml(manifest_path)
    if data is None:
        return False, "manifest unreadable"

    provider = data.get("provider", "unknown")

    if provider == "builtin":
        return True, "builtin (always available)"
    elif provider == "mcp":
        # MCP: we check that the manifest exists; actual server
        # connectivity is checked at runtime by the agent.
        return True, f"mcp ({data.get('mcp_name', 'unknown')})"
    elif provider == "cli":
        cmd = data.get("cli_command", cap_id)
        if shutil.which(cmd):
            return True, f"cli ({cmd} found)"
        else:
            return False, f"cli ({cmd} not found)"
    elif provider == "http":
        # HTTP: manifest exists, assume endpoint is reachable
        return True, f"http ({data.get('docs_url', 'unknown')})"
    else:
        return False, f"unknown provider: {provider}"


def check_role(role_id):
    """Check all capabilities required by a role.

    Returns (exit_code, results_list).
    """
    role_manifest = ROLES_DIR / role_id / "manifest.yaml"
    if not role_manifest.exists():
        print(f"ERROR: Role manifest not found: {role_manifest}", file=sys.stderr)
        return 2, []

    data = _load_yaml(role_manifest)
    if data is None:
        print(f"ERROR: Cannot parse role manifest: {role_manifest}", file=sys.stderr)
        return 2, []

    requires = data.get("requires_sub_skills") or data.get("requires_tools") or {}
    if not isinstance(requires, dict) or not requires:
        print(f"OK: {role_id} requires no capabilities.")
        return 0, []

    results = []
    exit_code = 0

    for semantics in ("any_of", "all_of"):
        cap_ids = requires.get(semantics) or []
        if not cap_ids:
            continue

        group_results = []
        for cap_id in cap_ids:
            available, reason = check_capability(cap_id)
            group_results.append((cap_id, available, reason))
            status = "OK" if available else "MISSING"
            print(f"  [{status}] {cap_id}: {reason}")

        results.extend(group_results)

        if semantics == "any_of":
            if not any(avail for _, avail, _ in group_results):
                print(f"FAIL: {role_id} requires any_of {cap_ids} but none available.")
                exit_code = 1
            else:
                available_ids = [cid for cid, avail, _ in group_results if avail]
                print(f"OK: {role_id} any_of satisfied by: {available_ids}")

        elif semantics == "all_of":
            missing = [cid for cid, avail, _ in group_results if not avail]
            if missing:
                print(f"FAIL: {role_id} requires all_of but missing: {missing}")
                exit_code = 1
            else:
                print(f"OK: {role_id} all_of satisfied.")

    return exit_code, results


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print(__doc__)
        return 0

    role_id = sys.argv[1]
    exit_code, _ = check_role(role_id)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
