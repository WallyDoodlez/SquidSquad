"""Regression tests for #1210 — cycle.py is-quiet handler.

The is-quiet functionality lives in vault_remember.py. It checks the most recent
iteration log file within the configured interval window and returns whether the
cycle was quiet (Type: quiet) or non-quiet (Type: active).

These tests verify the is_quiet() function correctly identifies quiet vs active
cycles based on iteration log content and file recency.
"""

import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import vault_remember


class TestIsQuietNoIterations:
    """#1210: is_quiet returns True when no iterations directory exists."""

    def test_no_iterations_dir_is_quiet(self, tmp_path):
        """#1210: Missing iterations dir should be treated as quiet."""
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path):
            assert vault_remember.is_quiet("skill") is True

    def test_no_iterations_dir_prints_quiet(self, tmp_path, capsys):
        """#1210: Missing iterations dir should print 'quiet'."""
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path):
            vault_remember.is_quiet("skill")
        assert capsys.readouterr().out.strip() == "quiet"


class TestIsQuietWithIterations:
    """#1210: is_quiet reads Type field from most recent iteration file."""

    def _make_iter_file(self, iter_dir, n, type_val="active", age_minutes=0):
        """Helper: create an iteration file with a given Type and mtime."""
        iter_dir.mkdir(parents=True, exist_ok=True)
        path = iter_dir / f"iter-{n}.md"
        content = (
            f"# Iteration {n}\n\n"
            f"- **Date**: 2026-04-19 12:00\n"
            f"- **Type**: {type_val}\n"
            f"- **Work Summary**:\n"
            f"  - test\n"
        )
        path.write_text(content, encoding="utf-8")
        if age_minutes > 0:
            mtime = time.time() - (age_minutes * 60)
            import os
            os.utime(str(path), (mtime, mtime))
        return path

    def test_active_cycle_is_non_quiet(self, tmp_path, capsys):
        """#1210: An active iteration log within the window means non-quiet."""
        iter_dir = tmp_path / "skill" / "iterations"
        self._make_iter_file(iter_dir, 1, type_val="active", age_minutes=0)
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="30"):
            result = vault_remember.is_quiet("skill")
        assert result is False
        assert capsys.readouterr().out.strip() == "non-quiet"

    def test_quiet_cycle_is_quiet(self, tmp_path, capsys):
        """#1210: A quiet iteration log within the window means quiet."""
        iter_dir = tmp_path / "skill" / "iterations"
        self._make_iter_file(iter_dir, 1, type_val="quiet", age_minutes=0)
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="30"):
            result = vault_remember.is_quiet("skill")
        assert result is True
        assert capsys.readouterr().out.strip() == "quiet"

    def test_old_log_outside_window_is_quiet(self, tmp_path, capsys):
        """#1210: An active iteration file older than the interval is quiet."""
        iter_dir = tmp_path / "skill" / "iterations"
        self._make_iter_file(iter_dir, 1, type_val="active", age_minutes=60)
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="30"):
            result = vault_remember.is_quiet("skill")
        assert result is True

    def test_most_recent_file_wins(self, tmp_path, capsys):
        """#1210: When multiple iter files exist, the most recent mtime wins."""
        iter_dir = tmp_path / "skill" / "iterations"
        # Older file is quiet, newer file is active
        self._make_iter_file(iter_dir, 1, type_val="quiet", age_minutes=5)
        self._make_iter_file(iter_dir, 2, type_val="active", age_minutes=0)
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value="30"):
            result = vault_remember.is_quiet("skill")
        assert result is False

    def test_default_interval_when_config_missing(self, tmp_path, capsys):
        """#1210: Falls back to 30-minute interval when config unavailable."""
        iter_dir = tmp_path / "skill" / "iterations"
        self._make_iter_file(iter_dir, 1, type_val="active", age_minutes=0)
        with patch.object(vault_remember, "SQUIDSQUAD_DIR", tmp_path), \
             patch.object(vault_remember, "get_field", return_value=None):
            result = vault_remember.is_quiet("skill")
        # Default interval is 30 min; file is fresh, so non-quiet
        assert result is False
