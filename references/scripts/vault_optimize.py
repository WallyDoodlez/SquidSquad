#!/usr/bin/env python3
"""SquidSquad vault optimizer — on-demand vault maintenance.

Covers 5 areas: prune (auto-archive stale+orphan), consolidate candidates,
reindex (links), confidence decay, relevance scoring.

Usage:
    python scripts/vault_optimize.py full-sweep [--dry-run]       # Full optimize pass
    python scripts/vault_optimize.py prune-scan [--dry-run]       # Archive stale+orphan notes
    python scripts/vault_optimize.py consolidate-scan [--dry-run]  # Detect merge candidates
    python scripts/vault_optimize.py decay-apply [--dry-run]       # Confidence decay
    python scripts/vault_optimize.py reindex                       # Rebuild links index
    python scripts/vault_optimize.py relevance-report              # Update relevance scores
    python scripts/vault_optimize.py pending-count                 # Count pending questions
    python scripts/vault_optimize.py add-question --agent <r> --note <path> --question <q>
    python scripts/vault_optimize.py --help

Exit codes:
    0 — success
    1 — error
    2 — usage error
"""

import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
VAULT_DIR = REPO_ROOT / ".squidsquad" / "vault"
PENDING_FILE = VAULT_DIR / ".pending-questions"
RELEVANCE_FILE = VAULT_DIR / ".relevance-index.json"
LOCK_FILE = VAULT_DIR / ".optimize-lock"
CONFIG_PATH = REPO_ROOT / ".squidsquad" / "config.md"

STALE_DAYS = 60
MIN_VAULT_SIZE = 20
LOCK_TTL = 30  # seconds


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_frontmatter(text):
    """Extract YAML-ish frontmatter as a dict."""
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    fm_text = text[3:end].strip()
    result = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            result[key.strip()] = val.strip()
    return result


def _get_all_notes():
    """Return {relative_path: absolute_Path} for all .md files in vault."""
    if not VAULT_DIR.exists():
        return {}
    notes = {}
    for md in VAULT_DIR.rglob("*.md"):
        if md.name.startswith(".") or ".obsidian" in str(md):
            continue
        rel = md.relative_to(VAULT_DIR)
        notes[str(rel).replace("\\", "/")] = md
    return notes


def _extract_wikilinks(text):
    """Extract wikilink targets from text body (after frontmatter)."""
    # Skip frontmatter
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            body = text[end + 3:]
    return set(re.findall(r"\[\[([^\]]+)\]\]", body))


def _count_notes():
    """Count total .md files in vault (excluding dotfiles)."""
    return len(_get_all_notes())


def _is_config_enabled():
    """Check if vault optimize is enabled in config.md."""
    if not CONFIG_PATH.exists():
        return True  # Default enabled
    try:
        text = CONFIG_PATH.read_text(encoding="utf-8")
        m = re.search(r"Vault Optimize.*?Enabled.*?:\s*(yes|no)", text, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).lower() == "yes"
    except Exception:
        pass
    return True  # Default enabled


def _acquire_lock():
    """Acquire optimize lock. Returns True if acquired."""
    try:
        if LOCK_FILE.exists():
            mtime = LOCK_FILE.stat().st_mtime
            if time.time() - mtime < LOCK_TTL:
                return False
            LOCK_FILE.unlink(missing_ok=True)
        LOCK_FILE.write_text(str(os.getpid()), encoding="utf-8")
        return True
    except Exception:
        return False


def _release_lock():
    """Release optimize lock."""
    try:
        LOCK_FILE.unlink(missing_ok=True)
    except Exception:
        pass


def _check_guards():
    """Check lock file and vault threshold. Returns (ok, reason) tuple."""
    if not _is_config_enabled():
        return False, "Vault optimize disabled in config.md"
    note_count = _count_notes()
    if note_count < MIN_VAULT_SIZE:
        return False, f"Vault too small ({note_count} notes, minimum {MIN_VAULT_SIZE})"
    if not _acquire_lock():
        return False, "Optimize lock held"
    return True, None


def _git_mv(src, dest):
    """Move a file using git mv to preserve history. Ensures dest parent exists."""
    dest_dir = Path(dest).parent
    dest_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "mv", str(src), str(dest)],
        capture_output=True, encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    if result.returncode != 0:
        raise RuntimeError(f"git mv failed: {result.stderr.strip()}")


def _rewrite_wikilinks_after_archive(note_name, notes):
    """Find all notes linking to note_name and append an archived comment."""
    for rel, path in notes.items():
        text = path.read_text(encoding="utf-8")
        if f"[[{note_name}]]" in text:
            comment = f"\n<!-- archived: [[{note_name}]] moved to archives/ -->"
            if comment.strip() not in text:
                path.write_text(text + comment, encoding="utf-8")


