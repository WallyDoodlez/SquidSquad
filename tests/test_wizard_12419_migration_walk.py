"""Unit tests for the INSTALLER-ARCH §10 migration-walk deterministic helpers (#12419).

Covers the wizard.py code half — version reads, chain selection, stamping, and
the aggregate plan. The LLM-driven three-gate application (DeepSeek audit /
mini-CQ / compose dry-run) lives in the WIZARD.md runbook and is not unit-tested
here; these tests pin the deterministic *what to apply*, not the *how*.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import wizard  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures: build a synthetic base_dir with .squidsquad/config.md + migrations/
# ---------------------------------------------------------------------------


def _write_config(base, version=None):
    """Create base/.squidsquad/config.md, optionally with a version stamp line."""
    squid = base / ".squidsquad"
    squid.mkdir(parents=True, exist_ok=True)
    lines = ["# SquidSquad Config", ""]
    if version is not None:
        lines.append(f"- **SquidSquad Version**: {version}")
    lines += ["- **Tracker**: github-issues", "", "## Project", "", "- **Name**: demo", ""]
    (squid / "config.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return squid / "config.md"


def _write_migrations(base, steps):
    """Create base/references/migrations/v<a>-to-v<b>.md for each (a, b) in steps."""
    mig = base / "references" / "migrations"
    mig.mkdir(parents=True, exist_ok=True)
    for frm, to in steps:
        (mig / f"v{frm}-to-v{to}.md").write_text(
            f"# Migration: v{frm} -> v{to}\n\nMechanical change.\n", encoding="utf-8"
        )
    return mig


def _write_installer_version(base, version):
    vf = base / "references" / "VERSION"
    vf.parent.mkdir(parents=True, exist_ok=True)
    vf.write_text(version + "\n", encoding="utf-8")
    return vf


# ---------------------------------------------------------------------------
# _parse_version / _version_key
# ---------------------------------------------------------------------------


class TestVersionParsing:
    @pytest.mark.parametrize("inp,expected", [
        ("1.4", (1, 4)),
        ("0.44.0", (0, 44, 0)),
        ("v1.5", (1, 5)),
        ("V2.0.1", (2, 0, 1)),
        ("  1.2  ", (1, 2)),
    ])
    def test_parse_ok(self, inp, expected):
        assert wizard._parse_version(inp) == expected

    @pytest.mark.parametrize("inp", ["", None, "abc", "1.x", "v"])
    def test_parse_junk_is_none(self, inp):
        assert wizard._parse_version(inp) is None

    def test_ordering_shorter_is_prefix(self):
        # (1, 4) < (1, 4, 1) — a release that adds a patch sorts after.
        assert wizard._version_key("1.4") < wizard._version_key("1.4.1")
        assert wizard._version_key("1.4") < wizard._version_key("1.5")

    def test_junk_sorts_lowest(self):
        assert wizard._version_key("garbage") < wizard._version_key("0.0.0")


# ---------------------------------------------------------------------------
# installed_version — AC1 (existing reads version; fresh returns None)
# ---------------------------------------------------------------------------


class TestInstalledVersion:
    def test_fresh_install_returns_none(self, tmp_path):
        """No .squidsquad/ → fresh → None (walk skipped)."""
        assert wizard.installed_version(tmp_path) is None

    def test_reads_stamp(self, tmp_path):
        _write_config(tmp_path, version="1.4")
        assert wizard.installed_version(tmp_path) == "1.4"

    def test_existing_without_stamp_is_pre_stamp(self, tmp_path):
        """Existing install, no version line → pre-1.0 sentinel, not None."""
        _write_config(tmp_path, version=None)
        assert wizard.installed_version(tmp_path) == wizard.PRE_VERSION_STAMP

    def test_empty_stamp_value_is_pre_stamp(self, tmp_path):
        squid = tmp_path / ".squidsquad"
        squid.mkdir(parents=True)
        (squid / "config.md").write_text(
            "# SquidSquad Config\n\n- **SquidSquad Version**:\n", encoding="utf-8"
        )
        assert wizard.installed_version(tmp_path) == wizard.PRE_VERSION_STAMP


# ---------------------------------------------------------------------------
# installer_version
# ---------------------------------------------------------------------------


class TestInstallerVersion:
    def test_reads_version_file(self, tmp_path):
        _write_installer_version(tmp_path, "1.5")
        assert wizard.installer_version(tmp_path) == "1.5"

    def test_missing_file_is_none(self, tmp_path):
        assert wizard.installer_version(tmp_path) is None

    def test_real_repo_has_version_file(self):
        """The shipped references/VERSION exists and parses (the installer-version source)."""
        v = wizard.installer_version(REPO_ROOT)
        assert v is not None
        assert wizard._parse_version(v) is not None


# ---------------------------------------------------------------------------
# list_migration_files / select_migration_chain — AC2 (ordered application)
# ---------------------------------------------------------------------------


class TestMigrationChain:
    def test_no_migrations_dir_empty(self, tmp_path):
        assert wizard.list_migration_files(tmp_path) == []
        assert wizard.select_migration_chain("1.0", "1.5", tmp_path) == []

    def test_chain_in_version_order(self, tmp_path):
        # Deliberately create out of lexical order to prove version sort.
        _write_migrations(tmp_path, [("1.4", "1.5"), ("1.2", "1.3"), ("1.3", "1.4")])
        chain = wizard.select_migration_chain("1.2", "1.5", tmp_path)
        assert [c["to"] for c in chain] == ["1.3", "1.4", "1.5"]

    def test_chain_excludes_already_applied(self, tmp_path):
        _write_migrations(tmp_path, [("1.2", "1.3"), ("1.3", "1.4"), ("1.4", "1.5")])
        # Installed at 1.3 → only 1.4 and 1.5 remain.
        chain = wizard.select_migration_chain("1.3", "1.5", tmp_path)
        assert [c["to"] for c in chain] == ["1.4", "1.5"]

    def test_chain_excludes_beyond_target(self, tmp_path):
        _write_migrations(tmp_path, [("1.2", "1.3"), ("1.3", "1.4"), ("1.4", "1.5")])
        # Target 1.4 → 1.5 migration excluded.
        chain = wizard.select_migration_chain("1.2", "1.4", tmp_path)
        assert [c["to"] for c in chain] == ["1.3", "1.4"]

    def test_target_le_installed_is_noop(self, tmp_path):
        _write_migrations(tmp_path, [("1.2", "1.3"), ("1.3", "1.4")])
        assert wizard.select_migration_chain("1.4", "1.4", tmp_path) == []
        assert wizard.select_migration_chain("1.4", "1.3", tmp_path) == []

    def test_missing_step_skipped_silently(self, tmp_path):
        # Gap: no 1.3->1.4 file. Walk applies 1.2->1.3 and 1.4->1.5, skips the gap.
        _write_migrations(tmp_path, [("1.2", "1.3"), ("1.4", "1.5")])
        chain = wizard.select_migration_chain("1.2", "1.5", tmp_path)
        assert [c["to"] for c in chain] == ["1.3", "1.5"]

    def test_pre_stamp_walks_all(self, tmp_path):
        _write_migrations(tmp_path, [("0.9", "1.0"), ("1.0", "1.1")])
        chain = wizard.select_migration_chain(wizard.PRE_VERSION_STAMP, "1.1", tmp_path)
        assert [c["to"] for c in chain] == ["1.0", "1.1"]

    def test_non_migration_files_ignored(self, tmp_path):
        mig = _write_migrations(tmp_path, [("1.2", "1.3")])
        (mig / "README.md").write_text("# Migration format\n", encoding="utf-8")
        (mig / "notes.txt").write_text("scratch", encoding="utf-8")
        files = wizard.list_migration_files(tmp_path)
        assert [f["file"] for f in files] == ["v1.2-to-v1.3.md"]


# ---------------------------------------------------------------------------
# stamp_version — AC4 (installer stamps; preservation)
# ---------------------------------------------------------------------------


class TestStampVersion:
    def test_replaces_existing_stamp(self, tmp_path):
        cfg = _write_config(tmp_path, version="1.4")
        assert wizard.stamp_version("1.5", tmp_path) is True
        text = cfg.read_text(encoding="utf-8")
        assert "- **SquidSquad Version**: 1.5" in text
        assert "1.4" not in text

    def test_inserts_when_absent(self, tmp_path):
        cfg = _write_config(tmp_path, version=None)
        assert wizard.stamp_version("1.0", tmp_path) is True
        text = cfg.read_text(encoding="utf-8")
        assert "- **SquidSquad Version**: 1.0" in text

    def test_preserves_other_content(self, tmp_path):
        """AC4: stamping must not wipe other config — only the version line changes."""
        cfg = _write_config(tmp_path, version="1.4")
        before = cfg.read_text(encoding="utf-8")
        wizard.stamp_version("1.5", tmp_path)
        after = cfg.read_text(encoding="utf-8")
        for marker in ("## Project", "- **Name**: demo", "- **Tracker**: github-issues"):
            assert marker in after, f"{marker} must survive a stamp"
        # Only the version line differs.
        assert before.replace("1.4", "1.5") == after

    def test_no_config_returns_false(self, tmp_path):
        assert wizard.stamp_version("1.5", tmp_path) is False

    def test_idempotent(self, tmp_path):
        _write_config(tmp_path, version="1.4")
        wizard.stamp_version("1.5", tmp_path)
        wizard.stamp_version("1.5", tmp_path)
        text = (tmp_path / ".squidsquad" / "config.md").read_text(encoding="utf-8")
        assert text.count("- **SquidSquad Version**:") == 1


# ---------------------------------------------------------------------------
# migration_walk_plan — the aggregate the runbook consumes
# ---------------------------------------------------------------------------


class TestMigrationWalkPlan:
    def test_fresh_install_plan(self, tmp_path):
        """AC1: fresh install → is_fresh, is_noop, no walk."""
        _write_installer_version(tmp_path, "1.5")
        plan = wizard.migration_walk_plan(tmp_path)
        assert plan["is_fresh"] is True
        assert plan["is_noop"] is True
        assert plan["chain"] == []
        assert plan["installed_version"] is None

    def test_existing_with_chain(self, tmp_path):
        _write_config(tmp_path, version="1.2")
        _write_installer_version(tmp_path, "1.5")
        _write_migrations(tmp_path, [("1.2", "1.3"), ("1.3", "1.4"), ("1.4", "1.5")])
        plan = wizard.migration_walk_plan(tmp_path)
        assert plan["is_fresh"] is False
        assert plan["is_pre_stamp"] is False
        assert plan["is_noop"] is False
        assert plan["installed_version"] == "1.2"
        assert plan["installer_version"] == "1.5"
        assert [c["to"] for c in plan["chain"]] == ["1.3", "1.4", "1.5"]

    def test_existing_up_to_date_is_noop(self, tmp_path):
        _write_config(tmp_path, version="1.5")
        _write_installer_version(tmp_path, "1.5")
        _write_migrations(tmp_path, [("1.4", "1.5")])
        plan = wizard.migration_walk_plan(tmp_path)
        assert plan["is_fresh"] is False
        assert plan["is_noop"] is True
        assert plan["chain"] == []

    def test_pre_stamp_install_walks_all(self, tmp_path):
        _write_config(tmp_path, version=None)
        _write_installer_version(tmp_path, "1.1")
        _write_migrations(tmp_path, [("0.9", "1.0"), ("1.0", "1.1")])
        plan = wizard.migration_walk_plan(tmp_path)
        assert plan["is_pre_stamp"] is True
        assert plan["is_noop"] is False
        assert [c["to"] for c in plan["chain"]] == ["1.0", "1.1"]
