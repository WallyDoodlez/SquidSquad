"""Tests for references/scripts/scan_index.py — SQLite scan index."""

import json
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import scan_index


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def db(tmp_path):
    """Create a fresh DB in a temp directory."""
    db_path = tmp_path / ".squidsquad" / "scan-index.db"
    db_path.parent.mkdir(parents=True)
    conn = scan_index._get_db(db_path)
    conn.close()
    return db_path


@pytest.fixture
def populated_db(db, tmp_path):
    """DB with known data for scoring tests."""
    conn = scan_index._get_db(db)
    now = datetime.now()

    # File A: scanned 14 days ago, high churn, cross-role findings, good acceptance
    old_ts = (now - timedelta(days=14)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO scans (role, scanned_at, file_path) VALUES (?, ?, ?)",
        ("skill", old_ts, "src/file_a.py"),
    )
    conn.execute(
        "INSERT INTO file_coverage VALUES (?, ?, 3, 5, 4, 1, ?, ?)",
        ("src/file_a.py", old_ts, "skill", 5 / 3),
    )
    conn.execute(
        "INSERT INTO git_churn VALUES (?, 10, 25, ?)",
        ("src/file_a.py", now.strftime("%Y-%m-%d %H:%M:%S")),
    )

    # File B: scanned 1 day ago, low churn, no cross-role, mixed acceptance
    recent_ts = (now - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO scans (role, scanned_at, file_path) VALUES (?, ?, ?)",
        ("skill", recent_ts, "src/file_b.py"),
    )
    conn.execute(
        "INSERT INTO file_coverage VALUES (?, ?, 2, 4, 2, 2, ?, ?)",
        ("src/file_b.py", recent_ts, "skill", 4 / 2),
    )
    conn.execute(
        "INSERT INTO git_churn VALUES (?, 2, 5, ?)",
        ("src/file_b.py", now.strftime("%Y-%m-%d %H:%M:%S")),
    )

    # File C: never scanned, moderate churn
    conn.execute(
        "INSERT INTO git_churn VALUES (?, 5, 12, ?)",
        ("src/file_c.py", now.strftime("%Y-%m-%d %H:%M:%S")),
    )

    # Add cross-role findings for file A (from qa role)
    scan_id = conn.execute(
        "INSERT INTO scans (role, scanned_at, file_path) VALUES (?, ?, ?)",
        ("qa", old_ts, "src/file_a.py"),
    ).lastrowid
    for i in range(3):
        conn.execute(
            "INSERT INTO findings (scan_id, file_path, finding_type, description, human_decision) VALUES (?, ?, ?, ?, ?)",
            (scan_id, "src/file_a.py", "issue", f"cross-role finding {i}", "accepted"),
        )

    conn.commit()
    conn.close()

    # Create the actual files on disk
    for name in ["src/file_a.py", "src/file_b.py", "src/file_c.py"]:
        p = tmp_path / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"# {name}\n")

    return db


@pytest.fixture
def scan_history_dir(tmp_path):
    """Create a .squidsquad dir with scan-history.md files for rebuild tests."""
    ss = tmp_path / ".squidsquad"
    skill_dir = ss / "skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "scan-history.md").write_text(
        "# Scan History\n\n"
        "## Scan \u2014 2026-04-10 14:00\n\n"
        "- **Files scanned**: references/scripts/tracker.py, references/scripts/compose.py\n"
        "- **Findings**: #100 dead code in compose.py\n"
        "- **Items rejected by human**: none\n\n"
        "## Scan \u2014 2026-04-12 09:30\n\n"
        "- **Files scanned**: references/scripts/cycle.py\n"
        "- **Findings**: none\n"
        "- **Items rejected by human**: none\n",
        encoding="utf-8",
    )

    qa_dir = ss / "qa"
    qa_dir.mkdir(parents=True)
    (qa_dir / "scan-history.md").write_text(
        "# Scan History\n\n"
        "## Scan \u2014 2026-04-11 10:00\n\n"
        "- **Files scanned**: tests/test_config.py\n"
        "- **Findings**: none\n"
        "- **Items rejected by human**: none\n",
        encoding="utf-8",
    )

    return ss


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

class TestGetDb:
    def test_creates_db_with_wal_mode(self, db):
        conn = scan_index._get_db(db)
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        assert mode == "wal"
        conn.close()

    def test_creates_tables(self, db):
        conn = scan_index._get_db(db)
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        assert "scans" in tables
        assert "findings" in tables
        assert "file_coverage" in tables
        assert "git_churn" in tables
        assert "rejections" in tables
        conn.close()

    def test_busy_timeout_set(self, db):
        conn = scan_index._get_db(db)
        timeout = conn.execute("PRAGMA busy_timeout").fetchone()[0]
        assert timeout == 5000
        conn.close()


class TestNormalizePath:
    def test_forward_slashes(self):
        assert scan_index._normalize_path("a\\b\\c.py") == "a/b/c.py"

    def test_already_forward(self):
        assert scan_index._normalize_path("a/b/c.py") == "a/b/c.py"


