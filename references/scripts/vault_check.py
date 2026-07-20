#!/usr/bin/env python3
"""SquidSquad vault validation — field checks, wikilinks, structure.

Single source of truth for vault integrity checks.

Usage:
    python scripts/vault_check.py validate           # Full vault validation
    python scripts/vault_check.py check-frontmatter   # Validate frontmatter in galaxy notes
    python scripts/vault_check.py check-wikilinks     # Find broken wikilinks
    python scripts/vault_check.py check-size           # Warn on galaxy notes >500 lines (advisory)
    python scripts/vault_check.py check-structure      # Registry-driven layout + folder/prefix/type consistency (#13858)
    python scripts/vault_check.py check-hub-links      # Level-2: budgeted notes with zero hub links (advisory, #13858)
    python scripts/vault_check.py list-orphans         # Notes not linked from anywhere
    python scripts/vault_check.py --help
"""

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
VAULT_DIR = REPO_ROOT / ".squidsquad" / "vault"

# Fallback taxonomy when no registry is readable anywhere (matches the
# pre-#13858 hardcode so a registry-less v1 vault validates unchanged).
PARAG_DIRS = ["projects", "areas", "resources", "archives", "galaxy"]
VALID_GALAXY_PREFIXES = ("decision-", "pattern-", "learning-", "style-")

# Legacy prefixes grandfathered until the M-track migration (#13862)
# reclassifies their notes (style-* -> pattern-*, VAULT-ARCH §4.2). Checks
# accept them without a registry entry so the live vault never turns red on
# content the migration owns (§9.9: vault checks never block).
LEGACY_GRANDFATHERED_PREFIXES = ("style-",)


def _load_schema(vault_dir=None):
    """Load the §3.1 type registry: <vault>/vault-schema.json, falling back
    to the framework seed, then to the pre-#13858 hardcoded PARAG shape.
    Returns {"types": {...}} — always a dict, never raises (§9.9)."""
    vd = Path(vault_dir) if vault_dir is not None else VAULT_DIR
    for candidate in (vd / "vault-schema.json",
                      REPO_ROOT / "references" / "vault-schema-default.json"):
        try:
            parsed = json.loads(candidate.read_text(encoding="utf-8"))
            types = parsed.get("types")
            if isinstance(types, dict) and types:
                return {"types": types}
        except (OSError, ValueError):
            continue
    # Hardcoded fallback mirrors the v1 PARAG shape.
    return {"types": {
        "project": {"folder": "projects", "traversal": "free", "hub": True},
        "area": {"folder": "areas", "traversal": "free", "hub": True},
        "resource": {"folder": "resources", "traversal": "free", "hub": False},
        "decision": {"folder": "galaxy", "traversal": "budgeted", "prefix": "decision-"},
        "pattern": {"folder": "galaxy", "traversal": "budgeted", "prefix": "pattern-"},
        "learning": {"folder": "galaxy", "traversal": "budgeted", "prefix": "learning-"},
        "archive": {"folder": "archives", "traversal": "free", "hub": False},
    }}


def _schema_views(schema):
    """Derive the lookup views checks need from a loaded registry."""
    types = schema["types"]
    folders = []
    folder_types = {}      # folder -> [type names]
    prefix_to_type = {}    # declared prefix -> type name
    hub_types = set()
    budgeted_types = set()
    for name, t in types.items():
        if not isinstance(t, dict) or not t.get("folder"):
            continue
        f = t["folder"]
        if f not in folders:
            folders.append(f)
        folder_types.setdefault(f, []).append(name)
        if t.get("prefix"):
            prefix_to_type[t["prefix"]] = name
        if t.get("hub"):
            hub_types.add(name)
        if t.get("traversal") == "budgeted":
            budgeted_types.add(name)
    return {
        "types": types,
        "folders": folders,
        "folder_types": folder_types,
        "prefix_to_type": prefix_to_type,
        "hub_types": hub_types,
        "budgeted_types": budgeted_types,
    }
