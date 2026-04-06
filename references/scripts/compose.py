#!/usr/bin/env python3
"""SquidSquad sub-skill composition engine.

Reads role entry files, resolves {{include: path}} directives by inlining
the referenced sub-skill content, and wraps each inclusion with
<!-- sub-skill: name --> section markers.

Usage:
    python scripts/compose.py dev-agent        # Compose dev agent template
    python scripts/compose.py pm-agent         # Compose PM/QA template
    python scripts/compose.py all              # Compose all roles to agent-instructions.md
    python scripts/compose.py --help
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SUB_SKILLS_DIR = REPO_ROOT / "references" / "sub-skills"
OUTPUT_FILE = REPO_ROOT / "references" / "agent-instructions.md"


def _resolve_includes(entry_file: Path) -> str:
    """Resolve all {{include: path}} directives in an entry file."""
    text = entry_file.read_text(encoding="utf-8")
    lines = text.splitlines()
    result = []

    for line in lines:
        match = re.match(r'\s*\{\{include:\s*(.+?)\}\}\s*$', line)
        if match:
            include_path = match.group(1).strip()
            # Resolve relative to sub-skills directory
            full_path = SUB_SKILLS_DIR / f"{include_path}.md"
            if not full_path.exists():
                result.append(f"<!-- ERROR: Missing include: {include_path} -->")
                continue

            # Extract sub-skill name from path (last component without .md)
            sub_skill_name = full_path.stem

            # Read and wrap with markers
            content = full_path.read_text(encoding="utf-8").rstrip()
            result.append(f"<!-- sub-skill: {sub_skill_name} -->")
            result.append(content)
            result.append(f"<!-- /sub-skill: {sub_skill_name} -->")
        else:
            result.append(line)

    return "\n".join(result)


def compose_role(role_name: str) -> str:
    """Compose a role's full template from its entry file."""
    entry_file = SUB_SKILLS_DIR / "roles" / f"{role_name}.md"
    if not entry_file.exists():
        print(f"ERROR: Entry file not found: {entry_file}", file=sys.stderr)
        sys.exit(1)

    composed = _resolve_includes(entry_file)
    return composed


def compose_all() -> str:
    """Compose the dev-agent template as the default agent-instructions.md."""
    # agent-instructions.md is the dev-agent template (primary output)
    header = "<!-- GENERATED FILE — DO NOT EDIT. Source: references/sub-skills/ -->\n"
    header += "<!-- Regenerate with: python references/scripts/compose.py all -->\n\n"
    composed = compose_role("dev-agent")
    return header + composed


def _read_config_value(field: str) -> str:
    """Read a config value using config.py."""
    try:
        from config import get_field
        return get_field(field)
    except Exception:
        return ""


def _get_entry_file_for_role(role_name: str) -> str:
    """Map an agent role name to its entry file name."""
    # Dev agents use dev-agent.md
    # PM uses pm-agent.md (or pm-lean.md if QA exists)
    # QA uses qa-agent.md
    # DM uses dm-agent.md
    # Designer uses designer.md
    role_map = {
        "pm": "pm-agent",
        "qa": "qa-agent",
        "dm": "dm-agent",
        "designer": "designer",
    }
    return role_map.get(role_name, "dev-agent")


def _substitute_placeholders(content: str, role_name: str, entry_file: str) -> str:
    """Substitute role-specific placeholders in composed content.

    Dev agents: [ROLE], [ROLE_UPPER], [ROLE_TEST_CMD], [INTERVAL] are substituted.
    PM/DM/QA/Designer: [ROLE] is NOT substituted (used as dev agent variable).
    """
    is_dev = entry_file == "dev-agent"

    if is_dev:
        content = content.replace("[ROLE]", role_name)
        content = content.replace("[ROLE_UPPER]", role_name.upper())

        # Test command
        test_cmd = _read_config_value(f"{role_name}-tests") or \
                   f'echo "{role_name.title()} repo -- no automated tests."'
        content = content.replace("[ROLE_TEST_CMD]", test_cmd)

        # Other roles
        all_agents = _read_config_value("dev-agents") or role_name
        other = [r.strip() for r in all_agents.split(",") if r.strip() != role_name]
        content = content.replace("[OTHER_ROLES]", ", ".join(other) if other else "(none)")

    # Shared placeholders (all roles)
    interval = _read_config_value("interval") or "30"
    content = content.replace("[INTERVAL]", interval)

    # PM/DM-specific
    if not is_dev:
        active_agents = _read_config_value("dev-agents") or ""
        content = content.replace("[ACTIVE_AGENTS]", active_agents)

        e2e_cmd = _read_config_value("e2e-tests") or "(none)"
        content = content.replace("[E2E_TEST_CMD]", e2e_cmd)

    return content