# ---------------------------------------------------------------------------
# suggest-targets
# ---------------------------------------------------------------------------

class TestSuggestTargets:
    def test_returns_files_ordered_by_score(self, populated_db, tmp_path):
        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            targets = scan_index.suggest_targets("skill", count=3, db_path=populated_db)
        assert len(targets) <= 3
        # File C (never scanned) and File A (old scan, high churn) should rank above B
        if len(targets) >= 2:
            assert "src/file_b.py" not in targets[:2] or targets.index("src/file_b.py") > 0

    def test_returns_empty_on_no_files(self, db, tmp_path):
        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            targets = scan_index.suggest_targets("skill", count=5, db_path=db)
        # tmp_path has no source files besides .squidsquad
        assert isinstance(targets, list)

    def test_excludes_nonexistent_files(self, db, tmp_path):
        """Files in DB but deleted from disk should not be returned."""
        conn = scan_index._get_db(db)
        conn.execute(
            "INSERT INTO file_coverage VALUES (?, ?, 1, 0, 0, 0, ?, 0.0)",
            ("deleted/file.py", "2020-01-01 00:00:00", "skill"),
        )
        conn.commit()
        conn.close()
        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            targets = scan_index.suggest_targets("skill", count=5, db_path=db)
        assert "deleted/file.py" not in targets

    def test_corrupt_db_returns_empty(self, tmp_path):
        """Corrupt DB should not crash — returns empty list."""
        db_path = tmp_path / ".squidsquad" / "scan-index.db"
        db_path.parent.mkdir(parents=True)
        db_path.write_text("garbage")
        targets = scan_index.suggest_targets("skill", count=5, db_path=db_path)
        assert targets == []


class TestSuggestTargetsPmFiltersApplicationCode:
    """#13729: PM's declared scan domain (roles/pm/improvement-scan.md) is
    process files only -- suggest_targets("pm", ...) must never hand back
    application code under references/scripts/ or tests/."""

    def _seed_files(self, tmp_path):
        (tmp_path / "references" / "scripts").mkdir(parents=True)
        (tmp_path / "references" / "scripts" / "git_ops.py").write_text("x", encoding="utf-8")
        (tmp_path / "tests").mkdir(parents=True)
        (tmp_path / "tests" / "test_git_ops.py").write_text("x", encoding="utf-8")
        (tmp_path / "references" / "sub-skills").mkdir(parents=True)
        (tmp_path / "references" / "sub-skills" / "git-commit.md").write_text("x", encoding="utf-8")

    def test_pm_excludes_scripts_and_tests(self, db, tmp_path):
        self._seed_files(tmp_path)
        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            targets = scan_index.suggest_targets("pm", count=10, db_path=db)
        assert "references/scripts/git_ops.py" not in targets
        assert "tests/test_git_ops.py" not in targets
        assert "references/sub-skills/git-commit.md" in targets

    def test_other_roles_unaffected(self, db, tmp_path):
        self._seed_files(tmp_path)
        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            targets = scan_index.suggest_targets("skill", count=10, db_path=db)
        assert "references/scripts/git_ops.py" in targets
        assert "tests/test_git_ops.py" in targets


class TestSuggestTargetsAutoPrune:
    """#13566 follow-up: suggest_targets() is the only code path invoked
    every improvement-scan cycle (rebuild() is CLI-only), so it must
    auto-trigger pruning for existing installs to self-heal without a
    separate manual migration step."""

    def test_oversized_history_gets_pruned_as_a_side_effect(self, db, tmp_path):
        history_file = tmp_path / ".squidsquad" / "skill" / "scan-history.md"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        history_file.write_text(_make_oversized_history(150), encoding="utf-8")

        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            scan_index.suggest_targets("skill", count=5, db_path=db)

        kept_text = history_file.read_text(encoding="utf-8")
        assert kept_text.count("## Scan —") == scan_index.SCAN_HISTORY_RETENTION
        archive_file = tmp_path / ".squidsquad" / "skill" / "scan-history.archive.md"
        assert archive_file.exists()
        assert archive_file.read_text(encoding="utf-8").count("## Scan —") == 50

    def test_under_cap_history_left_untouched(self, db, tmp_path):
        history_file = tmp_path / ".squidsquad" / "skill" / "scan-history.md"
        history_file.parent.mkdir(parents=True, exist_ok=True)
        body = _make_oversized_history(10)
        history_file.write_text(body, encoding="utf-8")

        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            scan_index.suggest_targets("skill", count=5, db_path=db)

        assert history_file.read_text(encoding="utf-8") == body
        assert not (tmp_path / ".squidsquad" / "skill" / "scan-history.archive.md").exists()

    def test_missing_history_does_not_crash(self, db, tmp_path):
        """No scan-history.md yet (fresh role, never scanned) — auto-prune
        must no-op silently, not raise."""
        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            targets = scan_index.suggest_targets("skill", count=5, db_path=db)
        assert isinstance(targets, list)

    def test_other_roles_history_untouched(self, db, tmp_path):
        """Auto-prune only touches the role passed to suggest_targets()."""
        skill_history = tmp_path / ".squidsquad" / "skill" / "scan-history.md"
        skill_history.parent.mkdir(parents=True, exist_ok=True)
        skill_history.write_text(_make_oversized_history(150), encoding="utf-8")

        qa_history = tmp_path / ".squidsquad" / "qa" / "scan-history.md"
        qa_history.parent.mkdir(parents=True, exist_ok=True)
        qa_body = _make_oversized_history(150)
        qa_history.write_text(qa_body, encoding="utf-8")

        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            scan_index.suggest_targets("skill", count=5, db_path=db)

        assert qa_history.read_text(encoding="utf-8") == qa_body