REQUIRED_FM_FIELDS = {"type", "tags", "created", "updated", "owner", "status", "confidence", "source"}
# Galaxy notes over this many lines are flagged for splitting (#13043 /
# VAULT-ARCH §4.3 + vault-protocol Level-1 check 5). Galaxy only — areas/
# projects/resources are exempt.
GALAXY_MAX_LINES = 500
VALID_CONFIDENCE = {"high", "medium", "low"}
VALID_SOURCES = {"conversation", "code", "review", "observation", "research"}


def _parse_frontmatter(text):
    """Parse YAML frontmatter from markdown text. Returns dict or None."""
    if not text.startswith("---"):
        return None
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None
    # Simple YAML-like parser (no pyyaml dependency)
    fm = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm


def _get_all_notes():
    """Get all .md files in the vault (excluding .gitkeep)."""
    notes = {}
    for md in VAULT_DIR.rglob("*.md"):
        if md.name == ".gitkeep":
            continue
        rel = md.relative_to(VAULT_DIR).as_posix()
        notes[rel] = md
    return notes


def _extract_wikilinks(text):
    """Extract all [[wikilink]] references from text body.

    Strips pipe-alias syntax: [[note|alias]] → note (#8200).
    """
    raw = re.findall(r'\[\[([^\]]+)\]\]', text)
    return [link.split("|")[0].strip() for link in raw]


def check_structure():
    """Validate the vault layout against the type registry (#13858).

    VAULT-ARCH §4.2a, registry-driven — a custom type registered in
    vault-schema.json gets validation for free:
      1. every registered folder exists (+ BRIEFING.md at the root);
      2. folder ↔ type: a note's `type:` must be registered to its folder;
      3. prefix ↔ type: where a type declares a `prefix`, filenames carrying
         that prefix must be that type (and prefixed-folder files must carry
         a registered prefix).
    Unregistered types are a WARN, not a FAIL — existing content awaiting
    the M-track migration (#13862) must not turn the vault red (§9.9).
    """
    issues = []
    if not VAULT_DIR.exists():
        issues.append("Vault directory missing: .squidsquad/vault/")
        print(f"FAIL: {issues[0]}")
        return issues

    views = _schema_views(_load_schema())

    for dirname in views["folders"]:
        if not (VAULT_DIR / dirname).exists():
            issues.append(f"Missing registered directory: vault/{dirname}/")

    if not (VAULT_DIR / "BRIEFING.md").exists():
        issues.append("Missing BRIEFING.md")

    warns = []
    for folder in views["folders"]:
        fdir = VAULT_DIR / folder
        if not fdir.exists():
            continue
        for md in fdir.glob("*.md"):
            if md.name in (".gitkeep", "README.md", "INDEX.md", "_template.md"):
                continue
            fm = _parse_frontmatter(md.read_text(encoding="utf-8")) or {}
            ntype = fm.get("type", "")
            reg = views["types"].get(ntype)
            if reg is None:
                if not md.name.startswith(LEGACY_GRANDFATHERED_PREFIXES):
                    warns.append(f"{folder}/{md.name}: type '{ntype}' not in "
                                 f"vault-schema.json (M-track #13862 migrates legacy content)")
                continue
            if reg.get("folder") != folder:
                issues.append(f"{folder}/{md.name}: type '{ntype}' is registered "
                              f"to folder '{reg.get('folder')}' (folder<->type, VAULT-ARCH 4.2a)")
            declared_prefix = reg.get("prefix")
            if declared_prefix and not md.name.startswith(declared_prefix):
                issues.append(f"{folder}/{md.name}: type '{ntype}' declares prefix "
                              f"'{declared_prefix}' (prefix<->type, VAULT-ARCH 4.2a)")

    for w in warns:
        print(f"WARN: {w}")
    if issues:
        for i in issues:
            print(f"FAIL: {i}")
    else:
        print("OK: Vault structure valid (registry-driven)")
    return issues


