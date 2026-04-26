"""Tests for references/scripts/migrate_state_branch.py — mocked subprocess, no real git."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Allow import from references/scripts/
SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import migrate_state_branch


# ---------------------------------------------------------------------------
# _is_state_file() — pattern matching
# ---------------------------------------------------------------------------

class TestIsStateFile:
    """STATE_PATTERNS matching logic."""

    def test_current_state_matches(self):
        assert migrate_state_branch._is_state_file("skill/current-state") is True

    def test_working_state_matches(self):
        assert migrate_state_branch._is_state_file("pm/working-state.md") is True

    def test_iterations_dir_matches(self):
        assert migrate_state_branch._is_state_file("skill/iterations/iter-1.md") is True

    def test_health_file_matches(self):
        assert migrate_state_branch._is_state_file("skill/.health") is True

    def test_pid_file_matches(self):
        assert migrate_state_branch._is_state_file("qa/.pid") is True

    def test_context_pressure_matches(self):
        assert migrate_state_branch._is_state_file("dm/context-pressure") is True

    def test_restart_log_matches(self):
        assert migrate_state_branch._is_state_file("skill/restart-log.txt") is True

    def test_scan_history_matches(self):
        assert migrate_state_branch._is_state_file("skill/scan-history.md") is True

    def test_vault_dir_matches(self):
        assert migrate_state_branch._is_state_file("vault/BRIEFING.md") is True

    def test_vault_subdirs_match(self):
        assert migrate_state_branch._is_state_file("vault/galaxy/note.md") is True

    def test_config_does_not_match(self):
        assert migrate_state_branch._is_state_file("config.md") is False

    def test_claude_md_does_not_match(self):
        assert migrate_state_branch._is_state_file("skill/CLAUDE.md") is False

    def test_soul_md_does_not_match(self):
        assert migrate_state_branch._is_state_file("skill/SOUL.md") is False

    def test_planning_does_not_match(self):
        assert migrate_state_branch._is_state_file("pm/planning/CONTEXT.md") is False

    def test_local_config_does_not_match(self):
        assert migrate_state_branch._is_state_file(".local-config") is False

    def test_backslash_normalized(self):
        """Windows paths with backslashes should still match."""
        assert migrate_state_branch._is_state_file("skill\\current-state") is True

    def test_empty_string_does_not_match(self):
        assert migrate_state_branch._is_state_file("") is False

    def test_random_file_does_not_match(self):
        assert migrate_state_branch._is_state_file("skill/random-file.txt") is False


# ---------------------------------------------------------------------------
# find_state_files() — file discovery
# ---------------------------------------------------------------------------

class TestFindStateFiles:
    def test_returns_empty_when_no_squidsquad_dir(self, tmp_path):
        """Returns empty list when .squidsquad/ doesn't exist."""
        with patch.object(migrate_state_branch, "SQUIDSQUAD_DIR", tmp_path / "nonexistent"):
            result = migrate_state_branch.find_state_files()
        assert result == []

    def test_finds_state_files(self, tmp_path):
        """Discovers state files matching STATE_PATTERNS."""
        squid = tmp_path / ".squidsquad"
        (squid / "skill").mkdir(parents=True)
        (squid / "skill" / "current-state").write_text("idle|")
        (squid / "skill" / "working-state.md").write_text("# Working State")
        (squid / "skill" / "CLAUDE.md").write_text("# Instructions")
        (squid / "skill" / "iterations").mkdir()
        (squid / "skill" / "iterations" / "iter-1.md").write_text("log")

        with patch.object(migrate_state_branch, "SQUIDSQUAD_DIR", squid):
            result = migrate_state_branch.find_state_files()

        names = [str(r) for r in result]
        assert any("current-state" in n for n in names)
        assert any("working-state.md" in n for n in names)
        assert any("iter-1.md" in n for n in names)
        # CLAUDE.md should NOT be in the list
        assert not any("CLAUDE.md" in n for n in names)

    def test_results_are_sorted(self, tmp_path):
        """Results should be sorted."""
        squid = tmp_path / ".squidsquad"
        (squid / "skill").mkdir(parents=True)
        (squid / "skill" / "working-state.md").write_text("")
        (squid / "skill" / "current-state").write_text("")

        with patch.object(migrate_state_branch, "SQUIDSQUAD_DIR", squid):
            result = migrate_state_branch.find_state_files()

        assert result == sorted(result)


# ---------------------------------------------------------------------------
# migrate() — dry-run and error handling
# ---------------------------------------------------------------------------

class TestMigrate:
    def test_dry_run_returns_zero_no_side_effects(self, tmp_path):
        """Dry run prints files but doesn't move them."""
        squid = tmp_path / ".squidsquad"
        (squid / "skill").mkdir(parents=True)
        (squid / "skill" / "current-state").write_text("idle|")

        with patch.object(migrate_state_branch, "SQUIDSQUAD_DIR", squid):
            result = migrate_state_branch.migrate(dry_run=True)

        assert result == 0
        # File should still exist in original location
        assert (squid / "skill" / "current-state").exists()

    def test_no_files_returns_zero(self, tmp_path):
        """Returns 0 when no state files exist."""
        squid = tmp_path / ".squidsquad"
        squid.mkdir()
        (squid / "config.md").write_text("# Config")

        with patch.object(migrate_state_branch, "SQUIDSQUAD_DIR", squid):
            result = migrate_state_branch.migrate(dry_run=True)

        assert result == 0

    @patch("migrate_state_branch.find_state_files", return_value=[])
    def test_empty_migration_skips_commit(self, mock_find):
        """No commit when nothing to migrate."""
        with patch.dict("sys.modules", {"state_bus": MagicMock()}):
            result = migrate_state_branch.migrate(dry_run=False)
        assert result == 0


# ---------------------------------------------------------------------------
# main() — CLI arg parsing
# ---------------------------------------------------------------------------

class TestMain:
    def test_help_flag_returns_zero(self):
        with patch("sys.argv", ["migrate_state_branch.py", "--help"]):
            result = migrate_state_branch.main()
        assert result == 0

    def test_dry_run_flag_parsed(self):
        with patch("sys.argv", ["migrate_state_branch.py", "--dry-run"]), \
             patch.object(migrate_state_branch, "migrate", return_value=0) as mock_migrate:
            result = migrate_state_branch.main()
        mock_migrate.assert_called_once_with(dry_run=True)
        assert result == 0

    def test_exception_returns_one(self):
        with patch("sys.argv", ["migrate_state_branch.py"]), \
             patch.object(migrate_state_branch, "migrate", side_effect=RuntimeError("boom")):
            result = migrate_state_branch.main()
        assert result == 1
