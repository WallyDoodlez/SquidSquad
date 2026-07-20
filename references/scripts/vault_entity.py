#!/usr/bin/env python3
"""SquidSquad vault entity extraction — detect entities from running context.

Pattern-matches entity types from text: business names, people, URLs,
projects, and recurring patterns/preferences. Returns structured JSON
for vault-remember to create/update notes.

Usage:
    python scripts/vault_entity.py extract "<text>"
    python scripts/vault_entity.py extract --file <path>
    python scripts/vault_entity.py template-for <type> [--vault <path>]   # #13858: resolved template path (or GENERIC)
    python scripts/vault_entity.py create <type> <slug> [--vault <path>]  # #13858: materialize a note from its template
    python scripts/vault_entity.py --help

Exit codes:
    0 — success (JSON output)
    1 — no entities found
    2 — usage error
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
TEMPLATES_DIR = REPO_ROOT / "references" / "vault-templates"
sys.path.insert(0, str(SCRIPT_DIR))


# ---------------------------------------------------------------------------
# Registry-derived template resolution (#13858, VAULT-ARCH 3.5 / 8.4)
# ---------------------------------------------------------------------------


def resolve_template(note_type, vault_dir=None):
    """Resolve the template for a registered type: <type>.md from
    references/vault-templates/, falling back to the generic skeleton for
    custom types without a shipped template. Returns (path, is_generic).
    Raises ValueError for a type not registered in vault-schema.json."""
    import vault_check
    schema = vault_check._load_schema(vault_dir)
    if note_type not in schema["types"]:
        raise ValueError(
            f"type '{note_type}' is not registered in vault-schema.json "
            f"(registered: {sorted(schema['types'])})")
    candidate = TEMPLATES_DIR / f"{note_type}.md"
    if candidate.is_file():
        return candidate, False
    return TEMPLATES_DIR / "_generic.md", True


def create_note(note_type, slug, vault_dir=None, today=None):
    """Materialize a template into a new note (VAULT-ARCH 8.4): resolve by
    registered type, stamp type/created/updated, honor the type's declared
    prefix, write into the type's registered folder. Refuses to overwrite.
    Returns the created path."""
    import datetime
    import vault_check
    if not slug or not re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", slug) or ".." in slug:
        raise ValueError(f"invalid slug: {slug!r} (alnum start; alnum/dot/dash/"
                         f"underscore only; no path traversal)")
    vd = Path(vault_dir) if vault_dir is not None else vault_check.VAULT_DIR
    schema = vault_check._load_schema(vd)
    template, is_generic = resolve_template(note_type, vd)
    reg = schema["types"][note_type]
    prefix = reg.get("prefix") or ""
    name = slug if not prefix or slug.startswith(prefix) else prefix + slug
    dest_dir = vd / reg["folder"]
    dest = dest_dir / f"{name}.md"
    if dest.exists():
        raise FileExistsError(f"note already exists: {dest}")
    stamp = today or datetime.date.today().isoformat()
    body = template.read_text(encoding="utf-8")
    body = body.replace("type: {type}", f"type: {note_type}")
    body = body.replace("created: YYYY-MM-DD", f"created: {stamp}")
    body = body.replace("updated: YYYY-MM-DD", f"updated: {stamp}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    return dest


# ---------------------------------------------------------------------------
# Entity patterns
# ---------------------------------------------------------------------------

# URL pattern
URL_PATTERN = re.compile(
    r'https?://[^\s<>\'")\]]+',
    re.IGNORECASE,
)

# Capitalized multi-word names (potential company/person names)
# Matches "Acme Corp", "Sarah Johnson", etc.
PROPER_NAME_PATTERN = re.compile(
    r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b'
)

# Project references (common patterns)
PROJECT_PATTERN = re.compile(
    r'(?:the\s+)?(?:project|repo|repository|codebase)\s+["\']?(\w[\w-]+)["\']?',
    re.IGNORECASE,
)

# Preference/pattern markers
PREFERENCE_MARKERS = [
    "always use", "never use", "prefer", "we use", "i like",
    "i want", "i need", "make sure to", "don't", "do not",
    "should always", "should never", "convention is",
    "standard is", "rule is", "pattern is",
]

# Common non-entity proper nouns to filter out
NOISE_WORDS = {
    "Monday", "Tuesday", "Wednesday", "Thursday", "Friday",
    "Saturday", "Sunday", "January", "February", "March",
    "April", "May", "June", "July", "August", "September",
    "October", "November", "December", "The", "This", "That",
    "What", "When", "Where", "Which", "Status", "Steps",
    "Expected", "Actual", "Fixed", "Error", "Warning",
    "Claude", "GitHub", "Python", "Linux", "Windows", "Docker",
    "Task", "Issue", "Pull Request",
}


def _is_noise_name(name):
    """Check if a proper name is a common non-entity word."""
    return name in NOISE_WORDS or name.split()[0] in NOISE_WORDS


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------


def extract_entities(text):
    """Extract entities from text. Returns list of entity dicts.

    Each entity: {type, value, context, confidence}
    Types: url, person, business, project, preference
    """
    entities = []
    seen = set()

    # URLs
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:)")
        if url not in seen:
            seen.add(url)
            entities.append({
                "type": "url",
                "value": url,
                "context": _get_context(text, match.start(), match.end()),
                "confidence": "high",
            })

    # Proper names (potential people or businesses)
    for match in PROPER_NAME_PATTERN.finditer(text):
        name = match.group(1)
        if name not in seen and not _is_noise_name(name):
            seen.add(name)
            # Heuristic: check name itself and trailing context for type signals
            name_lower = name.lower()
            after = text[match.end():match.end() + 30].lower()
            if any(w in name_lower for w in [" corp", " inc", " ltd", " llc", " co"]):
                entity_type = "business"  # business suffix in name itself
            elif any(w in after for w in [" corp", " inc", " ltd", " llc", " co"]):
                entity_type = "business"  # business suffix after name
            elif any(w in after for w in [" said", " asked", " from ", " at ", "'s "]):
                entity_type = "person"
            else:
                entity_type = "unknown"  # ambiguous — could be person, place, or brand (#7615)
            entities.append({
                "type": entity_type,
                "value": name,
                "context": _get_context(text, match.start(), match.end()),
                "confidence": "low" if entity_type == "unknown" else "medium",
            })

    # Projects
    for match in PROJECT_PATTERN.finditer(text):
        project = match.group(1)
        if project not in seen and len(project) > 2:
            seen.add(project)
            entities.append({
                "type": "project",
                "value": project,
                "context": _get_context(text, match.start(), match.end()),
                "confidence": "medium",
            })

    # Preferences/patterns
    text_lower = text.lower()
    for marker in PREFERENCE_MARKERS:
        idx = text_lower.find(marker)
        while idx != -1:
            # Extract the preference (rest of sentence)
            end = text.find(".", idx)
            if end == -1:
                end = min(idx + 100, len(text))
            pref_text = text[idx:end].strip()
            if pref_text not in seen and len(pref_text) > 10:
                seen.add(pref_text)
                entities.append({
                    "type": "preference",
                    "value": pref_text,
                    "context": _get_context(text, idx, end),
                    "confidence": "medium",
                })
            idx = text_lower.find(marker, idx + len(marker))

    return entities


def _get_context(text, start, end, window=50):
    """Get surrounding context for an entity match."""
    ctx_start = max(0, start - window)
    ctx_end = min(len(text), end + window)
    return text[ctx_start:ctx_end].strip()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("--help", "-h"):
        print(__doc__)
        return 0

    if args[0] == "template-for":
        if len(args) < 2:
            print("Usage: vault_entity.py template-for <type> [--vault <path>]", file=sys.stderr)
            return 2
        vault = args[args.index("--vault") + 1] if "--vault" in args else None
        try:
            path, is_generic = resolve_template(args[1], vault)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        print(json.dumps({"template": str(path), "generic": is_generic}))
        return 0

    if args[0] == "create":
        if len(args) < 3:
            print("Usage: vault_entity.py create <type> <slug> [--vault <path>]", file=sys.stderr)
            return 2
        vault = args[args.index("--vault") + 1] if "--vault" in args else None
        try:
            dest = create_note(args[1], args[2], vault)
        except (ValueError, FileExistsError) as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        print(json.dumps({"created": str(dest)}))
        return 0

    if args[0] != "extract":
        print(f"Unknown command: {args[0]}", file=sys.stderr)
        return 2

    # Get text from args or file
    text = ""
    if "--file" in args:
        idx = args.index("--file")
        if idx + 1 < len(args):
            path = Path(args[idx + 1])
            if not path.exists():
                print(f"File not found: {path}", file=sys.stderr)
                return 2
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError) as e:
                print(f"Cannot read {path}: {e}", file=sys.stderr)
                return 2
    else:
        # Remaining args after "extract" are the text
        text = " ".join(args[1:])

    if not text.strip():
        print("No text provided", file=sys.stderr)
        return 2

    entities = extract_entities(text)

    if not entities:
        print(json.dumps({"entities": [], "count": 0}))
        return 1

    print(json.dumps({
        "entities": entities,
        "count": len(entities),
    }, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