def deploy_role(role_name: str) -> Path:
    """Full pipeline: compose entry file -> substitute placeholders -> write CLAUDE.md."""
    entry_file = _get_entry_file_for_role(role_name)
    composed = compose_role(entry_file)
    final = _substitute_placeholders(composed, role_name, entry_file)

    # Prepend soul include (already resolved by compose_role via {{include: souls/...}})
    # Add header
    header = f"# SquidSquad -- {role_name} Lead\n\n"
    header += f"<!-- GENERATED by compose.py deploy {role_name}. DO NOT EDIT. -->\n"
    header += f"<!-- Regenerate: python references/scripts/compose.py deploy {role_name} -->\n\n"

    output_path = REPO_ROOT / ".squidsquad" / role_name / "CLAUDE.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(header + final, encoding="utf-8")
    return output_path


TEMPLATES_DIR = REPO_ROOT / "references" / "templates"


def boot_role(role_name: str) -> list:
    """Generate boot scripts (start-[role].sh and start-[role].ps1) from templates."""
    outputs = []
    for ext in ("sh", "ps1"):
        template_path = TEMPLATES_DIR / f"start-role.{ext}"
        if not template_path.exists():
            print(f"ERROR: Template not found: {template_path}", file=sys.stderr)
            sys.exit(1)

        content = template_path.read_text(encoding="utf-8")
        content = content.replace("{{ROLE}}", role_name)

        output_path = REPO_ROOT / ".squidsquad" / f"start-{role_name}.{ext}"
        # .sh files must use LF line endings (not CRLF on Windows)
        newline = "\n" if ext == "sh" else None
        output_path.write_text(content, encoding="utf-8", newline=newline)
        outputs.append(output_path)

    return outputs


def boot_all() -> list:
    """Generate boot scripts for all configured roles."""
    agents = _read_config_value("dev-agents") or ""
    roles = [r.strip() for r in agents.split(",") if r.strip()]
    roles.append("pm")  # PM always present
    # Add DM if directory exists
    dm_dir = REPO_ROOT / ".squidsquad" / "dm"
    if dm_dir.exists():
        roles.append("dm")
    all_outputs = []
    for role in roles:
        outputs = boot_role(role)
        all_outputs.extend(outputs)
    return all_outputs


def main():
    args = sys.argv[1:]
    if not args or args[0] == "--help":
        print(__doc__)
        # List available roles
        roles_dir = SUB_SKILLS_DIR / "roles"
        if roles_dir.exists():
            roles = [f.stem for f in roles_dir.glob("*.md")]
            print(f"Available roles: {', '.join(sorted(roles))}")
        sys.exit(0)

    cmd = args[0]

    if cmd == "all":
        content = compose_all()
        OUTPUT_FILE.write_text(content, encoding="utf-8")
        print(f"Composed agent-instructions.md ({len(content.splitlines())} lines)")

    elif cmd == "deploy":
        if len(args) < 2:
            print("Usage: compose.py deploy <role>", file=sys.stderr)
            print("  e.g.: compose.py deploy skill", file=sys.stderr)
            sys.exit(1)
        role_name = args[1]
        output = deploy_role(role_name)
        lines = output.read_text(encoding="utf-8").count("\n")
        print(f"Deployed {role_name} CLAUDE.md ({lines} lines) -> {output.relative_to(REPO_ROOT)}")

    elif cmd == "deploy-all":
        # Deploy all configured agents
        agents = _read_config_value("dev-agents") or ""
        roles = [r.strip() for r in agents.split(",") if r.strip()]
        roles.append("pm")  # PM always present
        for role in roles:
            output = deploy_role(role)
            lines = output.read_text(encoding="utf-8").count("\n")
            print(f"  {role}: {lines} lines -> {output.relative_to(REPO_ROOT)}")

    elif cmd == "boot":
        if len(args) < 2:
            print("Usage: compose.py boot <role>", file=sys.stderr)
            print("  e.g.: compose.py boot skill", file=sys.stderr)
            sys.exit(1)
        role_name = args[1]
        outputs = boot_role(role_name)
        for out in outputs:
            print(f"Generated {out.relative_to(REPO_ROOT)}")

    elif cmd == "boot-all":
        outputs = boot_all()
        for out in outputs:
            print(f"  {out.relative_to(REPO_ROOT)}")

    else:
        # Treat as role entry file name
        content = compose_role(cmd)
        print(content)


if __name__ == "__main__":
    main()