def _extract_keywords(text):
    """Extract simple keyword set from note body for consolidation analysis."""
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            body = text[end + 3:]
    # Extract words 4+ chars, lowercased, skip common stopwords
    stopwords = {"that", "this", "with", "from", "have", "been", "were", "will",
                 "they", "their", "them", "than", "into", "also", "when", "what",
                 "which", "about", "would", "could", "should", "there", "these",
                 "those", "each", "other", "some", "more", "very", "just", "only"}
    words = re.findall(r"[a-zA-Z]{4,}", body.lower())
    return {w for w in words if w not in stopwords}


# ---------------------------------------------------------------------------
# Prune — auto-archive stale+orphan galaxy notes
# ---------------------------------------------------------------------------

def prune(dry_run=False):
    """Archive galaxy notes that are both stale (>60 days) and orphaned (no inbound links).
    Also archives notes with status: superseded regardless of staleness/orphan status."""
    notes = _get_all_notes()
    cutoff = datetime.now() - timedelta(days=STALE_DAYS)
    archived = []

    # Build inbound link map
    inbound = {}
    for rel, path in notes.items():
        text = path.read_text(encoding="utf-8")
        for link in _extract_wikilinks(text):
            inbound.setdefault(link, set()).add(rel)

    for rel, path in notes.items():
        # Only prune galaxy/ notes
        if not rel.startswith("galaxy/"):
            continue

        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)

        # Grace period: use created frontmatter date instead of filesystem mtime
        created = fm.get("created", "")
        if created:
            try:
                created_date = datetime.strptime(created, "%Y-%m-%d")
                if created_date.date() == datetime.now().date():
                    continue
            except ValueError:
                pass
        else:
            # Fallback: skip if no created date available
            continue

        note_name = path.stem
        should_archive = False

        # Superseded notes are archived regardless of staleness/orphan
        if fm.get("status", "").strip() == "superseded":
            should_archive = True
        else:
            # Check staleness
            updated = fm.get("updated", "")
            if not updated:
                continue
            try:
                updated_date = datetime.strptime(updated, "%Y-%m-%d")
            except ValueError:
                continue
            if updated_date >= cutoff:
                continue

            # Check orphan status
            if note_name in inbound:
                continue  # Has inbound links — not orphan

            # Check status — only archive active notes
            if fm.get("status", "").strip() != "active":
                continue

            should_archive = True

        if not should_archive:
            continue

        # This note should be archived
        if dry_run:
            archived.append(f"[dry-run] would archive: {rel}")
        else:
            archives_dir = VAULT_DIR / "archives"
            archives_dir.mkdir(parents=True, exist_ok=True)
            dest = archives_dir / path.name
            if dest.exists():
                dest = archives_dir / f"{path.stem}-{int(time.time())}{path.suffix}"
            _git_mv(str(path), str(dest))
            _rewrite_wikilinks_after_archive(note_name, notes)
            archived.append(f"archived: {rel} -> archives/{dest.name}")

    return archived


# ---------------------------------------------------------------------------
# Consolidate scan — detect merge candidates among same-type galaxy notes
# ---------------------------------------------------------------------------

def consolidate_scan(dry_run=False):
    """Detect merge candidates among same-type galaxy notes via keyword overlap.
    Outputs candidates as pending questions — does NOT auto-merge."""
    notes = _get_all_notes()
    candidates = []

    # Group galaxy notes by type (from frontmatter)
    type_groups = {}
    note_keywords = {}
    for rel, path in notes.items():
        if not rel.startswith("galaxy/"):
            continue
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        note_type = fm.get("type", "").strip()
        if not note_type:
            continue
        type_groups.setdefault(note_type, []).append((rel, path))
        note_keywords[rel] = _extract_keywords(text)

    # For each type group, compare keyword overlap between pairs
    for note_type, group in type_groups.items():
        if len(group) < 2:
            continue
        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                rel_a, path_a = group[i]
                rel_b, path_b = group[j]
                kw_a = note_keywords.get(rel_a, set())
                kw_b = note_keywords.get(rel_b, set())
                if not kw_a or not kw_b:
                    continue
                overlap = kw_a & kw_b
                union = kw_a | kw_b
                if not union:
                    continue
                jaccard = len(overlap) / len(union)
                # Threshold: 40% keyword overlap suggests merge candidate
                if jaccard >= 0.4:
                    candidate = {
                        "type": note_type,
                        "note_a": rel_a,
                        "note_b": rel_b,
                        "overlap_ratio": round(jaccard, 2),
                        "shared_keywords": sorted(list(overlap))[:10],
                    }
                    candidates.append(candidate)
                    if not dry_run:
                        # Add as pending question
                        question = (
                            f"Consolidation candidate: {rel_a} and {rel_b} "
                            f"(type={note_type}, overlap={jaccard:.0%}). "
                            f"Shared keywords: {', '.join(sorted(list(overlap))[:5])}. "
                            f"Should these notes be merged?"
                        )
                        add_question("vault-optimize", rel_a, question)

    return candidates


