#!/usr/bin/env python3
"""SquidSquad vault entity extraction — detect entities from running context.

Pattern-matches entity types from text: business names, people, URLs,
projects, and recurring patterns/preferences. Returns structured JSON
for vault-remember to create/update notes.

Usage:
    python scripts/vault_entity.py extract "<text>"
    python scripts/vault_entity.py extract --file <path>
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
