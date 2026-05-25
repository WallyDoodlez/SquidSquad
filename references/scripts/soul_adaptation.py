#!/usr/bin/env python3
"""SquidSquad soul adaptation — render Project Adaptation sections into live SOUL.md.

PM writes adaptation entries to vault/areas/role-adaptations.md, then calls
this script to re-render the live SOUL.md for each affected role.

Usage:
    python references/scripts/soul_adaptation.py render <role>
        Re-render .squidsquad/<role>/SOUL.md from reference template + adaptations

    python references/scripts/soul_adaptation.py add <role> --category <cat> --signal <text>
        Append a new signal to role-adaptations.md for the given role

    python references/scripts/soul_adaptation.py check-cap <role>
        Check if role's adaptation section exceeds the 40-line soft cap

    python references/scripts/soul_adaptation.py list <role>
        List current adaptation entries for a role

Exit codes:
    0 — success
    1 — error
    2 — usage error
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
SQUID_DIR = REPO_ROOT / ".squidsquad"
VAULT_DIR = SQUID_DIR / "vault"
ADAPTATIONS_FILE = VAULT_DIR / "areas" / "role-adaptations.md"

sys.path.insert(0, str(SCRIPT_DIR))
from shared_fs import atomic_write_text  # #10007

ADAPTATION_HEADER = "## Project Adaptation"
ADAPTATION_FOOTER = "<!-- /project-adaptation -->"

# 5-category trigger checklist
CATEGORIES = [
    "deliverable-type",   # What the project ships (app, library, docs, etc.)
    "tech-stack",         # Languages, frameworks, tools, conventions
    "domain-vocabulary",  # Domain-specific terms, concepts, jargon
    "quality-preference", # Testing depth, review rigor, perf expectations
    "user-persona",       # Who uses this, how they interact, their needs
]

LINE_CAP = 40


def _read_file(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (FileNotFoundError, OSError):
        return ""


def _ensure_adaptations_file():
    """Create role-adaptations.md if it doesn't exist."""
    if ADAPTATIONS_FILE.exists():
        return
    ADAPTATIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    ADAPTATIONS_FILE.write_text(
        "# Role Adaptations\n\n"
        "_Append-only changelog of project-specific soul adaptations. "
        "Written by PM, reviewed by human via git history._\n\n"
        "---\n",
        encoding="utf-8",
    )


def get_adaptations(role):
    """Get all adaptation entries for a role from role-adaptations.md.

    Returns list of dicts: [{date, category, signal, source_task}, ...]
    """
    content = _read_file(ADAPTATIONS_FILE)
    if not content:
        return []

    entries = []
    current_role = None
    for line in content.splitlines():
        # Role headers: ### skill, ### pm, etc.
        if line.startswith("### ") and not line.startswith("### —"):
            current_role = line[4:].strip().lower()
            continue

        if current_role != role:
            continue

        # Entry format: - [YYYY-MM-DD] **category**: signal (from #NNN)
        match = re.match(
            r'^- \[(\d{4}-\d{2}-\d{2})\] \*\*(\S+)\*\*: (.+?)(?:\s*\(from #(\d+)\))?$',
            line.strip(),
        )
        if match:
            entries.append({
                "date": match.group(1),
                "category": match.group(2),
                "signal": match.group(3).strip(),
                "source_task": match.group(4),
            })

    return entries


def add_adaptation(role, category, signal, source_task=None):
    """Append a new adaptation entry for a role."""
    if category not in CATEGORIES:
        print(f"WARNING: category '{category}' not in standard list: {CATEGORIES}",
              file=sys.stderr)

    _ensure_adaptations_file()
    content = _read_file(ADAPTATIONS_FILE)

    date_str = datetime.now().strftime("%Y-%m-%d")
    task_ref = f" (from #{source_task})" if source_task else ""
    entry = f"- [{date_str}] **{category}**: {signal}{task_ref}"

    # Find or create role section
    role_header = f"### {role}"
    if role_header not in content:
        content = content.rstrip() + f"\n\n{role_header}\n\n{entry}\n"
    else:
        # Insert after last entry in role section
        lines = content.splitlines()
        insert_idx = None
        in_role = False
        for i, line in enumerate(lines):
            if line.strip() == role_header:
                in_role = True
                continue
            if in_role:
                if line.startswith("### ") or line.startswith("---"):
                    insert_idx = i
                    break
                insert_idx = i + 1
        if insert_idx is not None:
            lines.insert(insert_idx, entry)
            content = "\n".join(lines) + "\n"
        else:
            content = content.rstrip() + f"\n{entry}\n"

    atomic_write_text(ADAPTATIONS_FILE, content)
    return entry