# ---------------------------------------------------------------------------
# Confidence decay
# ---------------------------------------------------------------------------

def decay(dry_run=False):
    """Decay confidence from high->medium->low based on staleness.
    Skips notes tagged 'evergreen'. Appends changelog entry on decay."""
    notes = _get_all_notes()
    cutoff_medium = datetime.now() - timedelta(days=STALE_DAYS)
    cutoff_low = datetime.now() - timedelta(days=STALE_DAYS * 2)
    decayed = []

    for rel, path in notes.items():
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)

        # Skip evergreen notes
        tags = fm.get("tags", "")
        if "evergreen" in tags:
            continue

        updated = fm.get("updated", "")
        confidence = fm.get("confidence", "").strip()
        if not updated or not confidence:
            continue

        try:
            updated_date = datetime.strptime(updated, "%Y-%m-%d")
        except ValueError:
            continue

        new_confidence = None
        if confidence == "high" and updated_date < cutoff_medium:
            new_confidence = "medium"
        elif confidence == "medium" and updated_date < cutoff_low:
            new_confidence = "low"

        if new_confidence:
            if dry_run:
                decayed.append(f"[dry-run] {rel}: {confidence} -> {new_confidence}")
            else:
                today = datetime.now().strftime("%Y-%m-%d")
                new_text = text.replace(f"confidence: {confidence}", f"confidence: {new_confidence}", 1)
                new_text = re.sub(r"updated: \S+", f"updated: {today}", new_text, count=1)

                # Append changelog entry
                changelog_entry = f"- {today} — Confidence decayed by vault-optimize (staleness)."
                if "## Changelog" in new_text:
                    new_text = new_text.replace(
                        "## Changelog",
                        f"## Changelog\n{changelog_entry}",
                        1,
                    )
                else:
                    # Add a Changelog section at the end
                    new_text = new_text.rstrip() + f"\n\n## Changelog\n{changelog_entry}\n"

                path.write_text(new_text, encoding="utf-8")
                decayed.append(f"{rel}: {confidence} -> {new_confidence}")

    return decayed


# ---------------------------------------------------------------------------
# Reindex — rebuild links frontmatter from body wikilinks
# ---------------------------------------------------------------------------

def reindex():
    """Update links frontmatter in all notes to match body wikilinks."""
    notes = _get_all_notes()
    updated = []

    for rel, path in notes.items():
        text = path.read_text(encoding="utf-8")
        links = sorted(_extract_wikilinks(text))
        links_str = f"[{', '.join(links)}]" if links else "[]"

        fm = _parse_frontmatter(text)
        current_links = fm.get("links", "[]").strip()

        if current_links != links_str:
            new_text = re.sub(r"links: .*", f"links: {links_str}", text, count=1)
            if new_text == text and "links:" not in text:
                # No existing links field — insert before closing ---
                end = text.find("---", 3)
                if end != -1:
                    new_text = text[:end] + f"links: {links_str}\n" + text[end:]
            if new_text != text:
                path.write_text(new_text, encoding="utf-8")
                updated.append(f"{rel}: links -> {links_str}")

    return updated


# ---------------------------------------------------------------------------
# Relevance scoring
# ---------------------------------------------------------------------------

