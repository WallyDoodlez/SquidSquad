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

    role = args[0]

    if role == "all":
        content = compose_all()
        OUTPUT_FILE.write_text(content, encoding="utf-8")
        print(f"Composed agent-instructions.md ({len(content.splitlines())} lines)")
    else:
        content = compose_role(role)
        print(content)


if __name__ == "__main__":
    main()
