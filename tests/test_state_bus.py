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


class TestInitBranchRecovery:
    """Regression tests for #3290 — init() must restore original branch on failure."""

    @patch.object(state_bus, "_state_branch_exists", return_value=False)
    @patch.object(state_bus, "_worktree_exists", return_value=True)
    def test_captures_original_branch(self, mock_wt, mock_exists):
        """#3290: init() captures current branch before orphan checkout."""
        calls = []

        def fake_run(cmd, check=True, cwd=None):
            calls.append(cmd)
            result = MagicMock()
            result.returncode = 0
            result.stdout = "main\n"
            if "checkout" in cmd and "--orphan" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return result

        import subprocess
        with patch.object(state_bus, "_run", side_effect=fake_run), \
             patch.object(state_bus, "REPO_ROOT", Path("/tmp/fake")):
            try:
                state_bus.init()
            except Exception:
                pass

        # First call should be rev-parse to capture current branch
        assert any("rev-parse" in str(c) for c in calls), \
            "init() must capture current branch via rev-parse before orphan checkout"

    @patch.object(state_bus, "_state_branch_exists", return_value=False)
    @patch.object(state_bus, "_worktree_exists", return_value=True)
    def test_restores_branch_on_failure(self, mock_wt, mock_exists):
        """#3290: init() restores original branch even when orphan checkout fails."""
        checkout_targets = []

        def fake_run(cmd, check=True, cwd=None):
            result = MagicMock()
            result.returncode = 0
            result.stdout = "my-feature\n"
            if "checkout" in cmd and "--orphan" not in cmd and "rev-parse" not in str(cmd):
                checkout_targets.append(cmd[-1] if cmd else None)
            if "commit" in cmd:
                raise subprocess.CalledProcessError(1, cmd)
            return result

        import subprocess
        with patch.object(state_bus, "_run", side_effect=fake_run), \
             patch.object(state_bus, "REPO_ROOT", Path("/tmp/fake")):
            try:
                state_bus.init()
            except Exception:
                pass

        # Should attempt to checkout the original branch in finally
        assert "my-feature" in checkout_targets, \
            "init() must restore original branch (my-feature) in finally block"

    def test_no_hardcoded_main_fallback(self):
        """#3290: init() should not have a hardcoded 'main' fallback."""
        import inspect
        source = inspect.getsource(state_bus.init)
        # The old code had: _run(["git", "checkout", "main"], check=False)
        # The new code uses _read_branch_config() for the fallback
        assert '"main"' not in source or "_read_branch_config" in source, \
            "init() should use _read_branch_config() for fallback, not hardcoded 'main'"


class TestIsStateFile:
    """#3664: is_state_file classifies paths correctly."""

    def test_iterations_is_state(self):
        assert state_bus.is_state_file("skill/iterations/iter-1.md") is True

    def test_working_state_is_state(self):
        assert state_bus.is_state_file("pm/working-state.md") is True

    def test_scan_history_is_state(self):
        assert state_bus.is_state_file("skill/scan-history.md") is True

    def test_diagnostics_is_state(self):
        assert state_bus.is_state_file("diagnostics/diagnostic.jsonl") is True

    def test_config_is_not_state(self):
        assert state_bus.is_state_file("config.md") is False

    def test_claude_md_is_not_state(self):
        assert state_bus.is_state_file("skill/CLAUDE.md") is False

    def test_vault_is_not_state(self):
        assert state_bus.is_state_file("vault/galaxy/decision-foo.md") is False

    def test_planning_is_not_state(self):
        assert state_bus.is_state_file("pm/planning/FEAT-PM-123-CONTEXT.md") is False

    def test_iterations_dir_no_trailing_slash(self):
        """#3664 QA fix: bare dir path without trailing slash must match."""
        assert state_bus.is_state_file("skill/iterations") is True

    def test_diagnostics_dir_no_trailing_slash(self):
        """#3664 QA fix: bare dir path without trailing slash must match."""
        assert state_bus.is_state_file("diagnostics") is True


class TestStatePath:
    """#3664: state_path resolves to worktree for state files, .squidsquad/ for others."""

    def test_state_file_with_worktree(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt), \
             patch.object(state_bus, "REPO_ROOT", tmp_path):
            result = state_bus.state_path("skill/iterations/iter-1.md")
        assert str(wt) in str(result)

    def test_non_state_file_stays_on_main(self, tmp_path):
        wt = tmp_path / "state"
        wt.mkdir()
        (wt / ".git").write_text("gitdir: ...")
        with patch.object(state_bus, "STATE_WORKTREE", wt), \
             patch.object(state_bus, "REPO_ROOT", tmp_path):
            result = state_bus.state_path("config.md")
        assert ".squidsquad" in str(result)
        assert str(wt) not in str(result)

    def test_state_file_without_worktree_falls_back(self, tmp_path):
        with patch.object(state_bus, "STATE_WORKTREE", tmp_path / "nope"), \
             patch.object(state_bus, "REPO_ROOT", tmp_path):
            result = state_bus.state_path("skill/iterations/iter-1.md")
        assert ".squidsquad" in str(result)


class TestCLI:
    def test_help(self):
        sys.argv = ["state_bus.py", "--help"]
        code = state_bus.main()
        assert code == 0

    def test_unknown_command(self):
        sys.argv = ["state_bus.py", "badcmd"]
        code = state_bus.main()
        assert code == 2


# ---------------------------------------------------------------------------
# #7589: commit_and_push must detect failed git commit
# ---------------------------------------------------------------------------

class TestCommitAndPushFailedCommit:
    """#7589: commit_and_push returns False when git commit fails."""

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_returns_false_on_commit_failure(self, mock_run, mock_config, mock_wt):
        """Failed git commit should return False, not proceed to push."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),     # git add -A
            MagicMock(stdout=" M file.md\n", returncode=0),  # git status --porcelain
            MagicMock(stdout="", stderr="error: hook rejected", returncode=1),  # git commit FAILS
        ]
        result = state_bus.commit_and_push("test msg", role="skill")
        assert result is False
        # Push should NOT have been called (only 3 _run calls, not 4+)
        assert mock_run.call_count == 3

    @patch("state_bus._worktree_exists", return_value=True)
    @patch("state_bus._read_branch_config", return_value=("main", "squid-squad"))
    @patch("state_bus._run")
    def test_returns_true_on_commit_success(self, mock_run, mock_config, mock_wt):
        """Successful commit + push returns True."""
        mock_run.side_effect = [
            MagicMock(stdout="", returncode=0),     # git add -A
            MagicMock(stdout=" M file.md\n", returncode=0),  # git status --porcelain
            MagicMock(stdout="", stderr="", returncode=0),  # git commit succeeds
            MagicMock(stdout="", returncode=0),     # git push succeeds
        ]
        result = state_bus.commit_and_push("test msg", role="skill")
        assert result is True