def check_frontmatter():
    """Validate frontmatter in galaxy notes."""
    issues = []
    galaxy_dir = VAULT_DIR / "galaxy"
    if not galaxy_dir.exists():
        print("SKIP: No galaxy directory")
        return issues

    # Registry-declared prefixes (+ legacy grandfathered set, #13862) —
    # replaces the hardcoded tuple (#13858).
    views = _schema_views(_load_schema())
    valid_prefixes = tuple(views["prefix_to_type"]) + LEGACY_GRANDFATHERED_PREFIXES

    for note in galaxy_dir.glob("*.md"):
        if note.name == ".gitkeep":
            continue

        # Check prefix
        if not any(note.name.startswith(p) for p in valid_prefixes):
            issues.append(f"{note.name}: invalid prefix (expected: {valid_prefixes})")

        text = note.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        if fm is None:
            issues.append(f"{note.name}: missing frontmatter")
            continue

        # Check required fields
        missing = REQUIRED_FM_FIELDS - set(fm.keys())
        if missing:
            issues.append(f"{note.name}: missing fields: {missing}")

        # Check confidence
        if "confidence" in fm and fm["confidence"] not in VALID_CONFIDENCE:
            issues.append(f"{note.name}: invalid confidence '{fm['confidence']}'")

        # Check source
        if "source" in fm and fm["source"] not in VALID_SOURCES:
            issues.append(f"{note.name}: invalid source '{fm['source']}'")

    if issues:
        for i in issues:
            print(f"FAIL: {i}")
    else:
        print("OK: All galaxy note frontmatter valid")
    return issues


def check_galaxy_size():
    """Warn on galaxy notes exceeding GALAXY_MAX_LINES — suggest splitting.

    Level-1 check 5 (vault-protocol.md): galaxy notes only; areas/projects/
    resources are exempt (those legitimately grow). Advisory — returns a
    warning list but does NOT fail validation, since an oversized note is a
    split-suggestion, not a structural error (#13043).
    """
    warnings = []
    galaxy_dir = VAULT_DIR / "galaxy"
    if not galaxy_dir.exists():
        return warnings

    for note in sorted(galaxy_dir.glob("*.md")):
        if note.name == ".gitkeep":
            continue
        line_count = note.read_text(encoding="utf-8").count("\n") + 1
        if line_count > GALAXY_MAX_LINES:
            warnings.append(
                f"{note.name}: {line_count} lines (> {GALAXY_MAX_LINES}) — "
                "consider splitting into focused notes"
            )

    for w in warnings:
        print(f"[vault-check] WARN: {w}")
    if not warnings:
        print(f"OK: All galaxy notes within {GALAXY_MAX_LINES} lines")
    return warnings


def check_wikilinks():
    """Find broken wikilinks (references to non-existent notes)."""
    issues = []
    all_notes = _get_all_notes()
    # Build a set of note names (without path or extension)
    note_names = set()
    for rel_path in all_notes:
        name = Path(rel_path).stem
        note_names.add(name)

    for rel_path, note_path in all_notes.items():
        text = note_path.read_text(encoding="utf-8")
        links = _extract_wikilinks(text)
        for link in links:
            if link not in note_names:
                issues.append(f"{rel_path}: broken link [[{link}]]")

    if issues:
        for i in issues:
            print(f"WARN: {i}")
    else:
        print("OK: All wikilinks resolve")
    return issues