def relevance():
    """Compute relevance scores based on link count + recency + confidence."""
    notes = _get_all_notes()
    scores = {}

    # Build inbound link counts
    inbound_count = {}
    for rel, path in notes.items():
        text = path.read_text(encoding="utf-8")
        for link in _extract_wikilinks(text):
            inbound_count[link] = inbound_count.get(link, 0) + 1

    now = datetime.now()
    for rel, path in notes.items():
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)
        note_name = path.stem

        # Link score: inbound links (0-10 scale)
        links = min(inbound_count.get(note_name, 0), 10)

        # Recency score: days since update (0-10 scale, 10=today, 0=180+ days)
        updated = fm.get("updated", "")
        try:
            updated_date = datetime.strptime(updated, "%Y-%m-%d")
            days_ago = (now - updated_date).days
            recency = max(0, 10 - days_ago // 18)
        except ValueError:
            recency = 0

        # Confidence score
        conf_map = {"high": 10, "medium": 6, "low": 3}
        confidence = conf_map.get(fm.get("confidence", "").strip(), 0)

        # Weighted score
        score = round(links * 0.4 + recency * 0.3 + confidence * 0.3, 1)
        scores[rel] = {"score": score, "links": links, "recency": recency, "confidence": confidence}

    # Write to index file
    RELEVANCE_FILE.write_text(
        json.dumps(scores, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return scores


# ---------------------------------------------------------------------------
# Pending questions
# ---------------------------------------------------------------------------

def pending_count():
    """Count pending vault questions."""
    if not PENDING_FILE.exists():
        return 0
    try:
        lines = PENDING_FILE.read_text(encoding="utf-8").strip().splitlines()
        return len([l for l in lines if l.strip()])
    except Exception:
        return 0


def add_question(agent, note_path, question):
    """Add a pending question to the queue."""
    entry = json.dumps({
        "timestamp": time.time(),
        "agent": agent,
        "note": note_path,
        "question": question,
    })
    try:
        with open(PENDING_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Full optimize pass
# ---------------------------------------------------------------------------

def run_optimize(dry_run=False):
    """Run all optimization steps in order:
    relevance -> prune-scan -> consolidate-scan -> decay-apply -> reindex (last)."""
    if not _is_config_enabled():
        print("Vault optimize disabled in config.md")
        return {"skipped": True, "reason": "disabled"}

    note_count = _count_notes()
    if note_count < MIN_VAULT_SIZE:
        print(f"Vault too small ({note_count} notes, minimum {MIN_VAULT_SIZE}) — skipping")
        return {"skipped": True, "reason": f"vault too small ({note_count} notes)"}

    if not _acquire_lock():
        print("Optimize lock held — skipping")
        return {"skipped": True, "reason": "lock held"}

    try:
        results = {}
        # Execution order: relevance -> prune -> consolidate -> decay -> reindex
        results["relevance"] = len(relevance()) if not dry_run else 0
        results["pruned"] = prune(dry_run=dry_run)
        results["consolidate_candidates"] = consolidate_scan(dry_run=dry_run)
        results["decayed"] = decay(dry_run=dry_run)
        results["reindexed"] = reindex() if not dry_run else []
        results["pending_questions"] = pending_count()
        return results
    finally:
        _release_lock()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    cmd = args[0]
    dry_run = "--dry-run" in args

    if cmd == "full-sweep":
        results = run_optimize(dry_run=dry_run)
        print(json.dumps(results, indent=2, default=str))

    elif cmd == "prune-scan":
        ok, reason = _check_guards()
        if not ok:
            print(reason)
            return 0
        try:
            archived = prune(dry_run=dry_run)
            for a in archived:
                print(a)
            print(f"Pruned: {len(archived)} notes")
        finally:
            _release_lock()

    elif cmd == "consolidate-scan":
        ok, reason = _check_guards()
        if not ok:
            print(reason)
            return 0
        try:
            candidates = consolidate_scan(dry_run=dry_run)
            for c in candidates:
                print(json.dumps(c))
            print(f"Consolidation candidates: {len(candidates)}")
        finally:
            _release_lock()

    elif cmd == "decay-apply":
        ok, reason = _check_guards()
        if not ok:
            print(reason)
            return 0
        try:
            decayed = decay(dry_run=dry_run)
            for d in decayed:
                print(d)
            print(f"Decayed: {len(decayed)} notes")
        finally:
            _release_lock()

    elif cmd == "reindex":
        ok, reason = _check_guards()
        if not ok:
            print(reason)
            return 0
        try:
            updated = reindex()
            for u in updated:
                print(u)
            print(f"Reindexed: {len(updated)} notes")
        finally:
            _release_lock()

    elif cmd == "relevance-report":
        ok, reason = _check_guards()
        if not ok:
            print(reason)
            return 0
        try:
            scores = relevance()
            print(json.dumps(scores, indent=2))
        finally:
            _release_lock()

    elif cmd == "pending-count":
        print(pending_count())

    elif cmd == "add-question":
        opts = {}
        for i, a in enumerate(args):
            if a.startswith("--") and i + 1 < len(args):
                opts[a[2:]] = args[i + 1]
        if not all(k in opts for k in ("agent", "note", "question")):
            print("Usage: vault_optimize.py add-question --agent <r> --note <path> --question <q>",
                  file=sys.stderr)
            return 2
        add_question(opts["agent"], opts["note"], opts["question"])
        print("Question added")

    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
