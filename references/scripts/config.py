#!/usr/bin/env python3
"""SquidSquad config.md reader/writer.

Single source of truth for reading and writing config.md values.
All agents use this instead of parsing config.md themselves.

Usage:
    python scripts/config.py get <field>           # Get a field value
    python scripts/config.py set <field> <value>   # Set a field value
    python scripts/config.py dump                  # Dump all fields as JSON
    python scripts/config.py agents                # List agents as JSON
    python scripts/config.py schema-version        # Print 1 or 2
    python scripts/config.py --help                # Show usage

Schema versions:
    v1 (legacy) — Flat `## Agents` with a `- **Dev Agents**: fe, be` line.
        Per-role details live in `## Aliases`, `## Test Commands`, etc.
        Used by everything that shipped before #328.
    v2 (Q-new17) — `## Agents` with one entry per agent, nested fields
        (role / variant / iteration_mode / stack / test_command / setup).
        Written by the install wizard (Phase G) and resolved by Phase H.

Schema detection uses the top-level `- **Architecture Version**: N`
field. v1 files have `1`, v2 files have `2`. Readers that don't care
about agents (e.g. `get interval`) work unchanged against either schema.
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
    "project-intent": ("Project", "Intent Description"),
    "skill-tests": ("Test Commands", "skill Tests"),
    "e2e-tests": ("Test Commands", "E2E Tests"),
    "interval": ("Iteration Interval", "Minutes"),
    "context-threshold": ("Context Pressure", "Threshold"),
    "pr-flow": ("PR Flow", "Enabled"),
    "improvement-scanning": ("Improvement Scanning", "Enabled"),
    "ship-threshold": ("Auto Versioning", "Ship Threshold"),
    "shipped-since-bump": ("Auto Versioning", "Shipped Since Last Bump"),
    "alias-skill": ("Aliases", "skill"),
    "alias-pm": ("Aliases", "pm"),
    "alias-dm": ("Aliases", "dm"),
    "alias-designer": ("Aliases", "designer"),
    "alias-qa": ("Aliases", "qa"),
    "vault-remember": ("Vault Remember", "Enabled"),
    "vault-writes-per-cycle": ("Vault Remember", "Writes Per Cycle"),
    "briefing-token-budget": ("Vault Remember", "BRIEFING Token Budget"),
    "confidence-decay-days": ("Vault Remember", "Confidence Decay Days"),
    "vault-optimize": ("Vault Optimize", "Enabled"),
    "agent-compose": ("Agent Compose", "Enabled"),
    "auto-merge": ("Auto Merge", "Enabled"),
    "branch-workflow": ("Branch Workflow", "Enabled"),
    "mandatory-human-approval": ("Mandatory Human Approval", "Enabled"),
    "event-driven": ("Event Driven", "Enabled"),
    "scan-idle-timeout": ("Event Driven", "Scan Idle Timeout"),
    "diagnostics": ("Diagnostics", "Enabled"),
    "upstream-reporting": ("Diagnostics", "Upstream Reporting"),
    "default-model": ("Model Routing", "Default Model"),
    "research-model": ("Model Routing", "Research Model"),
    "discussion-prep-model": ("Model Routing", "Discussion Prep Model"),
    "test-plan-model": ("Model Routing", "Test Plan Model"),
    "qa-execution-model": ("Model Routing", "QA Execution Model"),
    "comprehension-model": ("Model Routing", "Comprehension Model"),
    "improvement-scan-model": ("Model Routing", "Improvement Scan Model"),
    "code-review-model": ("Model Routing", "Code Review Model"),  # #5932
    "fallback-model": ("Model Routing", "Fallback Model"),
    "api-timeout-seconds": ("Model Routing", "API Timeout Seconds"),
    "forge-provider": ("Forge Backend", "Provider"),
    "forge-endpoint": ("Forge Backend", "Endpoint"),
    "forge-owner": ("Forge Backend", "Owner"),
    "forge-repo": ("Forge Backend", "Repo"),
    "working-branch": ("Git Branches", "Working Branch"),
    "state-branch": ("Git Branches", "State Branch"),
    "branch-pattern": ("Git Branches", "Branch Pattern"),
    "harness-enabled": ("Harness", "Enabled"),
    "harness-port": ("Harness", "Port"),
    # Event-driven architecture (#7630 Phase 3)
    "event-timeout-minutes": ("Event Driven", "Timeout Minutes"),
    "event-max-retries": ("Event Driven", "Max Retries"),
    "event-poll-interval": ("Event Driven", "Poll Interval"),
    "event-queue-cap": ("Event Driven", "Queue Cap"),
    "scan-cooldown": ("Event Driven", "Scan Cooldown"),
    "effort-pm": ("Agent Effort", "pm"),
    "effort-skill": ("Agent Effort", "skill"),
    "effort-qa": ("Agent Effort", "qa"),
    "effort-dm": ("Agent Effort", "dm"),
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


# Fields that default to a value when absent from config.md (rather than exiting)
_FIELD_DEFAULTS = {
    "event-driven": "no",
}


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
        if field in _FIELD_DEFAULTS:
            return _FIELD_DEFAULTS[field]
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
        if not section_text:
            print(f"ERROR: Section '{section}' is empty or missing in config.md", file=sys.stderr)
            sys.exit(1)
        pattern = rf'(-\s*\*\*{re.escape(field_name)}\*\*:\s*).+'
        new_section, count = re.subn(pattern, rf'\g<1>{value}', section_text, count=1)
        if count == 0:
            print(f"ERROR: Field '{field}' not found in section '{section}'", file=sys.stderr)
            sys.exit(1)
        new_text = text.replace(section_text, new_section, 1)
    else:
        pattern = rf'(-\s*\*\*{re.escape(field_name)}\*\*:\s*).+'
        new_text, count = re.subn(pattern, rf'\g<1>{value}', text, count=1)
        if count == 0:
            print(f"ERROR: Field '{field}' not found in config.md", file=sys.stderr)
            sys.exit(1)

    CONFIG_PATH.write_text(new_text, encoding="utf-8")
    return value


def get_alias(role):
    """Get the alias for a role. Falls back to bare role name if not set."""
    text = _read_config()
    alias_key = f"alias-{role}"
    entry = FIELD_MAP.get(alias_key)
    if entry:
        section, field_name = entry
        val = _parse_field(text, section, field_name)
        if val:
            return val
    # Fallback: bare role name
    return role


# ---------------------------------------------------------------------------
# Event Reactions section parsing (#5868)
# ---------------------------------------------------------------------------


def get_event_reactions(text=None):
    """Parse the ## Event Reactions section from config.md.

    Returns a dict: {role: {"emits": [str], "reacts_to": [str]}} or empty dict
    if the section is absent or malformed. Never raises — graceful fallback.
    """
    if text is None:
        text = _read_config()
    sections = _parse_sections(text)
    section_text = sections.get("Event Reactions", "")
    if not section_text.strip():
        return {}

    result = {}
    current_role = None

    for line in section_text.splitlines():
        # Detect ### role heading
        role_match = re.match(r'^###\s+(\w+)', line)
        if role_match:
            current_role = role_match.group(1).strip()
            result[current_role] = {"emits": [], "reacts_to": []}
            continue

        if not current_role:
            continue

        # Parse - **emits**: event1, event2, ...
        emits_match = re.match(r'-\s*\*\*emits\*\*:\s*(.+)', line)
        if emits_match:
            raw = emits_match.group(1).strip()
            result[current_role]["emits"] = [
                e.strip() for e in raw.split(",") if e.strip()
            ]
            continue

        # Parse - **reacts-to**: event1, event2, ...
        reacts_match = re.match(r'-\s*\*\*reacts-to\*\*:\s*(.+)', line)
        if reacts_match:
            raw = reacts_match.group(1).strip()
            result[current_role]["reacts_to"] = [
                e.strip() for e in raw.split(",") if e.strip()
            ]
            continue

    return result


def get_event_filters_for_role(role, text=None):
    """Get the reacts-to event types for a specific role from Event Reactions.

    Returns a set of event type strings, or None if the section is absent
    (caller should fall back to hardcoded defaults).
    """
    reactions = get_event_reactions(text)
    if not reactions:
        return None
    role_data = reactions.get(role)
    if not role_data:
        return None
    reacts_to = role_data.get("reacts_to", [])
    return set(reacts_to) if reacts_to else None


def write_event_reactions(reactions_dict, text=None):
    """Write the ## Event Reactions section to config.md.

    reactions_dict: {role: {"emits": [str], "reacts_to": [str]}}
    Atomic write — replaces the entire section or appends if absent.
    """
    if text is None:
        text = _read_config()

    # Build the new section content
    lines = ["\n## Event Reactions\n"]
    for role in sorted(reactions_dict.keys()):
        data = reactions_dict[role]
        lines.append(f"\n### {role}")
        emits = ", ".join(data.get("emits", []))
        reacts_to = ", ".join(data.get("reacts_to", []))
        lines.append(f"- **emits**: {emits}")
        lines.append(f"- **reacts-to**: {reacts_to}")
    new_section = "\n".join(lines) + "\n"

    # Replace existing section or append
    sections = _parse_sections(text)
    if "Event Reactions" in sections:
        # Find and replace the section in the raw text
        # Match from "## Event Reactions" to next "## " or end of file
        pattern = r'(## Event Reactions\s*\n)(.*?)(?=\n## |\Z)'
        replacement = "## Event Reactions\n" + "\n".join(lines[1:]) + "\n"
        new_text = re.sub(pattern, replacement, text, count=1, flags=re.DOTALL)
    else:
        # Append to end of file
        new_text = text.rstrip() + "\n" + new_section

    # Atomic write
    tmp = CONFIG_PATH.with_suffix(".tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(CONFIG_PATH)


# ---------------------------------------------------------------------------
# Schema-aware agent parsing (#328 Phase H)
# ---------------------------------------------------------------------------


def detect_schema_version(text=None):
    """Return 1 or 2 based on the top-level `Architecture Version` field.

    Missing field -> assume v1 (legacy). Malformed/non-integer -> v1.
    """
    if text is None:
        text = _read_config()
    raw = _parse_field_in_text(text, "Architecture Version")
    if not raw:
        return 1
    try:
        n = int(raw.strip())
    except (TypeError, ValueError):
        return 1
    return 2 if n >= 2 else 1


def _parse_agents_v1(text):
    """Parse the legacy `- **Dev Agents**: fe, be` format.

    Returns a list of dicts shaped like the v2 output:
        [{"id": "fe", "alias": "fe", "role": "dev"}, ...]

    Infrastructure roles (pm, qa, dm) are always present (#6261 fixed team).
    Aliases are read from the `## Aliases` section.
    """
    sections = _parse_sections(text)
    agents_text = sections.get("Agents", "")
    aliases_text = sections.get("Aliases", "")
    test_cmd_text = sections.get("Test Commands", "")

    dev_roles_raw = _parse_field_in_text(agents_text, "Dev Agents") or ""
    dev_roles = [r.strip() for r in dev_roles_raw.split(",") if r.strip()]

    def _alias(role):
        val = _parse_field_in_text(aliases_text, role)
        return val if val else role

    def _test_cmd(role):
        # "skill Tests" is the legacy naming — keyed by role name
        return _parse_field_in_text(test_cmd_text, f"{role} Tests")

    result = []

    # PM is always present
    result.append({"id": "pm", "alias": _alias("pm"), "role": "pm"})

    # Dev roles — detect actual role identity from references/roles/
    # Agents like qa, designer have their own role templates and are NOT dev variants.
    known_identities = set()
    roles_dir = REPO_ROOT / "references" / "roles"
    if roles_dir.exists():
        known_identities = {
            d.name for d in roles_dir.iterdir()
            if d.is_dir() and (d / "CLAUDE.md").exists()
        }

    for role in dev_roles:
        # If this role has its own identity (not just dev), use it
        if role in known_identities and role != "dev":
            actual_role = role
        else:
            actual_role = "dev"
        entry = {"id": role, "alias": _alias(role), "role": actual_role}
        cmd = _test_cmd(role)
        if cmd:
            entry["test_command"] = cmd
        result.append(entry)

    # Fixed team: QA + DM always present (#6261)
    seen_ids = {e["id"] for e in result}
    for mandatory_role in ("qa", "dm"):
        if mandatory_role not in seen_ids:
            result.append({"id": mandatory_role, "alias": _alias(mandatory_role), "role": mandatory_role})

    return result


_AGENT_ENTRY_RE = re.compile(r"^-\s*\*\*([^*]+)\*\*:\s*(.*?)\s*$")
_NESTED_FIELD_RE = re.compile(r"^  -\s*([a-z_][a-z0-9_]*):\s*(.*?)\s*$")
_SETUP_FIELD_RE = re.compile(r"^    -\s*([a-z_][a-z0-9_]*):\s*(.*?)\s*$")


def _strip_yaml_quotes(value):
    """Remove surrounding double quotes if present — matches _quote_if_needed."""
    if len(value) >= 2 and value[0] == value[-1] == '"':
        return value[1:-1]
    return value


def _parse_agents_v2(text):
    """Parse the Q-new17 nested agent block.

    Returns a list of dicts with the same shape the wizard writes:
        {id, alias, role, variant, iteration_mode, stack, test_command, setup}
    """
    sections = _parse_sections(text)
    agents_text = sections.get("Agents", "")

    result = []
    current = None
    in_setup = False

    for raw_line in agents_text.splitlines():
        line = raw_line.rstrip()

        # Top-level agent entry line
        m = _AGENT_ENTRY_RE.match(line)
        if m:
            if current is not None:
                result.append(current)
            agent_id = m.group(1).strip()
            alias = _strip_yaml_quotes(m.group(2).strip())
            current = {"id": agent_id, "alias": alias or agent_id}
            in_setup = False
            continue

        if current is None:
            continue

        # `  - setup:` sentinel opens the nested setup block
        if re.match(r"^\s\s-\s*setup:\s*$", line):
            current["setup"] = {}
            in_setup = True
            continue

        # `    - key: value` inside the setup block
        if in_setup:
            sm = _SETUP_FIELD_RE.match(line)
            if sm:
                key = sm.group(1)
                value = _strip_yaml_quotes(sm.group(2))
                current["setup"][key] = value
                continue
            # Anything else closes the setup block
            in_setup = False

        # Nested field directly under the agent (role/variant/.../test_command)
        nm = _NESTED_FIELD_RE.match(line)
        if nm:
            key = nm.group(1)
            value = _strip_yaml_quotes(nm.group(2))
            current[key] = value
            continue

    if current is not None:
        result.append(current)

    return result


def get_agents(text=None):
    """Return the agent list for the active schema.

    Schema is detected via `detect_schema_version`. Callers that just want
    "the agents on this install" should use this — it abstracts the
    legacy vs wizard-shape distinction.
    """
    if text is None:
        text = _read_config()
    if detect_schema_version(text) == 2:
        return _parse_agents_v2(text)
    return _parse_agents_v1(text)


def sync_agents():
    """Scan .squidsquad/*/CLAUDE.md and update config.md Agents section."""
    sqdir = REPO_ROOT / ".squidsquad"
    # Find all roles with CLAUDE.md
    dev_roles = []
    for subdir in sorted(sqdir.iterdir()):
        if not subdir.is_dir():
            continue
        if (subdir / "CLAUDE.md").exists():
            name = subdir.name
            # Fixed team roles are listed separately (#6261)
            if name in ("pm", "qa", "dm"):
                continue
            dev_roles.append(name)

    # Update config
    if dev_roles:
        set_field("dev-agents", ", ".join(dev_roles))

    # Report — include fixed team roles that have CLAUDE.md
    roles = dev_roles + ["pm"]
    if (sqdir / "dm" / "CLAUDE.md").exists():
        roles.append("dm")
    if (sqdir / "qa" / "CLAUDE.md").exists():
        roles.append("qa")
    print(f"Synced agents: {', '.join(roles)}")
    return roles


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

    elif cmd == "sync-agents":
        sync_agents()

    elif cmd == "agents":
        print(json.dumps(get_agents(), indent=2))

    elif cmd == "schema-version":
        print(detect_schema_version())

    elif cmd == "list-agents":
        # Tab-separated columns: id<TAB>role<TAB>alias — one agent per line.
        # Designed for shell consumers (statusline.sh) that can't or
        # shouldn't depend on JSON parsing. Works against both v1 and v2
        # schemas via get_agents().
        for a in get_agents():
            agent_id = a.get("id", "")
            role = a.get("role", "")
            alias = a.get("alias", agent_id)
            print(f"{agent_id}\t{role}\t{alias}")

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