def check_hub_links():
    """Level-2 sweep (#13858, VAULT-ARCH §3.3): flag budgeted-type notes
    (galaxy leaves) that wikilink to ZERO hub-type notes. "Orphaned from the
    graph" is a distinct, cheaper-to-fix defect from "orphaned from any other
    note" (list_orphans). Advisory only — a maintenance signal for the
    improvement scan, never a write-time block.
    """
    warnings = []
    views = _schema_views(_load_schema())
    if not views["hub_types"] or not views["budgeted_types"]:
        print("SKIP: registry declares no hub or no budgeted types")
        return warnings

    all_notes = _get_all_notes()
    # slug -> type for every note, so link targets can be classified.
    slug_type = {}
    for rel, path in all_notes.items():
        fm = _parse_frontmatter(path.read_text(encoding="utf-8")) or {}
        slug_type[Path(rel).stem] = fm.get("type", "")

    for rel, path in sorted(all_notes.items()):
        ntype = slug_type.get(Path(rel).stem, "")
        if ntype not in views["budgeted_types"]:
            continue
        links = _extract_wikilinks(path.read_text(encoding="utf-8"))
        if not any(slug_type.get(l, "") in views["hub_types"] for l in links):
            warnings.append(f"{rel}: no wikilink to any hub note "
                            f"(graph-orphaned, VAULT-ARCH 3.3)")

    for w in warnings:
        print(f"[vault-check] WARN: {w}")
    if not warnings:
        print("OK: every budgeted-type note links to at least one hub")
    return warnings


def list_orphans():
    """Find notes that no other note links to."""
    all_notes = _get_all_notes()
    all_links = set()

    for note_path in all_notes.values():
        text = note_path.read_text(encoding="utf-8")
        for link in _extract_wikilinks(text):
            all_links.add(link)

    orphans = []
    for rel_path in all_notes:
        name = Path(rel_path).stem
        # Skip BRIEFING.md and top-level files
        if "/" not in rel_path:
            continue
        if name not in all_links:
            orphans.append(rel_path)

    if orphans:
        for o in orphans:
            print(f"ORPHAN: {o}")
    else:
        print("OK: No orphan notes")
    return orphans


def suggest_connections(note_path):
    """Suggest wikilinks for a note based on tag and keyword overlap.

    Scans the vault for notes with overlapping tags or keywords.
    Returns list of {target, score, reason} suggestions.
    """
    note_path = Path(note_path)
    if not note_path.exists():
        return []

    text = note_path.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)
    if not fm:
        return []

    note_name = note_path.stem
    note_tags = _parse_tag_string(fm.get("tags", ""))
    note_words = set(note_name.replace("-", " ").lower().split())

    # Get existing wikilinks to avoid suggesting already-linked notes
    existing_links = set(_extract_wikilinks(text))

    suggestions = []
    all_notes = _get_all_notes()

    for rel_path, other_path in all_notes.items():
        other_name = Path(rel_path).stem
        if other_name == note_name:
            continue
        if other_name in existing_links:
            continue

        other_text = other_path.read_text(encoding="utf-8")
        other_fm = _parse_frontmatter(other_text)
        other_tags = _parse_tag_string(other_fm.get("tags", "")) if other_fm else set()
        other_words = set(other_name.replace("-", " ").lower().split())

        # Calculate overlap
        tag_overlap = note_tags & other_tags
        word_overlap = note_words & other_words

        if tag_overlap or word_overlap:
            score = len(tag_overlap) * 2 + len(word_overlap)
            if score >= 2:
                reasons = []
                if tag_overlap:
                    reasons.append(f"shared tags: {', '.join(sorted(tag_overlap))}")
                if word_overlap:
                    reasons.append(f"shared keywords: {', '.join(sorted(word_overlap))}")
                suggestions.append({
                    "target": other_name,
                    "path": rel_path,
                    "score": score,
                    "reason": "; ".join(reasons),
                })

    # Sort by score descending, return top 5
    suggestions.sort(key=lambda x: x["score"], reverse=True)
    top = suggestions[:5]

    if top:
        for s in top:
            print(f"[vault-check] Suggest link: [[{s['target']}]] — {s['reason']}")

    return top


def _strip_galaxy_prefix(name):
    """Strip common galaxy note type prefixes from a lowercased name."""
    for prefix in ("decision ", "pattern ", "learning ", "style "):
        if name.startswith(prefix):
            return name[len(prefix):]
    return name


def _parse_tag_string(raw):
    """Parse a tags field value into a set of lowercase tag strings."""
    if not raw:
        return set()
    # Handle YAML list format [tag1, tag2] or plain comma-separated
    cleaned = str(raw).replace("[", "").replace("]", "")
    return {t.strip().lower() for t in cleaned.split(",") if t.strip()}


