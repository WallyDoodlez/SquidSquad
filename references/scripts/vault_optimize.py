#!/usr/bin/env python3
"""SquidSquad vault optimizer — on-demand vault maintenance.

Covers 5 areas: prune (auto-archive stale+orphan), consolidate candidates,
reindex (links), confidence decay, relevance scoring.

Usage:
    python scripts/vault_optimize.py run [--dry-run]     # Full optimize pass
    python scripts/vault_optimize.py prune [--dry-run]   # Archive stale+orphan notes
    python scripts/vault_optimize.py decay [--dry-run]    # Confidence decay
    python scripts/vault_optimize.py reindex              # Rebuild links index
    python scripts/vault_optimize.py relevance            # Update relevance scores
    python scripts/vault_optimize.py pending-count        # Count pending questions
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
import shutil
import sys
import time
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


# ---------------------------------------------------------------------------
# Prune — auto-archive stale+orphan galaxy notes
# ---------------------------------------------------------------------------

def prune(dry_run=False):
    """Archive galaxy notes that are both stale (>60 days) and orphaned (no inbound links)."""
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

        # Grace period: never prune notes created today
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if mtime.date() == datetime.now().date():
                continue
        except Exception:
            continue

        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)

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
        note_name = path.stem
        if note_name in inbound:
            continue  # Has inbound links — not orphan

        # Check status — only archive active notes
        if fm.get("status", "").strip() != "active":
            continue

        # This note is stale + orphan + active → archive
        if dry_run:
            archived.append(f"[dry-run] would archive: {rel}")
        else:
            dest = VAULT_DIR / "archives" / path.name
            if dest.exists():
                dest = VAULT_DIR / "archives" / f"{path.stem}-{int(time.time())}{path.suffix}"
            shutil.move(str(path), str(dest))
            archived.append(f"archived: {rel} -> archives/{dest.name}")

    return archived


# ---------------------------------------------------------------------------
# Confidence decay
# ---------------------------------------------------------------------------

def decay(dry_run=False):
    """Decay confidence from high→medium→low based on staleness."""
    notes = _get_all_notes()
    cutoff_medium = datetime.now() - timedelta(days=STALE_DAYS)
    cutoff_low = datetime.now() - timedelta(days=STALE_DAYS * 2)
    decayed = []

    for rel, path in notes.items():
        text = path.read_text(encoding="utf-8")
        fm = _parse_frontmatter(text)

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
                new_text = text.replace(f"confidence: {confidence}", f"confidence: {new_confidence}", 1)
                today = datetime.now().strftime("%Y-%m-%d")
                new_text = re.sub(r"updated: \S+", f"updated: {today}", new_text, count=1)
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
    """Run all optimization steps in order."""
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
        results["pruned"] = prune(dry_run=dry_run)
        results["decayed"] = decay(dry_run=dry_run)
        results["reindexed"] = reindex() if not dry_run else []
        results["relevance"] = len(relevance()) if not dry_run else 0
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

    if cmd == "run":
        results = run_optimize(dry_run=dry_run)
        print(json.dumps(results, indent=2, default=str))

    elif cmd == "prune":
        archived = prune(dry_run=dry_run)
        for a in archived:
            print(a)
        print(f"Pruned: {len(archived)} notes")

    elif cmd == "decay":
        decayed = decay(dry_run=dry_run)
        for d in decayed:
            print(d)
        print(f"Decayed: {len(decayed)} notes")

    elif cmd == "reindex":
        updated = reindex()
        for u in updated:
            print(u)
        print(f"Reindexed: {len(updated)} notes")

    elif cmd == "relevance":
        scores = relevance()
        print(json.dumps(scores, indent=2))

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
