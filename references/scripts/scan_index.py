#!/usr/bin/env python3
"""SQLite-based improvement scan index for smarter scan targeting.

Replaces heuristic file selection with query-driven targeting based on
coverage gaps, git churn, cross-role findings, and human acceptance rates.

The DB is per-clone and gitignored. scan-history.md remains the source
of truth — the DB is a rebuildable query index.

Usage:
    python scripts/scan_index.py suggest-targets <role> [--count N]
    python scripts/scan_index.py record-scan --role <r> --files <csv> --findings <json>
    python scripts/scan_index.py record-decision --issue <N> --accepted <bool>
    python scripts/scan_index.py refresh-churn
    python scripts/scan_index.py rebuild
    python scripts/scan_index.py --help
"""

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DB_PATH = REPO_ROOT / ".squidsquad" / "scan-index.db"

# Composite scoring weights (locked decision: hardcoded)
WEIGHT_COVERAGE_GAP = 0.3
WEIGHT_CHURN = 0.3
WEIGHT_CROSS_ROLE = 0.2
WEIGHT_ACCEPTANCE = 0.2

# Directories to exclude from source file walks
EXCLUDE_DIRS = {
    ".squidsquad", ".git", "node_modules", "vendor",
    "dist", "build", "out", "__pycache__", ".pytest_cache",
    ".obsidian", ".claude",
}

# File extensions to exclude (binary / generated)
EXCLUDE_EXTS = {
    ".pyc", ".pyo", ".exe", ".dll", ".so", ".dylib",
    ".db", ".sqlite3", ".db-wal", ".db-shm", ".db-journal",
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg",
    ".woff", ".woff2", ".ttf", ".eot",
    ".zip", ".tar", ".gz", ".bz2",
    ".lock", ".pid", ".stackdump",
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    scanned_at TEXT NOT NULL,
    file_path TEXT NOT NULL,
    UNIQUE(role, scanned_at, file_path)
);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER NOT NULL REFERENCES scans(id),
    file_path TEXT NOT NULL,
    finding_type TEXT NOT NULL,
    description TEXT NOT NULL,
    github_issue_number INTEGER,
    human_decision TEXT,
    decided_at TEXT,
    FOREIGN KEY (scan_id) REFERENCES scans(id)
);

CREATE TABLE IF NOT EXISTS file_coverage (
    file_path TEXT PRIMARY KEY,
    last_scanned_at TEXT,
    total_scan_count INTEGER DEFAULT 0,
    finding_count INTEGER DEFAULT 0,
    accepted_finding_count INTEGER DEFAULT 0,
    rejected_finding_count INTEGER DEFAULT 0,
    last_scanned_by TEXT,
    finding_density REAL DEFAULT 0.0
);

