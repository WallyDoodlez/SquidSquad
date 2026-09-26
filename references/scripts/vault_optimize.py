#!/usr/bin/env python3
"""SquidSquad vault optimizer — on-demand vault maintenance.

Covers 5 areas: prune (auto-archive stale+orphan), consolidate candidates,
reindex (links), confidence decay, relevance scoring.

Usage:
    python scripts/vault_optimize.py run [--dry-run]              # Full optimize pass (alias: full-sweep)
    python scripts/vault_optimize.py prune-scan [--dry-run]       # Archive stale+orphan notes
    python scripts/vault_optimize.py consolidate-scan [--dry-run]  # Detect merge candidates
    python scripts/vault_optimize.py decay-apply [--dry-run]       # Confidence decay
    python scripts/vault_optimize.py reindex                       # Rebuild links index
    python scripts/vault_optimize.py propose-prunes [--stale-days N]  # #13859: engine-report-driven prune PROPOSALS (never auto-applied)
    python scripts/vault_optimize.py compact-telemetry --alias <alias> [--horizon-days N]  # #13859 S3.4: compact own shard via the engine (owner-only)
    python scripts/vault_optimize.py analyze-queue [--cutoff-days 14] [--limit 20]  # #13861: notes due for analyze (last_optimized)
    python scripts/vault_optimize.py mark-optimized --slugs a,b [--date YYYY-MM-DD]  # #13861: stamp last_optimized after analyze
    python scripts/vault_optimize.py file-contradiction --slug-a <s> --slug-b <s> --topic <t> --statement-a <x> --statement-b <y> --reporter <alias>  # #13861: HITL task (pending), deduped
    python scripts/vault_optimize.py file-prune-review --reporter <alias> [--stale-days N]  # #13861: impressions-report proposals -> one HITL task
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
    """Vault optimize is always-on — there is no enable/disable toggle (#13043).

    Activation is controlled by the quiet-cycle gate + the 20-note threshold
    + the cooldown, not by config. Retained as a function (rather than deleting
    the call sites) so the activation contract stays in one named place; it now
    unconditionally returns True.
    """
    return True


def _acquire_lock():
    """Acquire optimize lock atomically. Returns True if acquired."""
    try:
        # Check for stale lock first — single stat() avoids TOCTOU (#7618)
        try:
            mtime = LOCK_FILE.stat().st_mtime
            if time.time() - mtime < LOCK_TTL:
                return False
            LOCK_FILE.unlink(missing_ok=True)
        except FileNotFoundError:
            pass  # No lock file — proceed to create
        # Atomic create — O_CREAT | O_EXCL fails if file already exists
        fd = os.open(str(LOCK_FILE), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        return True
    except FileExistsError:
        return False  # Another process claimed the lock between check and create
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

ENGINE_REPORT = (Path(__file__).resolve().parent.parent
                 / "skills" / "vault-search" / "scripts"
                 / "vault-impressions-report.mjs")


def propose_prunes(stale_days=90):
    """#13859 (S3.3 consumption AC, VAULT-ARCH 7.3/6.4): run the ENGINE's
    impressions report and turn its buckets into prune/archival PROPOSALS.

    The report is the purge signal -- usage-based staleness (4.4), never time
    decay. This function proposes only: output is a JSON proposal list for
    PM's improvement scan / human triage; nothing is archived or deleted here
    (contradiction-class actions stay human-gated, 7.3). The shard read lives
    entirely behind the engine boundary (8.5) -- this script invokes the
    packaged reporter; the shard store is never opened from Python. Engine unavailable
    (node missing, script error) degrades to an honest empty proposal set
    with a reason (9.9), never an exception.

    Returns the proposal dict (also printed as JSON by the CLI wrapper).
    """
    import shutil as _shutil
    node = _shutil.which("node")
    if node is None or not ENGINE_REPORT.is_file():
        reason = "node unavailable" if node is None else "engine report script missing"
        return {"proposals": [], "engineUnavailable": True, "reason": reason}
    proc = subprocess.run(
        [node, str(ENGINE_REPORT), "--vault", str(VAULT_DIR),
         "--stale-days", str(stale_days)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120,
    )
    if proc.returncode != 0:
        return {"proposals": [], "engineUnavailable": True,
                "reason": f"report exited {proc.returncode}: {(proc.stderr or '').strip()[:200]}"}
    try:
        report = json.loads(proc.stdout)
    except ValueError as e:
        return {"proposals": [], "engineUnavailable": True,
                "reason": f"report output unparseable: {e}"}

    proposals = []
    for row in report.get("rows", []):
        if row.get("status") in ("archived", "superseded"):
            continue  # already retired -- nothing to propose
        if row.get("stale"):
            proposals.append({"slug": row["slug"], "path": row["path"],
                              "action": "archive", "bucket": "stale",
                              "evidence": f"used {row['used']}x, last {row['lastUsed']}"})
        elif row.get("surfacedNeverUsed"):
            proposals.append({"slug": row["slug"], "path": row["path"],
                              "action": "review", "bucket": "surfaced-never-used",
                              "evidence": f"offered {row['impression']}+{row['walked']}x, never cited"})
        elif row.get("cold"):
            proposals.append({"slug": row["slug"], "path": row["path"],
                              "action": "review", "bucket": "cold",
                              "evidence": "never surfaced by any search"})
    return {"proposals": proposals, "engineUnavailable": False,
            "counts": report.get("counts", {}), "staleDays": stale_days}


ENGINE_COMPACT = (Path(__file__).resolve().parent.parent
                  / "skills" / "vault-search" / "scripts"
                  / "compact-telemetry.mjs")
INSTANCE_ID_FILE = REPO_ROOT / ".squidsquad" / ".instance-id"


def _read_instance_id():
    """The engine identity contract (vault-search SKILL.md): the harness
    instance UUID lives in the gitignored .squidsquad/.instance-id; absent
    means the install predates the mint -- callers pass 'unprovisioned'."""
    try:
        val = INSTANCE_ID_FILE.read_text(encoding="utf-8").strip()
        return val or "unprovisioned"
    except OSError:
        return "unprovisioned"


def compact_telemetry(alias, horizon_days=30):
    """#13859 (S3.4, VAULT-ARCH 6.5): quiet-cycle compaction of THIS writer's
    own telemetry shard, via the engine's compaction tool.

    Owner-only is structural on both sides: the alias is an explicit caller
    argument (never guessed from the environment -- a wrong identity would
    compact another writer's shard), and the engine tool itself refuses to run
    without one. The shard store stays behind the engine boundary (8.5) --
    Python invokes the packaged tool and relays its JSON; the aggregate and
    shard writes (invariant 2 ordering) happen engine-side, and the caller's
    normal cycle commit picks BOTH files up as one commit. Engine unavailable
    degrades to an honest skip with a reason (9.9), never an exception.
    """
    import shutil as _shutil
    node = _shutil.which("node")
    if node is None or not ENGINE_COMPACT.is_file():
        reason = "node unavailable" if node is None else "engine compact script missing"
        return {"skipped": True, "engineUnavailable": True, "reason": reason}
    instance_id = _read_instance_id()
    if instance_id == "unprovisioned":
        # Truncation is the one destructive telemetry op: under the shared
        # 'unprovisioned' sentinel, distinct un-minted clones with the same
        # alias collapse onto ONE shard, so "owner-only" is not actually
        # satisfied -- this pass could absorb another machine's appends.
        # Reads/writes tolerate the sentinel; compaction requires a real
        # minted identity.
        return {"skipped": True, "engineUnavailable": False,
                "reason": "instance-id unprovisioned -- owner-only compaction "
                          "requires a minted identity (wizard mint step)"}
    proc = subprocess.run(
        [node, str(ENGINE_COMPACT), "--vault", str(VAULT_DIR),
         "--instance-id", instance_id, "--alias", alias,
         "--horizon-days", str(horizon_days)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120,
    )
    if proc.returncode != 0:
        return {"skipped": True, "engineUnavailable": True,
                "reason": f"compact exited {proc.returncode}: {(proc.stderr or '').strip()[:200]}"}
    try:
        result = json.loads(proc.stdout)
    except ValueError as e:
        return {"skipped": True, "engineUnavailable": True,
                "reason": f"compact output unparseable: {e}"}
    result["skipped"] = False
    return result


# ---------------------------------------------------------------------------
# Harness-scheduled analyze (#13861, PRD-VAULT-V2 S5.1, VAULT-ARCH 7.3/9.6)
# ---------------------------------------------------------------------------
#
# The harness maintenance window runs analyze_queue(); a non-empty queue wakes
# pm, whose vault-optimize sub-skill judges contradictions over the queued
# notes. Judgment is agent-side; everything around it -- queue selection,
# HITL filing with dedup, the last_optimized stamp -- is deterministic here.

OPTIMIZE_CUTOFF_DAYS = 14
ANALYZE_QUEUE_LIMIT = 20
_RETIRED_STATUSES = ("archived", "superseded")
CONTRADICTION_TITLE_PREFIX = "Vault contradiction:"
PRUNE_REVIEW_TITLE_PREFIX = "Vault pruning review:"


def analyze_queue(cutoff_days=OPTIMIZE_CUTOFF_DAYS, limit=ANALYZE_QUEUE_LIMIT, today=None):
    """Notes due for an optimize analyze pass, oldest ``last_optimized`` first.

    Due = active note whose ``last_optimized`` is absent/unparseable or at least
    ``cutoff_days`` old. Never-optimized notes sort first (then by path, so the
    order is stable). BRIEFING.md (excluded from the engine, VAULT-ARCH 5), the
    legacy ``archives/`` folder, and retired statuses are skipped.
    """
    today = today or datetime.now().date()
    due = []
    for rel, path in sorted(_get_all_notes().items()):
        if rel == "BRIEFING.md" or rel.startswith("archives/"):
            continue
        try:
            fm = _parse_frontmatter(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        if fm.get("status", "").strip().lower() in _RETIRED_STATUSES:
            continue
        raw = fm.get("last_optimized", "").strip().strip("'\"")
        try:
            last = datetime.strptime(raw, "%Y-%m-%d").date() if raw else None
        except ValueError:
            last = None
        if last is not None and (today - last).days < cutoff_days:
            continue
        due.append({"slug": Path(rel).stem, "path": rel,
                    "last_optimized": last.isoformat() if last else None})
    due.sort(key=lambda n: (n["last_optimized"] is not None,
                            n["last_optimized"] or "", n["path"]))
    return {"queue": due[:limit], "total_due": len(due),
            "cutoff_days": cutoff_days, "limit": limit}


def _set_frontmatter_field(text, key, value):
    """Set ``key: value`` in the note's frontmatter (replace or append).
    Returns None when the note has no frontmatter block."""
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    head, rest = text[:end], text[end:]
    # Preserve the note's own line endings (CRLF notes stay CRLF): the
    # closing "\n---" leaves a trailing "\r" on head for CRLF files.
    cr = "\r" if head.endswith("\r") else ""
    pattern = re.compile(rf"^{re.escape(key)}:[^\r\n]*", re.MULTILINE)
    if pattern.search(head):
        head = pattern.sub(f"{key}: {value}", head, count=1)
    else:
        head = f"{head.rstrip()}{cr}\n{key}: {value}{cr}"
    return head + rest


def mark_optimized(slugs, date=None):
    """Stamp ``last_optimized`` on each slug's note (TRD 4.3). The ``updated``
    field is deliberately untouched -- it drives the recency rank (6.2) and an
    analyze pass is not a content change. Atomic per-note write."""
    date = date or datetime.now().strftime("%Y-%m-%d")
    by_slug = {Path(rel).stem: path for rel, path in _get_all_notes().items()}
    marked, missing = [], []
    for slug in slugs:
        path = by_slug.get(slug)
        new = None
        if path is not None:
            with open(path, encoding="utf-8", newline="") as f:  # raw line endings
                new = _set_frontmatter_field(f.read(), "last_optimized", date)
        if new is None:
            missing.append(slug)
            continue
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(new, encoding="utf-8", newline="")
        tmp.replace(path)
        marked.append(slug)
    return {"marked": marked, "missing": missing, "date": date}


def _tracker(*args):
    """Run tracker.py; returns (returncode, stdout). The single forge egress
    for this module, so tests stub exactly one seam."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPT_DIR / "tracker.py"), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO_ROOT), timeout=120,
    )
    return proc.returncode, proc.stdout


def _open_pm_task_titles():
    """Titles of open pm tasks, or None when the forge read failed (callers
    then refuse to file -- a duplicate HITL task is worse than a late one)."""
    rc, out = _tracker("list-by-labels", "type:task,role:pm")
    if rc != 0:
        return None
    try:
        return [i.get("title", "") for i in json.loads(out or "[]")]
    except ValueError:
        return None


# The forge's issue listing lags creation by seconds (verifier TC6 on #13861:
# back-to-back files of one pair both landed at +3s/+6s). Every successful
# filing is recorded here first-hand and consulted before the forge list, so
# a re-file inside the lag window is caught; the TTL comfortably outlasts the
# lag while still letting a contradiction re-file after its task is closed.
HITL_LEDGER_FILE = REPO_ROOT / ".squidsquad" / ".vault-hitl-ledger.json"
HITL_LEDGER_TTL = 3600  # seconds


def _read_ledger(now):
    try:
        data = json.loads(HITL_LEDGER_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {t: e for t, e in data.items()
            if isinstance(e, dict) and now - e.get("at", 0) < HITL_LEDGER_TTL}


def _record_filed(title, number, now):
    ledger = _read_ledger(now)
    ledger[title] = {"number": number, "at": now}
    try:
        HITL_LEDGER_FILE.parent.mkdir(parents=True, exist_ok=True)
        tmp = HITL_LEDGER_FILE.with_name(HITL_LEDGER_FILE.name + ".tmp")
        tmp.write_text(json.dumps(ledger, indent=2), encoding="utf-8")
        tmp.replace(HITL_LEDGER_FILE)
    except OSError:
        pass  # the forge list still dedupes once it catches up


def _already_filed(match, titles, now):
    """(True, reason) when a recent ledger entry or an open forge task
    matches. ``match`` is applied to the ASCII-transliterated title form
    tracker.create_task stores (#13517)."""
    for t, e in _read_ledger(now).items():
        if match(t):
            return True, f"filed moments ago as #{e.get('number')} (ledger)"
    if any(match(t.removeprefix("TASK:").strip()) for t in titles):
        return True, "open task already exists"
    return False, ""


def _file_pm_task(title, body, reporter, titles=None, match=None):
    """File a ``pending`` pm task -- the human approval gate IS the HITL gate
    (never auto-applied). Dedup: recent-filing ledger, then open pm tasks
    (exact title unless ``match`` is given)."""
    from tracker import _asciiize_title
    now = time.time()
    stored = _asciiize_title(title)
    match = match or (lambda t: t == stored)
    if titles is None:
        titles = _open_pm_task_titles()
    if titles is None:
        return {"filed": False, "reason": "forge read failed -- not filing blind"}
    dup, reason = _already_filed(match, titles, now)
    if dup:
        return {"filed": False, "duplicate": True, "reason": reason, "title": title}
    rc, out = _tracker("create-task", "--title", title, "--body", body,
                       "--role", "pm", "--priority", "low", "--reporter", reporter)
    if rc != 0:
        return {"filed": False, "reason": f"create-task exited {rc}", "title": title}
    number = None
    for line in reversed((out or "").strip().splitlines()):
        try:
            number = json.loads(line).get("number")
            break
        except (ValueError, AttributeError):
            continue
    _record_filed(stored, number, now)
    return {"filed": True, "number": number, "title": title}


def file_contradiction(slug_a, slug_b, topic, statement_a, statement_b, reporter):
    """File one contradiction as a HITL task. Title carries the sorted slug
    pair so the same contradiction found by two windows files once."""
    a, b = sorted((slug_a, slug_b))
    if a == b:
        return {"filed": False, "reason": "a contradiction needs two distinct notes"}
    stmt = {slug_a: statement_a, slug_b: statement_b}
    body = (
        f"Vault optimize analyze (VAULT-ARCH 9.6) found two active notes that "
        f"contradict each other on: **{topic}**\n\n"
        f"- [[{a}]]: {stmt[a]}\n- [[{b}]]: {stmt[b]}\n\n"
        f"Human decision needed -- nothing has been changed. On approval, resolve "
        f"by updating one note or retiring it (`status: superseded`/`archived`, "
        f"flipped in place per vault-protocol)."
    )
    return _file_pm_task(f"{CONTRADICTION_TITLE_PREFIX} {a} vs {b}", body, reporter)


def file_prune_review(reporter, stale_days=90):
    """File the impressions-report pruning proposals (6.4) as ONE HITL review
    task. Engine unavailable or zero proposals files nothing."""
    result = propose_prunes(stale_days=stale_days)
    if result.get("engineUnavailable"):
        return {"filed": False, "reason": f"engine unavailable: {result.get('reason')}"}
    proposals = result.get("proposals", [])
    if not proposals:
        return {"filed": False, "reason": "no proposals"}
    rows ="\n".join(f"- [[{p['slug']}]] -- {p['bucket']} -> {p['action']} ({p['evidence']})"
                     for p in proposals)
    body = (
        f"Usage-based pruning proposals from the impressions report "
        f"(VAULT-ARCH 6.4, stale = {stale_days}d). Proposals only -- nothing "
        f"was archived. On approval, retire by setting `status: archived` in "
        f"place; never move or delete the file.\n\n{rows}"
    )
    # One open review at a time, whatever its count: match on the prefix.
    return _file_pm_task(f"{PRUNE_REVIEW_TITLE_PREFIX} {len(proposals)} notes", body,
                         reporter, match=lambda t: t.startswith(PRUNE_REVIEW_TITLE_PREFIX))


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

    for rel, path in list(notes.items()):
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
            # Remove archived note from dict before rewriting links (#2677)
            notes.pop(rel, None)
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
                # Scope rewrites to frontmatter only (#6514) — avoid corrupting body.
                # Decay rewrites ONLY `confidence:`, never `updated:` (#13042):
                # VAULT-ARCH §4.4 — "Decay steps do NOT modify `updated:`"; the
                # decay clock keys off the last human/agent semantic edit, not the
                # decay event. Bumping `updated:` here restarts the medium→low clock
                # from the decay (so a note never reaches `low` on the 120-day-from-
                # edit schedule) and hides just-decayed notes from the next
                # decay-scan for ~60 days. The decay event is recorded by the
                # changelog entry below, which is the correct audit trail.
                fm_end = text.find("---", 3)
                if fm_end != -1:
                    header = text[:fm_end + 3]
                    body = text[fm_end + 3:]
                    header = header.replace(f"confidence: {confidence}", f"confidence: {new_confidence}", 1)
                    new_text = header + body
                else:
                    # No frontmatter boundary — fall back to full-text (shouldn't happen)
                    new_text = text.replace(f"confidence: {confidence}", f"confidence: {new_confidence}", 1)

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
    except OSError as e:
        print(f"WARNING: Failed to write pending question: {e}", file=sys.stderr)


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

def _str_opt(args, flag):
    """Value after ``flag``, or "" when absent / followed by another flag."""
    if flag in args:
        i = args.index(flag) + 1
        if i < len(args) and not args[i].startswith("--"):
            return args[i]
    return ""


def _int_opt(args, flag, default):
    try:
        return int(_str_opt(args, flag))
    except ValueError:
        return default


def main():
    args = sys.argv[1:]
    if not args or "--help" in args or "-h" in args:
        print(__doc__)
        return 0

    cmd = args[0]
    dry_run = "--dry-run" in args

    if cmd in ("full-sweep", "run"):
        # `run` is the canonical name in VAULT-ARCH §7.3/§8.3 and the
        # vault-optimize sub-skill (~7 references); `full-sweep` is kept as
        # the historical alias (#13043).
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

    elif cmd == "propose-prunes":
        sd = 90
        if "--stale-days" in args:
            try:
                sd = int(args[args.index("--stale-days") + 1])
            except (ValueError, IndexError):
                pass
        result = propose_prunes(stale_days=sd)
        print(json.dumps(result, indent=2))
        sys.exit(0)
    elif cmd == "compact-telemetry":
        alias = None
        if "--alias" in args:
            try:
                alias = args[args.index("--alias") + 1]
            except IndexError:
                pass
        if not alias or alias.startswith("--"):
            print("Usage: vault_optimize.py compact-telemetry --alias <alias> [--horizon-days N]",
                  file=sys.stderr)
            return 2
        hd = 30
        if "--horizon-days" in args:
            try:
                hd = int(args[args.index("--horizon-days") + 1])
            except (ValueError, IndexError):
                pass
        result = compact_telemetry(alias, horizon_days=hd)
        print(json.dumps(result, indent=2))
        sys.exit(0)
    elif cmd == "analyze-queue":
        cd, lim = _int_opt(args, "--cutoff-days", OPTIMIZE_CUTOFF_DAYS), \
            _int_opt(args, "--limit", ANALYZE_QUEUE_LIMIT)
        print(json.dumps(analyze_queue(cutoff_days=cd, limit=lim), indent=2))
    elif cmd == "mark-optimized":
        slugs = [s for s in _str_opt(args, "--slugs").split(",") if s.strip()]
        if not slugs:
            print("Usage: vault_optimize.py mark-optimized --slugs a,b [--date YYYY-MM-DD]",
                  file=sys.stderr)
            return 2
        print(json.dumps(mark_optimized([s.strip() for s in slugs],
                                        date=_str_opt(args, "--date") or None), indent=2))
    elif cmd == "file-contradiction":
        opts = {k: _str_opt(args, f"--{k}") for k in
                ("slug-a", "slug-b", "topic", "statement-a", "statement-b", "reporter")}
        if not all(opts.values()):
            print("Usage: vault_optimize.py file-contradiction --slug-a <s> --slug-b <s> "
                  "--topic <t> --statement-a <text> --statement-b <text> --reporter <alias>",
                  file=sys.stderr)
            return 2
        result = file_contradiction(opts["slug-a"], opts["slug-b"], opts["topic"],
                                    opts["statement-a"], opts["statement-b"], opts["reporter"])
        print(json.dumps(result, indent=2))
        return 0 if result["filed"] or result.get("duplicate") else 1
    elif cmd == "file-prune-review":
        reporter = _str_opt(args, "--reporter")
        if not reporter:
            print("Usage: vault_optimize.py file-prune-review --reporter <alias> [--stale-days N]",
                  file=sys.stderr)
            return 2
        print(json.dumps(file_prune_review(reporter, _int_opt(args, "--stale-days", 90)),
                         indent=2))
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