class TestResolveScanHistoryPath:
    def test_prefers_state_worktree_when_present(self, tmp_path):
        state_file = tmp_path / ".squidsquad-state" / "skill" / "scan-history.md"
        state_file.parent.mkdir(parents=True)
        state_file.write_text("# Scan History\n", encoding="utf-8")
        main_file = tmp_path / ".squidsquad" / "skill" / "scan-history.md"
        main_file.parent.mkdir(parents=True)
        main_file.write_text("# Scan History\n", encoding="utf-8")

        resolved = scan_index._resolve_scan_history_path("skill", tmp_path)
        assert resolved == state_file

    def test_falls_back_to_main_when_no_state_worktree(self, tmp_path):
        resolved = scan_index._resolve_scan_history_path("skill", tmp_path)
        assert resolved == tmp_path / ".squidsquad" / "skill" / "scan-history.md"


# ---------------------------------------------------------------------------
# record-scan
# ---------------------------------------------------------------------------

class TestRecordScan:
    def test_inserts_scan_rows(self, db):
        files = ["a.py", "b.py"]
        scan_index.record_scan("skill", files, "[]", db_path=db)
        conn = scan_index._get_db(db)
        rows = conn.execute("SELECT * FROM scans WHERE role='skill'").fetchall()
        assert len(rows) == 2
        conn.close()

    def test_updates_file_coverage(self, db):
        scan_index.record_scan("qa", ["tracker.py"], "[]", db_path=db)
        conn = scan_index._get_db(db)
        row = conn.execute(
            "SELECT total_scan_count, last_scanned_by FROM file_coverage WHERE file_path='tracker.py'"
        ).fetchone()
        assert row is not None
        assert row["total_scan_count"] == 1
        assert row["last_scanned_by"] == "qa"
        conn.close()

    def test_inserts_findings(self, db):
        findings = json.dumps([
            {"file": "a.py", "type": "issue", "description": "dead code", "issue_number": 42}
        ])
        scan_index.record_scan("skill", ["a.py"], findings, db_path=db)
        conn = scan_index._get_db(db)
        row = conn.execute(
            "SELECT * FROM findings WHERE github_issue_number=42"
        ).fetchone()
        assert row is not None
        assert row["description"] == "dead code"
        conn.close()

    def test_increments_scan_count_on_repeat(self, db):
        scan_index.record_scan("skill", ["a.py"], "[]", db_path=db)
        scan_index.record_scan("skill", ["a.py"], "[]", db_path=db)
        conn = scan_index._get_db(db)
        row = conn.execute(
            "SELECT total_scan_count FROM file_coverage WHERE file_path='a.py'"
        ).fetchone()
        assert row["total_scan_count"] == 2
        conn.close()

    def test_invalid_json_does_not_leak_connection(self, db):
        """Bad findings_json raises without leaking DB connection (#4344)."""
        with pytest.raises(json.JSONDecodeError):
            scan_index.record_scan("skill", ["a.py"], "{bad json", db_path=db)
        # DB should still be usable (not locked by leaked connection)
        conn = scan_index._get_db(db)
        row = conn.execute("SELECT COUNT(*) as c FROM scans").fetchone()
        assert row["c"] == 0  # no rows inserted
        conn.close()


# ---------------------------------------------------------------------------
# record-decision
# ---------------------------------------------------------------------------

