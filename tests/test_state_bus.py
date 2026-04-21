"""Tests for references/scripts/state_bus.py — state branch worktree management."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import state_bus


class TestReadBranchConfig:
    def test_reads_from_config(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text(
            "## Git Branches\n\n"
            "- **Working Branch**: dev\n"
            "- **State Branch**: agent-state\n"
        )
        with patch.object(state_bus, "CONFIG_MD", config):
            working, state = state_bus._read_branch_config()
        assert working == "dev"
        assert state == "agent-state"

    def test_defaults_when_missing(self, tmp_path):
        with patch.object(state_bus, "CONFIG_MD", tmp_path / "missing"):
            working, state = state_bus._read_branch_config()
        assert working == "stag"
        assert state == "squid-squad"

    def test_defaults_when_no_section(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("## Project\n\n- **Name**: test\n")
        with patch.object(state_bus, "CONFIG_MD", config):
            working, state = state_bus._read_branch_config()
        assert working == "stag"
        assert state == "squid-squad"


class TestWorktreeExists:
    def test_true_when_git_present(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            assert state_bus._worktree_exists() is True

    def test_false_when_missing(self, tmp_path):
        with patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"):
            assert state_bus._worktree_exists() is False

    def test_false_when_no_git(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            assert state_bus._worktree_exists() is False


class TestReadFile:
    def test_reads_existing_file(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        (wt / "test.txt").write_text("hello")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            content = state_bus.read_file("test.txt")
        assert content == "hello"

    def test_returns_none_for_missing(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            assert state_bus.read_file("missing.txt") is None

    def test_returns_none_when_no_worktree(self, tmp_path):
        with patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"):
            assert state_bus.read_file("test.txt") is None


class TestWriteFile:
    def test_writes_file(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            result = state_bus.write_file("test.txt", "content")
        assert result is True
        assert (wt / "test.txt").read_text() == "content"

    def test_creates_subdirs(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt):
            result = state_bus.write_file("sub/dir/file.txt", "nested")
        assert result is True
        assert (wt / "sub" / "dir" / "file.txt").read_text() == "nested"

    def test_fails_when_no_worktree(self, tmp_path):
        with patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"):
            assert state_bus.write_file("test.txt", "x") is False


class TestStatus:
    def test_outputs_json(self, tmp_path, capsys):
        config = tmp_path / "config.md"
        config.write_text(
            "## Git Branches\n\n"
            "- **Working Branch**: dev\n"
            "- **State Branch**: my-state\n"
        )
        with patch.object(state_bus, "CONFIG_MD", config), \
             patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"):
            code = state_bus.status()
        assert code == 0
        output = json.loads(capsys.readouterr().out)
        assert output["state_branch"] == "my-state"
        assert output["worktree_exists"] is False


class TestCLI:
    def test_help(self):
        sys.argv = ["state_bus.py", "--help"]
        code = state_bus.main()
        assert code == 0

    def test_unknown_command(self):
        sys.argv = ["state_bus.py", "badcmd"]
        code = state_bus.main()
        assert code == 2
