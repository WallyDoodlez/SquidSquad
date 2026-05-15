#!/usr/bin/env python3
"""SquidSquad vault validation — field checks, wikilinks, structure.

Single source of truth for vault integrity checks.

Usage:
    python scripts/vault_check.py validate           # Full vault validation
    python scripts/vault_check.py check-frontmatter   # Validate frontmatter in galaxy notes
    python scripts/vault_check.py check-wikilinks     # Find broken wikilinks
    python scripts/vault_check.py check-structure      # Validate PARAG directory structure
    python scripts/vault_check.py list-orphans         # Notes not linked from anywhere
    python scripts/vault_check.py --help
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
VAULT_DIR = REPO_ROOT / ".squidsquad" / "vault"

PARAG_DIRS = ["projects", "areas", "resources", "archives", "galaxy"]
VALID_GALAXY_PREFIXES = ("decision-", "pattern-", "learning-", "style-")
REQUIRED_FM_FIELDS = {"type", "tags", "created", "updated", "owner", "status", "confidence"}
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
    """Validate PARAG directory structure."""
    issues = []
    if not VAULT_DIR.exists():
        issues.append("Vault directory missing: .squidsquad/vault/")
        print(f"FAIL: {issues[0]}")
        return issues

    for dirname in PARAG_DIRS:
        path = VAULT_DIR / dirname
        if not path.exists():
            issues.append(f"Missing PARAG directory: vault/{dirname}/")

    briefing = VAULT_DIR / "BRIEFING.md"
    if not briefing.exists():
        issues.append("Missing BRIEFING.md")

    if issues:
        for i in issues:
            print(f"FAIL: {i}")
    else:
        print("OK: Vault structure valid")
    return issues


def check_frontmatter():
    """Validate frontmatter in galaxy notes."""
    issues = []
    galaxy_dir = VAULT_DIR / "galaxy"
    if not galaxy_dir.exists():
        print("SKIP: No galaxy directory")
        return issues

    for note in galaxy_dir.glob("*.md"):
        if note.name == ".gitkeep":
            continue

        # Check prefix
        if not any(note.name.startswith(p) for p in VALID_GALAXY_PREFIXES):
            issues.append(f"{note.name}: invalid prefix (expected: {VALID_GALAXY_PREFIXES})")

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