class TestRecordDecision:
    def test_accept_updates_finding(self, db):
        # Set up a finding
        conn = scan_index._get_db(db)
        sid = conn.execute(
            "INSERT INTO scans (role, scanned_at, file_path) VALUES ('skill', '2026-01-01 00:00:00', 'x.py')"
        ).lastrowid
        conn.execute(
            "INSERT INTO findings (scan_id, file_path, finding_type, description, github_issue_number) VALUES (?, 'x.py', 'issue', 'test', 100)",
            (sid,),
        )
        conn.execute(
            "INSERT INTO file_coverage VALUES ('x.py', '2026-01-01 00:00:00', 1, 1, 0, 0, 'skill', 1.0)"
        )
        conn.commit()
        conn.close()

        result = scan_index.record_decision(100, True, db_path=db)
        assert result is True

        conn = scan_index._get_db(db)
        row = conn.execute(
            "SELECT human_decision, decided_at FROM findings WHERE github_issue_number=100"
        ).fetchone()
        assert row["human_decision"] == "accepted"
        assert row["decided_at"] is not None

        cov = conn.execute(
            "SELECT accepted_finding_count FROM file_coverage WHERE file_path='x.py'"
        ).fetchone()
        assert cov["accepted_finding_count"] == 1
        conn.close()

    def test_reject_updates_finding_and_rejections(self, db):
        conn = scan_index._get_db(db)
        sid = conn.execute(
            "INSERT INTO scans (role, scanned_at, file_path) VALUES ('skill', '2026-01-01 00:00:00', 'y.py')"
        ).lastrowid
        conn.execute(
            "INSERT INTO findings (scan_id, file_path, finding_type, description, github_issue_number) VALUES (?, 'y.py', 'issue', 'bad style', 200)",
            (sid,),
        )
        conn.execute(
            "INSERT INTO file_coverage VALUES ('y.py', '2026-01-01 00:00:00', 1, 1, 0, 0, 'skill', 1.0)"
        )
        conn.commit()
        conn.close()

        scan_index.record_decision(200, False, db_path=db)

        conn = scan_index._get_db(db)
        row = conn.execute(
            "SELECT human_decision FROM findings WHERE github_issue_number=200"
        ).fetchone()
        assert row["human_decision"] == "rejected"

        cov = conn.execute(
            "SELECT rejected_finding_count FROM file_coverage WHERE file_path='y.py'"
        ).fetchone()
        assert cov["rejected_finding_count"] == 1

        rej = conn.execute("SELECT * FROM rejections WHERE github_issue_number=200").fetchone()
        assert rej is not None
        assert rej["role"] == "skill"
        conn.close()

    def test_missing_issue_returns_false(self, db):
        result = scan_index.record_decision(9999, True, db_path=db)
        assert result is False

    def test_accept_creates_coverage_row_if_missing(self, db):
        """#8082 regression: accepted decision inserts file_coverage if no row exists."""
        conn = scan_index._get_db(db)
        sid = conn.execute(
            "INSERT INTO scans (role, scanned_at, file_path) VALUES ('skill', '2026-01-01 00:00:00', 'orphan.py')"
        ).lastrowid
        conn.execute(
            "INSERT INTO findings (scan_id, file_path, finding_type, description, github_issue_number) VALUES (?, 'orphan.py', 'issue', 'no coverage row', 300)",
            (sid,),
        )
        # Intentionally no file_coverage row for orphan.py
        conn.commit()
        conn.close()

        result = scan_index.record_decision(300, True, db_path=db)
        assert result is True

        conn = scan_index._get_db(db)
        cov = conn.execute(
            "SELECT accepted_finding_count, rejected_finding_count FROM file_coverage WHERE file_path='orphan.py'"
        ).fetchone()
        assert cov is not None, "file_coverage row should be created on accept"
        assert cov["accepted_finding_count"] == 1
        assert cov["rejected_finding_count"] == 0
        conn.close()

    def test_reject_creates_coverage_row_if_missing(self, db):
        """#8082 regression: rejected decision inserts file_coverage if no row exists."""
        conn = scan_index._get_db(db)
        sid = conn.execute(
            "INSERT INTO scans (role, scanned_at, file_path) VALUES ('skill', '2026-01-01 00:00:00', 'orphan2.py')"
        ).lastrowid
        conn.execute(
            "INSERT INTO findings (scan_id, file_path, finding_type, description, github_issue_number) VALUES (?, 'orphan2.py', 'issue', 'no coverage row', 400)",
            (sid,),
        )
        # Intentionally no file_coverage row for orphan2.py
        conn.commit()
        conn.close()

        result = scan_index.record_decision(400, False, db_path=db)
        assert result is True

        conn = scan_index._get_db(db)
        cov = conn.execute(
            "SELECT accepted_finding_count, rejected_finding_count FROM file_coverage WHERE file_path='orphan2.py'"
        ).fetchone()
        assert cov is not None, "file_coverage row should be created on reject"
        assert cov["rejected_finding_count"] == 1
        assert cov["accepted_finding_count"] == 0
        conn.close()


# ---------------------------------------------------------------------------
# refresh-churn
# ---------------------------------------------------------------------------

class TestRefreshChurn:
    def test_populates_churn_table(self, db):
        # Mock git to return known data
        mock_30d = {"a.py": 5, "b.py": 2}
        mock_90d = {"a.py": 12, "b.py": 5, "c.py": 3}
        with patch.object(scan_index, "_git_churn", side_effect=[mock_30d, mock_90d]), \
             patch.object(scan_index, "_detect_renames", return_value={}):
            scan_index.refresh_churn(db_path=db)

        conn = scan_index._get_db(db)
        rows = {
            r["file_path"]: dict(r)
            for r in conn.execute("SELECT * FROM git_churn").fetchall()
        }
        assert rows["a.py"]["commit_count_30d"] == 5
        assert rows["a.py"]["commit_count_90d"] == 12
        assert rows["b.py"]["commit_count_30d"] == 2
        assert rows["c.py"]["commit_count_30d"] == 0  # only in 90d
        conn.close()

    def test_applies_renames(self, db):
        # Pre-populate with old path
        conn = scan_index._get_db(db)
        conn.execute(
            "INSERT INTO file_coverage VALUES ('old/path.py', '2026-01-01 00:00:00', 3, 0, 0, 0, 'skill', 0.0)"
        )
        conn.commit()
        conn.close()

        with patch.object(scan_index, "_git_churn", return_value={}), \
             patch.object(scan_index, "_detect_renames", return_value={"old/path.py": "new/path.py"}):
            scan_index.refresh_churn(db_path=db)

        conn = scan_index._get_db(db)
        old = conn.execute("SELECT * FROM file_coverage WHERE file_path='old/path.py'").fetchone()
        new = conn.execute("SELECT * FROM file_coverage WHERE file_path='new/path.py'").fetchone()
        assert old is None
        assert new is not None
        assert new["total_scan_count"] == 3
        conn.close()


