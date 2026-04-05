#!/usr/bin/env python3
"""SquidSquad config.md reader/writer.

Single source of truth for reading and writing config.md values.
All agents use this instead of parsing config.md themselves.

Usage:
    python scripts/config.py get <field>           # Get a field value
    python scripts/config.py set <field> <value>    # Set a field value
    python scripts/config.py dump                   # Dump all fields as JSON
    python scripts/config.py --help                 # Show usage
"""

import json
import re
import sys
from pathlib import Path

# Auto-detect repo root (walk up from script location)
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
CONFIG_PATH = REPO_ROOT / ".squidsquad" / "config.md"

# Known field mappings: short name -> (section_heading, field_name)
# Section heading is used for disambiguation when field names repeat (e.g. "Enabled")
FIELD_MAP = {
    "version": (None, "SquidSquad Version"),
    "tracker": (None, "Tracker"),
    "arch-version": (None, "Architecture Version"),
    "dev-agents": ("Agents", "Dev Agents"),
    "project-name": ("Project", "Name"),
    "repo": ("Project", "Repo"),
    "skill-tests": ("Test Commands", "skill Tests"),
    "e2e-tests": ("Test Commands", "E2E Tests"),
    "interval": ("Iteration Interval", "Minutes"),
    "context-threshold": ("Context Pressure", "Threshold"),
    "pr-flow": ("PR Flow", "Enabled"),
    "improvement-scanning": ("Improvement Scanning", "Enabled"),
    "ship-threshold": ("Auto Versioning", "Ship Threshold"),
    "shipped-since-bump": ("Auto Versioning", "Shipped Since Last Bump"),
    "alias-skill": ("Agent Aliases", "skill"),
    "alias-pm": ("Agent Aliases", "pm"),
    "alias-dm": ("Agent Aliases", "dm"),
    "alias-designer": ("Agent Aliases", "designer"),
    "alias-qa": ("Agent Aliases", "qa"),
}


def _read_config():
    """Read config.md and return raw text."""
    if not CONFIG_PATH.exists():
        print(f"ERROR: config.md not found at {CONFIG_PATH}", file=sys.stderr)
        sys.exit(1)
    return CONFIG_PATH.read_text(encoding="utf-8")


def _parse_sections(text):
    """Parse config.md into {section_heading: section_text} dict."""
    sections = {"": ""}  # content before first heading
    current = ""
    for line in text.splitlines():
        heading_match = re.match(r'^##\s+(.+)', line)
        if heading_match:
            current = heading_match.group(1).strip()
            sections[current] = ""
        else:
            sections[current] = sections.get(current, "") + line + "\n"
    return sections


def _parse_field_in_text(text, field_name):
    """Extract a field value from a block of markdown text."""
    pattern = rf'-\s*\*\*{re.escape(field_name)}\*\*:\s*(.+)'
    match = re.search(pattern, text)
    return match.group(1).strip() if match else None


def _parse_field(text, section, field_name):
    """Extract a field value, optionally scoped to a section."""
    if section:
        sections = _parse_sections(text)
        section_text = sections.get(section, "")
        return _parse_field_in_text(section_text, field_name)
    return _parse_field_in_text(text, field_name)


def _parse_all(text):
    """Parse all known fields from config.md."""
    result = {}
    for short_name, (section, field_name) in FIELD_MAP.items():
        val = _parse_field(text, section, field_name)
        if val is not None:
            result[short_name] = val
    return result


def get_field(field):
    """Get a config field by short name or full name."""
    text = _read_config()
    entry = FIELD_MAP.get(field)
    if entry:
        section, field_name = entry
        val = _parse_field(text, section, field_name)
    else:
        val = _parse_field_in_text(text, field)
    if val is None:
        print(f"ERROR: Field '{field}' not found in config.md", file=sys.stderr)
        sys.exit(1)
    return val


def set_field(field, value):
    """Set a config field value."""
    text = _read_config()
    entry = FIELD_MAP.get(field)
    if entry:
        section, field_name = entry
    else:
        section, field_name = None, field

    if section:
        # Section-aware replacement: find the section, then the field within it
        sections = _parse_sections(text)
        section_text = sections.get(section, "")
        pattern = rf'(-\s*\*\*{re.escape(field_name)}\*\*:\s*).+'
        new_section, count = re.subn(pattern, rf'\g<1>{value}', section_text, count=1)
        if count == 0:
            print(f"ERROR: Field '{field}' not found in section '{section}'", file=sys.stderr)
            sys.exit(1)
        new_text = text.replace(section_text, new_section)
    else:
        pattern = rf'(-\s*\*\*{re.escape(field_name)}\*\*:\s*).+'
        new_text, count = re.subn(pattern, rf'\g<1>{value}', text, count=1)
        if count == 0:
            print(f"ERROR: Field '{field}' not found in config.md", file=sys.stderr)
            sys.exit(1)

    CONFIG_PATH.write_text(new_text, encoding="utf-8")
    return value


def get_alias(role):
    """Get the alias for a role. Falls back to {project-name}-{role} if not set."""
    text = _read_config()
    alias_key = f"alias-{role}"
    entry = FIELD_MAP.get(alias_key)
    if entry:
        section, field_name = entry
        val = _parse_field(text, section, field_name)
        if val:
            return val
    # Fallback: project-name + role
    project = _parse_field(text, "Project", "Name") or "project"
    return f"{project.lower()}-{role}"


def dump_all():
    """Dump all config fields as JSON."""
    text = _read_config()
    return _parse_all(text)


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "--help":
        print(__doc__)
        print("Fields:", ", ".join(sorted(FIELD_MAP.keys())))
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "get":
        if len(sys.argv) < 3:
            print("Usage: config.py get <field>", file=sys.stderr)
            sys.exit(1)
        print(get_field(sys.argv[2]))

    elif cmd == "set":
        if len(sys.argv) < 4:
            print("Usage: config.py set <field> <value>", file=sys.stderr)
            sys.exit(1)
        set_field(sys.argv[2], sys.argv[3])
        print(f"Set {sys.argv[2]} = {sys.argv[3]}")

    elif cmd == "alias":
        if len(sys.argv) < 3:
            print("Usage: config.py alias <role>", file=sys.stderr)
            sys.exit(1)
        print(get_alias(sys.argv[2]))

    elif cmd == "dump":
        print(json.dumps(dump_all(), indent=2))

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