def render_adaptation_section(role):
    """Build the Project Adaptation section text for a role's SOUL.md."""
    entries = get_adaptations(role)
    if not entries:
        return (
            f"{ADAPTATION_HEADER}\n\n"
            "_No project-specific adaptations yet. PM will populate this "
            "as the project develops._\n"
            f"{ADAPTATION_FOOTER}\n"
        )

    lines = [ADAPTATION_HEADER, ""]

    # Group by category
    by_cat = {}
    for e in entries:
        cat = e["category"]
        by_cat.setdefault(cat, []).append(e)

    for cat in CATEGORIES:
        if cat not in by_cat:
            continue
        lines.append(f"**{cat}**:")
        for e in by_cat[cat]:
            lines.append(f"- {e['signal']}")
        lines.append("")

    # Uncategorized
    for cat, items in by_cat.items():
        if cat not in CATEGORIES:
            lines.append(f"**{cat}**:")
            for e in items:
                lines.append(f"- {e['signal']}")
            lines.append("")

    lines.append(ADAPTATION_FOOTER)
    return "\n".join(lines) + "\n"


def render_soul(role):
    """Re-render a role's live SOUL.md with current adaptations.

    Reads the live SOUL.md, replaces the Project Adaptation section
    (or appends it if missing), writes back.
    """
    soul_path = SQUID_DIR / role / "SOUL.md"
    content = _read_file(soul_path)
    if not content:
        print(f"ERROR: {soul_path} not found", file=sys.stderr)
        return False

    adaptation_text = render_adaptation_section(role)

    # Replace existing adaptation section
    if ADAPTATION_HEADER in content:
        # Find the section boundaries
        start = content.index(ADAPTATION_HEADER)
        if ADAPTATION_FOOTER in content:
            end = content.index(ADAPTATION_FOOTER) + len(ADAPTATION_FOOTER)
            # Include trailing newline
            while end < len(content) and content[end] == "\n":
                end += 1
        else:
            # No footer — replace to next ## or end of file
            rest = content[start + len(ADAPTATION_HEADER):]
            next_section = re.search(r'\n## ', rest)
            if next_section:
                end = start + len(ADAPTATION_HEADER) + next_section.start()
            else:
                end = len(content)
        content = content[:start] + adaptation_text + content[end:]
    else:
        # Append at end
        content = content.rstrip() + "\n\n" + adaptation_text

    atomic_write_text(soul_path, content)
    return True


def check_cap(role):
    """Check if a role's adaptation section exceeds the line cap.

    Returns (line_count, exceeds_cap).
    """
    section = render_adaptation_section(role)
    line_count = len([l for l in section.splitlines() if l.strip()])
    return line_count, line_count > LINE_CAP


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    cmd = sys.argv[1]

    if cmd == "render":
        if len(sys.argv) < 3:
            print("Usage: soul_adaptation.py render <role>", file=sys.stderr)
            return 2
        role = sys.argv[2]
        ok = render_soul(role)
        if ok:
            print(f"Rendered {role} SOUL.md with current adaptations")
        return 0 if ok else 1

    elif cmd == "add":
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("cmd")
        parser.add_argument("role")
        parser.add_argument("--category", required=True)
        parser.add_argument("--signal", required=True)
        parser.add_argument("--task", default=None)
        args = parser.parse_args()
        entry = add_adaptation(args.role, args.category, args.signal, args.task)
        print(f"Added: {entry}")
        return 0

    elif cmd == "check-cap":
        if len(sys.argv) < 3:
            print("Usage: soul_adaptation.py check-cap <role>", file=sys.stderr)
            return 2
        role = sys.argv[2]
        count, exceeds = check_cap(role)
        print(json.dumps({"role": role, "lines": count, "cap": LINE_CAP, "exceeds": exceeds}))
        return 0

    elif cmd == "list":
        if len(sys.argv) < 3:
            print("Usage: soul_adaptation.py list <role>", file=sys.stderr)
            return 2
        role = sys.argv[2]
        entries = get_adaptations(role)
        print(json.dumps(entries, indent=2))
        return 0

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