def dedup_check(title, tags=""):
    """Check for near-duplicate vault notes by keyword overlap.

    Returns up to 3 candidate matches with overlap scores.
    Exit code 0 if no matches, 1 if matches found.
    """
    # Extract keywords from candidate title (lowercase, strip common prefixes)
    title_lower = _strip_galaxy_prefix(title.lower().replace("-", " "))
    candidate_words = set(title_lower.split())

    # Extract tag keywords
    tag_words = _parse_tag_string(tags)

    all_candidate = candidate_words | tag_words
    if not all_candidate:
        print("No keywords to match")
        return []

    matches = []
    all_notes = _get_all_notes()

    for rel_path, note_path in all_notes.items():
        # Skip non-galaxy notes for title matching
        note_name = _strip_galaxy_prefix(Path(rel_path).stem.lower().replace("-", " "))
        note_words = set(note_name.split())

        # Also check tags from frontmatter
        text = note_path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        note_tags = _parse_tag_string(fm.get("tags", "")) if fm else set()

        all_note = note_words | note_tags
        if not all_note:
            continue

        # Calculate overlap
        overlap = all_candidate & all_note
        if not overlap:
            continue

        score = len(overlap) / max(len(all_candidate), 1) * 100
        if score >= 30:  # Minimum 30% overlap to report
            matches.append((score, rel_path, overlap))

    # Sort by score descending, return top 3
    matches.sort(key=lambda x: x[0], reverse=True)
    top = matches[:3]

    if top:
        for score, path, overlap in top:
            print(f"MATCH ({score:.0f}%): {path} — shared: {', '.join(sorted(overlap))}")
    else:
        print("No near-duplicates found")

    return top


def validate():
    """Run all vault checks."""
    all_issues = []
    all_issues.extend(check_structure())
    all_issues.extend(check_frontmatter())
    all_issues.extend(check_wikilinks())
    # Galaxy size is advisory (split-suggestion) — surfaced but not counted
    # toward the pass/fail total (#13043).
    check_galaxy_size()
    list_orphans()

    total = len(all_issues)
    if total:
        print(f"\n{total} issue(s) found")
        return False
    print("\nVault validation passed")
    return True


def main():
    args = sys.argv[1:]
    if not args or args[0] == "--help":
        print(__doc__)
        sys.exit(0)

    cmd = args[0]
    if cmd == "validate":
        sys.exit(0 if validate() else 1)
    elif cmd == "check-structure":
        issues = check_structure()
        sys.exit(1 if issues else 0)
    elif cmd == "check-frontmatter":
        issues = check_frontmatter()
        sys.exit(1 if issues else 0)
    elif cmd == "check-wikilinks":
        issues = check_wikilinks()
        sys.exit(1 if issues else 0)
    elif cmd == "check-size":
        # Advisory: always exits 0 (warnings, not failures).
        check_galaxy_size()
        sys.exit(0)
    elif cmd == "check-hub-links":
        # Advisory Level-2 sweep (#13858, §3.3): always exits 0.
        check_hub_links()
        sys.exit(0)
    elif cmd == "list-orphans":
        list_orphans()
    elif cmd == "dedup-check":
        title = None
        tags = ""
        i = 1
        while i < len(args):
            if args[i] == "--title" and i + 1 < len(args):
                title = args[i + 1]
                i += 2
            elif args[i] == "--tags" and i + 1 < len(args):
                tags = args[i + 1]
                i += 2
            else:
                i += 1
        if not title:
            print("Usage: vault_check.py dedup-check --title <title> [--tags <tags>]", file=sys.stderr)
            sys.exit(2)
        matches = dedup_check(title, tags)
        sys.exit(1 if matches else 0)
    elif cmd == "suggest-connections":
        if len(args) < 2:
            print("Usage: vault_check.py suggest-connections <note-path>", file=sys.stderr)
            sys.exit(2)
        suggestions = suggest_connections(args[1])
        sys.exit(0)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