CREATE TABLE IF NOT EXISTS git_churn (
    file_path TEXT PRIMARY KEY,
    commit_count_30d INTEGER DEFAULT 0,
    commit_count_90d INTEGER DEFAULT 0,
    last_refreshed TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rejections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role TEXT NOT NULL,
    file_path TEXT NOT NULL,
    finding_description TEXT NOT NULL,
    github_issue_number INTEGER,
    rejected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_scans_role ON scans(role);
CREATE INDEX IF NOT EXISTS idx_scans_file ON scans(file_path);
CREATE INDEX IF NOT EXISTS idx_scans_at ON scans(scanned_at);
CREATE INDEX IF NOT EXISTS idx_findings_issue ON findings(github_issue_number);
CREATE INDEX IF NOT EXISTS idx_findings_decision ON findings(human_decision);
CREATE INDEX IF NOT EXISTS idx_churn_commits ON git_churn(commit_count_30d DESC);
"""


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _get_db(db_path=None):
    """Open or create the SQLite DB with WAL mode and busy timeout."""
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.executescript(SCHEMA_SQL)
    return conn


def _now_iso():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _normalize_path(p):
    """Normalize a file path to forward slashes relative to repo root."""
    return str(Path(p)).replace("\\", "/")


# ---------------------------------------------------------------------------
# Source file discovery
# ---------------------------------------------------------------------------

def _walk_source_files(root=None):
    """Walk the repo for source files, excluding non-source directories/files."""
    root = root or REPO_ROOT
    source_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Filter excluded dirs in-place
        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not d.startswith(".")
        ]
        for f in filenames:
            ext = Path(f).suffix.lower()
            if ext in EXCLUDE_EXTS:
                continue
            full = Path(dirpath) / f
            try:
                rel = full.relative_to(root)
            except ValueError:
                continue
            rel_str = str(rel).replace("\\", "/")
            # Skip hidden files
            if any(part.startswith(".") for part in rel.parts):
                continue
            source_files.append(rel_str)
    return source_files


# ---------------------------------------------------------------------------
# suggest-targets
# ---------------------------------------------------------------------------

def suggest_targets(role, count=5, db_path=None):
    """Return top N files to scan, ranked by composite score."""
    resolved_db_path = db_path or DB_PATH

    # Lazy churn refresh (if stale > 24h) — uses its own connection.
    # Gracefully handle corrupt DB during refresh (#7614).
    try:
        _maybe_refresh_churn(resolved_db_path)
    except (sqlite3.DatabaseError, sqlite3.OperationalError):
        pass  # Churn refresh failed — proceed with stale data

    # Open DB once after churn refresh (#7614)
    try:
        conn = _get_db(resolved_db_path)
    except (sqlite3.DatabaseError, sqlite3.OperationalError) as e:
        print(f"WARNING: DB error ({e}), returning empty list", file=sys.stderr)
        return []

    # Get all source files on disk
    root = REPO_ROOT if db_path is None else db_path.parent.parent
    all_files = _walk_source_files(root)
    if not all_files:
        conn.close()
        return []

    # Load coverage data
    coverage = {}
    for row in conn.execute("SELECT * FROM file_coverage"):
        coverage[row["file_path"]] = dict(row)

    # Load churn data
    churn = {}
    for row in conn.execute("SELECT * FROM git_churn"):
        churn[row["file_path"]] = dict(row)

    # Load cross-role findings (files where OTHER roles found accepted findings)
    cross_role_counts = {}
    rows = conn.execute("""
        SELECT f.file_path, COUNT(*) AS cnt
        FROM findings f
        JOIN scans s ON f.scan_id = s.id
        WHERE s.role != ? AND f.human_decision = 'accepted'
        GROUP BY f.file_path
    """, (role,)).fetchall()
    for row in rows:
        cross_role_counts[row["file_path"]] = row["cnt"]

    conn.close()

    # Compute normalization maximums
    now = datetime.now()
    max_days = 30.0  # cap at 30 days
    max_churn = max((c.get("commit_count_30d", 0) for c in churn.values()), default=1) or 1
    max_cross = max(cross_role_counts.values(), default=1) or 1

    # Score each file
    scored = []
    for f in all_files:
        cov = coverage.get(f, {})
        ch = churn.get(f, {})

        # Coverage gap: days since last scan (higher = more overdue)
        last_scanned = cov.get("last_scanned_at")
        if last_scanned:
            try:
                last_dt = datetime.strptime(last_scanned, "%Y-%m-%d %H:%M:%S")
                days_since = (now - last_dt).total_seconds() / 86400
            except ValueError:
                days_since = max_days
        else:
            days_since = max_days  # never scanned = max gap

        coverage_score = min(days_since / max_days, 1.0)

        # Churn score
        commits_30d = ch.get("commit_count_30d", 0)
        churn_score = min(commits_30d / max_churn, 1.0)

        # Cross-role score
        cross_count = cross_role_counts.get(f, 0)
        cross_score = min(cross_count / max_cross, 1.0)

        # Acceptance rate — only meaningful when decisions exist
        accepted = cov.get("accepted_finding_count", 0)
        rejected = cov.get("rejected_finding_count", 0)
        has_decisions = (accepted + rejected) > 0

        if has_decisions:
            acceptance_rate = accepted / (accepted + rejected)
            score = (
                WEIGHT_COVERAGE_GAP * coverage_score
                + WEIGHT_CHURN * churn_score
                + WEIGHT_CROSS_ROLE * cross_score
                + WEIGHT_ACCEPTANCE * acceptance_rate
            )
        else:
            # No decision history — redistribute acceptance weight
            other = WEIGHT_COVERAGE_GAP + WEIGHT_CHURN + WEIGHT_CROSS_ROLE
            score = (
                (WEIGHT_COVERAGE_GAP / other) * coverage_score
                + (WEIGHT_CHURN / other) * churn_score
                + (WEIGHT_CROSS_ROLE / other) * cross_score
            )

        scored.append((f, score))

    # Sort by score descending, take top N
    scored.sort(key=lambda x: x[1], reverse=True)

    # Filter to files that exist on disk
    results = []
    root_path = REPO_ROOT if db_path is None else db_path.parent.parent
    for f, _score in scored:
        if (root_path / f).exists():
            results.append(f)
            if len(results) >= count:
                break

    return results


# ---------------------------------------------------------------------------
# record-scan
# ---------------------------------------------------------------------------

def record_scan(role, files, findings_json, db_path=None):
    """Record a scan: insert scan rows, findings, and update file_coverage."""
    # Parse findings before opening DB — fail fast on bad input
    findings = json.loads(findings_json) if isinstance(findings_json, str) else findings_json

    conn = _get_db(db_path)
    now = _now_iso()
    try:
        scan_ids = {}
        for f in files:
            f = _normalize_path(f)
            try:
                cur = conn.execute(
                    "INSERT INTO scans (role, scanned_at, file_path) VALUES (?, ?, ?)",
                    (role, now, f),
                )
                scan_ids[f] = cur.lastrowid
            except sqlite3.IntegrityError:
                # Duplicate scan entry — skip
                row = conn.execute(
                    "SELECT id FROM scans WHERE role=? AND scanned_at=? AND file_path=?",
                    (role, now, f),
                ).fetchone()
                if row:
                    scan_ids[f] = row["id"]

        # Insert findings
        for finding in findings:
            fp = _normalize_path(finding.get("file", files[0] if files else "unknown"))
            sid = scan_ids.get(fp)
            if sid is None:
                # Finding for a file not in the scanned list — use first scan id
                sid = next(iter(scan_ids.values()), None)
                if sid is None:
                    continue
            conn.execute(
                """INSERT INTO findings (scan_id, file_path, finding_type, description,
                   github_issue_number) VALUES (?, ?, ?, ?, ?)""",
                (
                    sid,
                    fp,
                    finding.get("type", "issue"),
                    finding.get("description", ""),
                    finding.get("issue_number"),
                ),
            )

        # Update file_coverage
        for f in files:
            f = _normalize_path(f)
            existing = conn.execute(
                "SELECT * FROM file_coverage WHERE file_path=?", (f,)
            ).fetchone()
            finding_count_for_file = sum(
                1 for fi in findings if _normalize_path(fi.get("file", "")) == f
            )
            if existing:
                new_scan_count = existing["total_scan_count"] + 1
                new_finding_count = existing["finding_count"] + finding_count_for_file
                density = new_finding_count / new_scan_count if new_scan_count > 0 else 0.0
                conn.execute(
                    """UPDATE file_coverage SET last_scanned_at=?, total_scan_count=?,
                       finding_count=?, last_scanned_by=?, finding_density=?
                       WHERE file_path=?""",
                    (now, new_scan_count, new_finding_count, role, density, f),
                )
            else:
                density = finding_count_for_file / 1.0
                conn.execute(
                    """INSERT INTO file_coverage (file_path, last_scanned_at,
                       total_scan_count, finding_count, last_scanned_by, finding_density)
                       VALUES (?, ?, 1, ?, ?, ?)""",
                    (f, now, finding_count_for_file, role, density),
                )

        conn.commit()
    finally:
        conn.close()
    print(f"Recorded scan: {len(files)} files, {len(findings)} findings")


# ---------------------------------------------------------------------------
# record-decision
# ---------------------------------------------------------------------------

def record_decision(issue_number, accepted, db_path=None):
    """Record a human decision (accept/reject) for a finding."""
    conn = _get_db(db_path)
    now = _now_iso()
    decision = "accepted" if accepted else "rejected"

    row = conn.execute(
        "SELECT id, file_path FROM findings WHERE github_issue_number=?",
        (issue_number,),
    ).fetchone()

    if not row:
        print(f"WARNING: No finding found for issue #{issue_number}", file=sys.stderr)
        conn.close()
        return False

    conn.execute(
        "UPDATE findings SET human_decision=?, decided_at=? WHERE github_issue_number=?",
        (decision, now, issue_number),
    )

    # Update file_coverage counters
    fp = row["file_path"]
    if accepted:
        cur = conn.execute(
            "UPDATE file_coverage SET accepted_finding_count = accepted_finding_count + 1 WHERE file_path=?",
            (fp,),
        )
        if cur.rowcount == 0:
            conn.execute(
                "INSERT INTO file_coverage (file_path, accepted_finding_count) VALUES (?, 1)",
                (fp,),
            )
    else:
        cur = conn.execute(
            "UPDATE file_coverage SET rejected_finding_count = rejected_finding_count + 1 WHERE file_path=?",
            (fp,),
        )
        if cur.rowcount == 0:
            conn.execute(
                "INSERT INTO file_coverage (file_path, rejected_finding_count) VALUES (?, 1)",
                (fp,),
            )

        # Also record in rejections table
        finding = conn.execute(
            "SELECT description FROM findings WHERE github_issue_number=?",
            (issue_number,),
        ).fetchone()
        scan = conn.execute(
            "SELECT s.role FROM scans s JOIN findings f ON f.scan_id = s.id WHERE f.github_issue_number=?",
            (issue_number,),
        ).fetchone()
        if finding and scan:
            conn.execute(
                "INSERT INTO rejections (role, file_path, finding_description, github_issue_number, rejected_at) VALUES (?, ?, ?, ?, ?)",
                (scan["role"], fp, finding["description"], issue_number, now),
            )

    conn.commit()
    conn.close()
    print(f"Recorded decision: issue #{issue_number} → {decision}")
    return True


# ---------------------------------------------------------------------------
# refresh-churn
# ---------------------------------------------------------------------------

def _git_churn(days, root=None):
    """Get file commit counts from git log for the last N days."""
    cwd = str(root or REPO_ROOT)
    try:
        result = subprocess.run(
            ["git", "log", f"--since={days} days ago", "--numstat", "--format="],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=cwd, check=False,
        )
    except FileNotFoundError:
        return {}

    if result.returncode != 0:
        return {}

    counts = {}
    for line in result.stdout.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[2]:
            fp = parts[2].replace("\\", "/")
            counts[fp] = counts.get(fp, 0) + 1
    return counts


def _detect_renames(root=None):
    """Detect file renames from git history."""
    cwd = str(root or REPO_ROOT)
    try:
        result = subprocess.run(
            ["git", "log", "--diff-filter=R", "--name-status", "--format=",
             "--since=180 days ago"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            cwd=cwd, check=False,
        )
    except FileNotFoundError:
        return {}

    if result.returncode != 0:
        return {}

    renames = {}  # old_path -> new_path
    for line in result.stdout.splitlines():
        # Format: R<NNN>\told_path\tnew_path
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].startswith("R"):
            old_path = parts[1].replace("\\", "/")
            new_path = parts[2].replace("\\", "/")
            renames[old_path] = new_path
    return renames


def refresh_churn(db_path=None):
    """Refresh git churn data in the DB."""
    conn = _get_db(db_path)
    now = _now_iso()
    root = REPO_ROOT if db_path is None else db_path.parent.parent

    churn_30d = _git_churn(30, root)
    churn_90d = _git_churn(90, root)

    # All files mentioned in either period
    all_files = set(churn_30d.keys()) | set(churn_90d.keys())

    for fp in all_files:
        c30 = churn_30d.get(fp, 0)
        c90 = churn_90d.get(fp, 0)
        conn.execute(
            """INSERT INTO git_churn (file_path, commit_count_30d, commit_count_90d, last_refreshed)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(file_path) DO UPDATE SET
               commit_count_30d=?, commit_count_90d=?, last_refreshed=?""",
            (fp, c30, c90, now, c30, c90, now),
        )

    # Detect and apply renames
    renames = _detect_renames(root)
    for old_path, new_path in renames.items():
        # Update file_coverage
        old_row = conn.execute(
            "SELECT * FROM file_coverage WHERE file_path=?", (old_path,)
        ).fetchone()
        if old_row:
            new_row = conn.execute(
                "SELECT * FROM file_coverage WHERE file_path=?", (new_path,)
            ).fetchone()
            if not new_row:
                conn.execute(
                    "UPDATE file_coverage SET file_path=? WHERE file_path=?",
                    (new_path, old_path),
                )
            # If both exist, keep the new_path row (it has more recent data)

        # Update git_churn
        conn.execute(
            "UPDATE OR IGNORE git_churn SET file_path=? WHERE file_path=?",
            (new_path, old_path),
        )

    conn.commit()
    conn.close()
    print(f"Refreshed churn: {len(all_files)} files, {len(renames)} renames detected")


def _maybe_refresh_churn(db_path):
    """Refresh churn if data is stale (>24h old). Takes db_path, opens its own connection."""
    conn = _get_db(db_path)
    row = conn.execute(
        "SELECT MAX(last_refreshed) AS lr FROM git_churn"
    ).fetchone()
    conn.close()
    if row and row["lr"]:
        try:
            last = datetime.strptime(row["lr"], "%Y-%m-%d %H:%M:%S")
            if (datetime.now() - last) < timedelta(hours=24):
                return  # fresh enough
        except ValueError:
            pass
    # Stale or missing — refresh
    refresh_churn(db_path)


# ---------------------------------------------------------------------------
# rebuild
# ---------------------------------------------------------------------------

def _parse_scan_history(md_path):
    """Parse a scan-history.md file into structured scan entries."""
    entries = []
    if not md_path.exists():
        return entries

    text = md_path.read_text(encoding="utf-8", errors="replace")
    # Split by scan headers
    scan_blocks = re.split(r"^## Scan\s*[—–-]+\s*", text, flags=re.MULTILINE)

    for block in scan_blocks[1:]:  # skip header before first scan
        lines = block.strip().splitlines()
        if not lines:
            continue

        # First line is the timestamp
        timestamp_line = lines[0].strip()
        # Parse YYYY-MM-DD HH:MM format
        ts_match = re.match(r"(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})", timestamp_line)
        if not ts_match:
            continue
        timestamp = ts_match.group(1) + ":00"  # add seconds

        files = []
        findings_list = []
        rejections_list = []

        for line in lines[1:]:
            line = line.strip()
            if line.startswith("- **Files scanned**:"):
                files_text = line.split(":", 1)[1].strip()
                # Handle parenthetical notes like "(coverage check — ...)"
                if files_text.startswith("("):
                    continue
                # Split by comma, strip each
                files = [f.strip() for f in files_text.split(",") if f.strip()]
            elif line.startswith("- **Findings**:"):
                findings_text = line.split(":", 1)[1].strip()
                if findings_text.lower() in ("none", "none yet", "(none)", "(none yet)"):
                    continue
                # Extract issue numbers: #NNN
                issue_nums = re.findall(r"#(\d+)", findings_text)
                # Extract description (everything after issue numbers or the whole text)
                desc = re.sub(r"#\d+\s*", "", findings_text).strip("() ,")
                for num in issue_nums:
                    findings_list.append({
                        "issue_number": int(num),
                        "description": desc,
                    })
                if not issue_nums and findings_text:
                    findings_list.append({"description": findings_text})
            elif line.startswith("- **Items rejected"):
                reject_text = line.split(":", 1)[1].strip()
                if reject_text.lower() not in ("none", "none yet", "(none)", "(none yet)"):
                    rejections_list.append(reject_text)

        if files:
            entries.append({
                "timestamp": timestamp,
                "files": files,
                "findings": findings_list,
                "rejections": rejections_list,
            })

    return entries


def rebuild(db_path=None):
    """Rebuild the DB from scan-history.md files."""
    path = db_path or DB_PATH
    # Delete existing DB if present
    if path.exists():
        path.unlink()
    # Also clean WAL/SHM files
    for suffix in ["-wal", "-shm", "-journal"]:
        aux = Path(str(path) + suffix)
        if aux.exists():
            aux.unlink()

    conn = _get_db(path)
    root = REPO_ROOT if db_path is None else path.parent.parent
    now = _now_iso()

    # Find all scan-history.md files — check both main (.squidsquad/) and
    # state worktree (.squidsquad-state/) for scan-history.md (#3664)
    squidsquad_dir = root / ".squidsquad"
    state_dir = root / ".squidsquad-state"
    search_dirs = [squidsquad_dir]
    if state_dir.exists():
        search_dirs.insert(0, state_dir)  # prefer state worktree
    total_scans = 0
    total_findings = 0
    seen_roles = set()

    for base_dir in search_dirs:
        if not base_dir.exists():
            continue
        for role_dir in sorted(base_dir.iterdir()):
            if not role_dir.is_dir():
                continue
            role = role_dir.name
            if role in seen_roles:
                continue  # already found in state worktree
            history_file = role_dir / "scan-history.md"
            if not history_file.exists():
                continue
            seen_roles.add(role)

            entries = _parse_scan_history(history_file)

            for entry in entries:
                for f in entry["files"]:
                    f = _normalize_path(f)
                    try:
                        cur = conn.execute(
                            "INSERT INTO scans (role, scanned_at, file_path) VALUES (?, ?, ?)",
                            (role, entry["timestamp"], f),
                        )
                        scan_id = cur.lastrowid
                        total_scans += 1
                    except sqlite3.IntegrityError:
                        row = conn.execute(
                            "SELECT id FROM scans WHERE role=? AND scanned_at=? AND file_path=?",
                            (role, entry["timestamp"], f),
                        ).fetchone()
                        scan_id = row["id"] if row else None

                    if scan_id is None:
                        continue

                    # Insert findings for this file
                    for finding in entry["findings"]:
                        conn.execute(
                            """INSERT INTO findings (scan_id, file_path, finding_type,
                               description, github_issue_number) VALUES (?, ?, ?, ?, ?)""",
                            (
                                scan_id,
                                f,
                                "issue",  # default from scan-history format
                                finding.get("description", ""),
                                finding.get("issue_number"),
                            ),
                        )
                        total_findings += 1

    # Rebuild file_coverage from scans and findings
    conn.execute("DELETE FROM file_coverage")
    conn.execute("""
        INSERT INTO file_coverage (file_path, last_scanned_at, total_scan_count,
            finding_count, accepted_finding_count, rejected_finding_count,
            last_scanned_by, finding_density)
        SELECT
            s.file_path,
            MAX(s.scanned_at) AS last_scanned_at,
            COUNT(DISTINCT s.id) AS total_scan_count,
            COUNT(DISTINCT f.id) AS finding_count,
            COUNT(DISTINCT CASE WHEN f.human_decision='accepted' THEN f.id END) AS accepted,
            COUNT(DISTINCT CASE WHEN f.human_decision='rejected' THEN f.id END) AS rejected,
            (SELECT s2.role FROM scans s2 WHERE s2.file_path = s.file_path
             ORDER BY s2.scanned_at DESC LIMIT 1) AS last_scanned_by,
            CASE WHEN COUNT(DISTINCT s.id) > 0
                 THEN CAST(COUNT(DISTINCT f.id) AS REAL) / COUNT(DISTINCT s.id)
                 ELSE 0.0 END AS finding_density
        FROM scans s
        LEFT JOIN findings f ON f.scan_id = s.id
        GROUP BY s.file_path
    """)

    conn.commit()
    conn.close()
    print(f"Rebuilt DB: {total_scans} scan records, {total_findings} findings")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args():
    parser = argparse.ArgumentParser(
        description="SQLite-based improvement scan index",
    )
    sub = parser.add_subparsers(dest="command")

    # suggest-targets
    st = sub.add_parser("suggest-targets", help="Suggest files to scan")
    st.add_argument("role", help="Agent role (e.g. skill, pm, qa)")
    st.add_argument("--count", type=int, default=5, help="Number of targets")

    # record-scan
    rs = sub.add_parser("record-scan", help="Record a completed scan")
    rs.add_argument("--role", required=True, help="Agent role")
    rs.add_argument("--files", required=True, help="Comma-separated file list")
    rs.add_argument("--findings", default="[]", help="JSON array of findings")

    # record-decision
    rd = sub.add_parser("record-decision", help="Record human decision on a finding")
    rd.add_argument("--issue", type=int, required=True, help="GitHub issue number")
    rd.add_argument("--accepted", required=True, help="true or false")

    # refresh-churn
    sub.add_parser("refresh-churn", help="Refresh git churn data")

    # rebuild
    sub.add_parser("rebuild", help="Rebuild DB from scan-history.md files")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    return args


def main():
    args = _parse_args()

    if args.command == "suggest-targets":
        targets = suggest_targets(args.role, args.count)
        for t in targets:
            print(t)

    elif args.command == "record-scan":
        files = [f.strip() for f in args.files.split(",") if f.strip()]
        record_scan(args.role, files, args.findings)

    elif args.command == "record-decision":
        accepted = args.accepted.lower() in ("true", "yes", "1")
        record_decision(args.issue, accepted)

    elif args.command == "refresh-churn":
        refresh_churn()

    elif args.command == "rebuild":
        rebuild()


if __name__ == "__main__":
    main()