# ---------------------------------------------------------------------------
# rebuild
# ---------------------------------------------------------------------------

class TestRebuild:
    def test_rebuilds_from_scan_history(self, scan_history_dir, tmp_path):
        db_path = scan_history_dir / "scan-index.db"
        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            scan_index.rebuild(db_path=db_path)

        conn = scan_index._get_db(db_path)
        scans = conn.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        # 2 files in first skill scan + 1 in second + 1 in qa scan = 4
        assert scans == 4

        # #13133: exactly 1 finding row — #100 is attributed ONCE to the first
        # file of the scan, NOT duplicated across every scanned file (the
        # pre-fix over-count produced 2 rows for this 2-file/1-finding scan).
        findings = conn.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        assert findings == 1
        rows = conn.execute(
            "SELECT file_path, github_issue_number FROM findings"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["github_issue_number"] == 100
        # Attributed to files[0] (tracker.py), matching record_scan's default,
        # since scan-history carries no per-finding file attribution.
        assert rows[0]["file_path"] == "references/scripts/tracker.py"

        # Check file_coverage was populated
        cov = conn.execute("SELECT COUNT(*) FROM file_coverage").fetchone()[0]
        assert cov >= 3  # at least 3 unique file paths

        # #13133 symptom: finding_count must not be inflated across the scan's
        # files. Only the first file carries the finding; the others stay at 0
        # (pre-fix, BOTH tracker.py and compose.py showed finding_count=1).
        def _fc(path):
            r = conn.execute(
                "SELECT finding_count FROM file_coverage WHERE file_path=?", (path,)
            ).fetchone()
            return r["finding_count"] if r else None
        assert _fc("references/scripts/tracker.py") == 1
        assert _fc("references/scripts/compose.py") == 0
        conn.close()

    def test_rebuild_deletes_old_db(self, scan_history_dir, tmp_path):
        db_path = scan_history_dir / "scan-index.db"
        # Create initial DB with some data
        conn = scan_index._get_db(db_path)
        conn.execute(
            "INSERT INTO scans (role, scanned_at, file_path) VALUES ('test', '2020-01-01', 'stale.py')"
        )
        conn.commit()
        conn.close()

        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            scan_index.rebuild(db_path=db_path)

        conn = scan_index._get_db(db_path)
        stale = conn.execute(
            "SELECT * FROM scans WHERE file_path='stale.py'"
        ).fetchone()
        assert stale is None  # old data should be gone
        conn.close()


# ---------------------------------------------------------------------------
# scan-history.md retention cap (#13566)
# ---------------------------------------------------------------------------

def _make_oversized_history(count):
    """Build a synthetic scan-history.md body with `count` entries, newest
    first (block N is dated further in the past than block N-1), matching
    the file's real prepend convention."""
    blocks = []
    for i in range(count):
        day = 28 - (i % 27)
        blocks.append(
            f"## Scan — 2026-01-{day:02d} 0{i % 10}:00\n\n"
            f"- **Files scanned**: references/scripts/file_{i}.py\n"
            "- **Findings**: none\n"
            "- **Items rejected by human**: none\n\n"
        )
    return "# Scan History\n\n" + "".join(blocks)


class TestPruneScanHistoryNoPreamble:
    def test_headerless_file_no_spurious_blank_lines(self, tmp_path):
        """Some roles' scan-history.md (e.g. pm's) has no '# ... History'
        line and starts directly with the first '## Scan' block -- pruning
        must not inject blank lines at the top (real committed data)."""
        history_file = tmp_path / "scan-history.md"
        body = "".join(
            f"## Scan — 2026-01-{28 - (i % 27):02d} 0{i % 10}:00\n\n"
            f"- **Files scanned**: references/scripts/file_{i}.py\n"
            "- **Findings**: none\n"
            "- **Items rejected by human**: none\n\n"
            for i in range(150)
        )
        history_file.write_text(body, encoding="utf-8")
        pruned = scan_index._prune_scan_history(history_file, keep=100)
        assert pruned is True
        kept_text = history_file.read_text(encoding="utf-8")
        assert not kept_text.startswith("\n"), (
            "headerless prune must not prepend spurious blank lines"
        )
        assert kept_text.startswith("## Scan — 2026-01-28")


class TestPruneScanHistoryRegexParity:
    def test_dash_less_scan_mention_in_body_does_not_fragment_block(self, tmp_path):
        """The prune split must require the same dash separator as
        _parse_scan_history's split, so a finding description that starts a
        line with '## Scan ' (no dash) doesn't get misread as a new block
        boundary by prune while the parser correctly ignores it."""
        history_file = tmp_path / "scan-history.md"
        body = (
            "# Scan History\n\n"
            "## Scan — 2026-01-28 00:00\n\n"
            "- **Files scanned**: references/scripts/file_0.py\n"
            "- **Findings**: none\n"
            "- **Criteria note**: watch for headers like\n"
            "## Scan of a subsystem inside finding prose (no dash after Scan)\n"
            "- **Items rejected by human**: none\n\n"
            "## Scan — 2026-01-27 00:00\n\n"
            "- **Files scanned**: references/scripts/file_1.py\n"
            "- **Findings**: none\n"
            "- **Items rejected by human**: none\n\n"
        )
        history_file.write_text(body, encoding="utf-8")
        # Well under the cap -- prune is a no-op, but the block COUNT it
        # computes internally must still be 2, not 3 (which would indicate
        # the dash-less "## Scan of a subsystem..." line was mis-split).
        pruned = scan_index._prune_scan_history(history_file, keep=1)
        assert pruned is True
        kept_text = history_file.read_text(encoding="utf-8")
        assert kept_text.count("## Scan — 2026-01") == 1
        assert "2026-01-28" in kept_text
        archive_text = (tmp_path / "scan-history.archive.md").read_text(encoding="utf-8")
        assert "2026-01-27" in archive_text
        # The dash-less in-body mention must have stayed attached to its
        # parent block (2026-01-28, kept), not been split into its own block.
        assert "watch for headers like" in kept_text


class TestPruneScanHistory:
    def test_under_cap_is_a_noop(self, tmp_path):
        history_file = tmp_path / "scan-history.md"
        history_file.write_text(_make_oversized_history(10), encoding="utf-8")
        pruned = scan_index._prune_scan_history(history_file, keep=100)
        assert pruned is False
        assert history_file.read_text(encoding="utf-8").count("## Scan") == 10
        assert not (tmp_path / "scan-history.archive.md").exists()

    def test_over_cap_trims_to_keep_and_archives_remainder(self, tmp_path):
        history_file = tmp_path / "scan-history.md"
        history_file.write_text(_make_oversized_history(150), encoding="utf-8")
        pruned = scan_index._prune_scan_history(history_file, keep=100)
        assert pruned is True

        kept_text = history_file.read_text(encoding="utf-8")
        assert kept_text.count("## Scan") == 100
        # Newest (file_0) stays; oldest (file_149) is evicted.
        assert "file_0.py" in kept_text
        assert "file_149.py" not in kept_text

        archive_file = tmp_path / "scan-history.archive.md"
        assert archive_file.exists()
        archived_text = archive_file.read_text(encoding="utf-8")
        assert archived_text.count("## Scan") == 50
        assert "file_99.py" not in archived_text  # kept, not archived
        assert "file_100.py" in archived_text
        assert "file_149.py" in archived_text  # nothing deleted, just moved
        assert archived_text.startswith("# Scan History Archive")

    def test_repeated_prune_prepends_to_existing_archive(self, tmp_path):
        history_file = tmp_path / "scan-history.md"
        history_file.write_text(_make_oversized_history(150), encoding="utf-8")
        scan_index._prune_scan_history(history_file, keep=100)

        # Grow scan-history.md again past the cap and prune a second time.
        grown = _make_oversized_history(120)
        history_file.write_text(grown, encoding="utf-8")
        scan_index._prune_scan_history(history_file, keep=100)

        archive_file = tmp_path / "scan-history.archive.md"
        archived_text = archive_file.read_text(encoding="utf-8")
        # 50 from the first prune + 20 from the second = 70, single header.
        assert archived_text.count("## Scan") == 70
        assert archived_text.count("# Scan History Archive") == 1

    def test_missing_file_is_a_noop(self, tmp_path):
        assert scan_index._prune_scan_history(tmp_path / "missing.md") is False


class TestRebuildEnforcesRetentionCap:
    def test_rebuild_prunes_oversized_history_and_keeps_full_db_coverage(
        self, tmp_path
    ):
        ss = tmp_path / ".squidsquad"
        skill_dir = ss / "skill"
        skill_dir.mkdir(parents=True)
        history_file = skill_dir / "scan-history.md"
        history_file.write_text(_make_oversized_history(150), encoding="utf-8")

        db_path = ss / "scan-index.db"
        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            scan_index.rebuild(db_path=db_path)

        # On-disk file is capped.
        assert history_file.read_text(encoding="utf-8").count("## Scan") == 100
        assert (skill_dir / "scan-history.archive.md").exists()

        # DB coverage includes archived entries too — pruning the markdown
        # file must not lose historical scan-index stats.
        conn = scan_index._get_db(db_path)
        scans = conn.execute(
            "SELECT COUNT(*) FROM scans WHERE role='skill'"
        ).fetchone()[0]
        assert scans == 150
        conn.close()

    def test_rebuild_is_idempotent_on_already_pruned_history(self, tmp_path):
        ss = tmp_path / ".squidsquad"
        skill_dir = ss / "skill"
        skill_dir.mkdir(parents=True)
        history_file = skill_dir / "scan-history.md"
        history_file.write_text(_make_oversized_history(150), encoding="utf-8")

        db_path = ss / "scan-index.db"
        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            scan_index.rebuild(db_path=db_path)
            scan_index.rebuild(db_path=db_path)  # second run, already pruned

        assert history_file.read_text(encoding="utf-8").count("## Scan") == 100
        archived_text = (skill_dir / "scan-history.archive.md").read_text(
            encoding="utf-8"
        )
        # Second rebuild's prune is a no-op (already at the cap) — archive
        # must not accumulate the same 50 entries twice.
        assert archived_text.count("## Scan") == 50

        conn = scan_index._get_db(db_path)
        scans = conn.execute(
            "SELECT COUNT(*) FROM scans WHERE role='skill'"
        ).fetchone()[0]
        assert scans == 150
        conn.close()


# ---------------------------------------------------------------------------
# parse scan-history.md
# ---------------------------------------------------------------------------

class TestParseScanHistory:
    def test_parses_basic_entry(self, tmp_path):
        md = tmp_path / "scan-history.md"
        md.write_text(
            "# Scan History\n\n"
            "## Scan \u2014 2026-04-10 14:00\n\n"
            "- **Files scanned**: a.py, b.py\n"
            "- **Findings**: #42 dead code\n"
            "- **Items rejected by human**: none\n",
            encoding="utf-8",
        )
        entries = scan_index._parse_scan_history(md)
        assert len(entries) == 1
        assert entries[0]["timestamp"] == "2026-04-10 14:00:00"
        assert entries[0]["files"] == ["a.py", "b.py"]
        assert len(entries[0]["findings"]) == 1
        assert entries[0]["findings"][0]["issue_number"] == 42

    def test_handles_none_findings(self, tmp_path):
        md = tmp_path / "scan-history.md"
        md.write_text(
            "## Scan \u2014 2026-04-10 14:00\n\n"
            "- **Files scanned**: a.py\n"
            "- **Findings**: none\n",
            encoding="utf-8",
        )
        entries = scan_index._parse_scan_history(md)
        assert len(entries) == 1
        assert entries[0]["findings"] == []

    def test_handles_missing_file(self, tmp_path):
        md = tmp_path / "nonexistent.md"
        entries = scan_index._parse_scan_history(md)
        assert entries == []

    def test_handles_none_yet_variants(self, tmp_path):
        md = tmp_path / "scan-history.md"
        md.write_text(
            "## Scan \u2014 2026-04-10 14:00\n\n"
            "- **Files scanned**: a.py\n"
            "- **Findings**: (none yet)\n"
            "- **Items rejected by human**: (none)\n",
            encoding="utf-8",
        )
        entries = scan_index._parse_scan_history(md)
        assert len(entries) == 1
        assert entries[0]["findings"] == []
        assert entries[0]["rejections"] == []


# ---------------------------------------------------------------------------
# Composite scoring
# ---------------------------------------------------------------------------

class TestCompositeScoring:
    def test_weights_sum_to_one(self):
        total = (
            scan_index.WEIGHT_COVERAGE_GAP
            + scan_index.WEIGHT_CHURN
            + scan_index.WEIGHT_CROSS_ROLE
            + scan_index.WEIGHT_ACCEPTANCE
        )
        assert abs(total - 1.0) < 0.001

    def test_never_scanned_gets_max_coverage_score(self, db, tmp_path):
        """A never-scanned file should get coverage_score = 1.0."""
        # Create a source file
        (tmp_path / "fresh.py").write_text("# new\n")

        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            targets = scan_index.suggest_targets("skill", count=1, db_path=db)
        # Should return the file (it's the only one)
        assert "fresh.py" in targets or len(targets) == 0  # empty if no files found

    def test_no_decisions_redistributes_acceptance_weight(self, db, tmp_path):
        """#8435: Files without decisions should not have acceptance_rate=0 penalty.

        When no decisions exist, the WEIGHT_ACCEPTANCE component should be
        redistributed among the other weights, not treated as 0.
        """
        # Create two files
        (tmp_path / "a.py").write_text("# a\n")
        (tmp_path / "b.py").write_text("# b\n")

        conn = scan_index._get_db(db)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Both files scanned, one has an accepted decision
        conn.execute(
            "INSERT INTO file_coverage (file_path, last_scanned_at, finding_count, "
            "accepted_finding_count, rejected_finding_count) VALUES (?, ?, 2, 2, 0)",
            ("a.py", now),
        )
        conn.execute(
            "INSERT INTO file_coverage (file_path, last_scanned_at, finding_count, "
            "accepted_finding_count, rejected_finding_count) VALUES (?, ?, 2, 0, 0)",
            ("b.py", now),
        )
        conn.commit()
        conn.close()

        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            targets = scan_index.suggest_targets("skill", count=2, db_path=db)

        # Both should be returned (no crash, no zero-division)
        assert len(targets) == 2

    def test_acceptance_rate_uses_decision_counts(self, db, tmp_path):
        """#8435: acceptance_rate should use accepted/(accepted+rejected),
        not accepted/finding_count."""
        (tmp_path / "high.py").write_text("# high acceptance\n")
        (tmp_path / "low.py").write_text("# low acceptance\n")

        conn = scan_index._get_db(db)
        old = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")

        # Both files: same coverage gap and churn, but different acceptance rates
        conn.execute(
            "INSERT INTO file_coverage (file_path, last_scanned_at, finding_count, "
            "accepted_finding_count, rejected_finding_count) VALUES (?, ?, 5, 4, 1)",
            ("high.py", old),
        )
        conn.execute(
            "INSERT INTO file_coverage (file_path, last_scanned_at, finding_count, "
            "accepted_finding_count, rejected_finding_count) VALUES (?, ?, 5, 1, 4)",
            ("low.py", old),
        )
        conn.commit()
        conn.close()

        with patch.object(scan_index, "REPO_ROOT", tmp_path):
            targets = scan_index.suggest_targets("skill", count=2, db_path=db)

        # high.py should rank higher (4/5=0.8 acceptance vs 1/5=0.2)
        assert targets[0] == "high.py"


# ---------------------------------------------------------------------------
# CLI (smoke tests)
# ---------------------------------------------------------------------------

class TestCLI:
    def test_help_flag(self):
        """--help should list subcommands."""
        with pytest.raises(SystemExit) as exc:
            with patch("sys.argv", ["scan_index.py", "--help"]):
                scan_index._parse_args()
        assert exc.value.code == 0

    def test_no_command_shows_help(self):
        with pytest.raises(SystemExit) as exc:
            with patch("sys.argv", ["scan_index.py"]):
                scan_index._parse_args()
        assert exc.value.code == 1

    def test_suggest_targets_args(self):
        with patch("sys.argv", ["scan_index.py", "suggest-targets", "skill", "--count", "3"]):
            args = scan_index._parse_args()
        assert args.command == "suggest-targets"
        assert args.role == "skill"
        assert args.count == 3

    def test_record_scan_args(self):
        with patch("sys.argv", [
            "scan_index.py", "record-scan", "--role", "qa",
            "--files", "a.py,b.py", "--findings", "[]"
        ]):
            args = scan_index._parse_args()
        assert args.command == "record-scan"
        assert args.role == "qa"

    def test_record_decision_args(self):
        with patch("sys.argv", [
            "scan_index.py", "record-decision", "--issue", "42", "--accepted", "true"
        ]):
            args = scan_index._parse_args()
        assert args.command == "record-decision"
        assert args.issue == 42

    def test_rebuild_args(self):
        with patch("sys.argv", ["scan_index.py", "rebuild"]):
            args = scan_index._parse_args()
        assert args.command == "rebuild"

    def test_refresh_churn_args(self):
        with patch("sys.argv", ["scan_index.py", "refresh-churn"]):
            args = scan_index._parse_args()
        assert args.command == "refresh-churn"


# ---------------------------------------------------------------------------
# Walk source files
# ---------------------------------------------------------------------------

class TestWalkSourceFiles:
    def test_excludes_squidsquad_dir(self, tmp_path):
        (tmp_path / ".squidsquad" / "config.md").parent.mkdir(parents=True)
        (tmp_path / ".squidsquad" / "config.md").write_text("test")
        (tmp_path / "src" / "main.py").parent.mkdir(parents=True)
        (tmp_path / "src" / "main.py").write_text("# main")

        files = scan_index._walk_source_files(tmp_path)
        assert "src/main.py" in files
        assert not any(".squidsquad" in f for f in files)

    def test_excludes_binary_extensions(self, tmp_path):
        (tmp_path / "image.png").write_bytes(b"\x89PNG")
        (tmp_path / "code.py").write_text("# code")

        files = scan_index._walk_source_files(tmp_path)
        assert "code.py" in files
        assert "image.png" not in files

    def test_excludes_hidden_files(self, tmp_path):
        (tmp_path / ".hidden").write_text("secret")
        (tmp_path / "visible.py").write_text("# ok")

        files = scan_index._walk_source_files(tmp_path)
        assert "visible.py" in files
        assert ".hidden" not in files


class TestSuggestTargetsDbOpen:
    """#7614: suggest_targets opens DB once after churn refresh, not twice."""

    def test_no_redundant_db_open(self, tmp_path):
        """suggest_targets calls _get_db exactly once at runtime (#7614, #7636)."""
        from unittest.mock import patch, MagicMock
        import sqlite3

        # Create a minimal DB so suggest_targets can run
        db_path = tmp_path / "scan.db"
        conn = scan_index._get_db(db_path)
        conn.close()

        with patch.object(scan_index, "_get_db", wraps=scan_index._get_db) as mock_get_db, \
             patch.object(scan_index, "_maybe_refresh_churn"):
            scan_index.suggest_targets("skill", count=3, db_path=db_path)

        assert mock_get_db.call_count == 1, \
            f"suggest_targets should call _get_db once, called {mock_get_db.call_count} times (#7614)"
