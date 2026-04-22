"""Tests for references/scripts/git_ops.py — mocked subprocess, no real git."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Allow import from references/scripts/
SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


# ---------------------------------------------------------------------------
# pull()
# ---------------------------------------------------------------------------

class TestPull:
    @patch("git_ops._run")
    def test_clean_pull(self, mock_run):
        mock_run.return_value = _mock_result()
        assert git_ops.pull() is True
        mock_run.assert_called_once()

    @patch("git_ops._run")
    def test_pull_stash_pop(self, mock_run):
        """Dirty tree → stash, pull, pop succeeds."""
        mock_run.side_effect = [
            _mock_result(returncode=1),  # pull fails
            _mock_result(),              # stash
            _mock_result(),              # pull --rebase
            _mock_result(),              # stash pop
        ]
        assert git_ops.pull() is True
        assert mock_run.call_count == 4

    @patch("git_ops._run")
    def test_pull_stash_pop_conflict(self, mock_run):
        """Stash pop fails → warning printed, still returns True."""
        mock_run.side_effect = [
            _mock_result(returncode=1),  # pull fails
            _mock_result(),              # stash
            _mock_result(),              # pull --rebase
            _mock_result(returncode=1),  # stash pop fails
        ]
        assert git_ops.pull() is True


# ---------------------------------------------------------------------------
# add_all()
# ---------------------------------------------------------------------------

class TestAddAll:
    @patch("git_ops._run")
    def test_stages_all(self, mock_run):
        mock_run.return_value = _mock_result()
        git_ops.add_all()
        mock_run.assert_called_once_with("git add -A")


# ---------------------------------------------------------------------------
# commit()
# ---------------------------------------------------------------------------

class TestCommit:
    @patch("subprocess.run")
    def test_successful_commit(self, mock_run):
        mock_run.return_value = _mock_result(stdout="[main abc1234] skill: msg")
        assert git_ops.commit("skill", "test message") is True
        args = mock_run.call_args
        assert args[0][0][0] == "git"
        assert args[0][0][1] == "commit"
        # Check message contains role prefix
        msg = args[0][0][3]
        assert msg.startswith("skill: test message")
        assert "Co-Authored-By:" in msg

    @patch("subprocess.run")
    def test_nothing_to_commit(self, mock_run):
        mock_run.return_value = _mock_result(
            stdout="nothing to commit, working tree clean",
            returncode=1,
        )
        assert git_ops.commit("skill", "msg") is False

    @patch("subprocess.run")
    def test_commit_error(self, mock_run):
        mock_run.return_value = _mock_result(
            stderr="fatal: some error", returncode=1,
        )
        assert git_ops.commit("skill", "msg") is False


# ---------------------------------------------------------------------------
# push()
# ---------------------------------------------------------------------------

class TestPush:
    @patch("git_ops._run")
    def test_successful_push(self, mock_run):
        mock_run.return_value = _mock_result()
        assert git_ops.push() is True

    @patch("git_ops._run")
    def test_push_failure(self, mock_run):
        mock_run.return_value = _mock_result(stderr="rejected", returncode=1)
        assert git_ops.push() is False


# ---------------------------------------------------------------------------
# commit_push()
# ---------------------------------------------------------------------------

class TestCommitPush:
    @patch("git_ops.push", return_value=True)
    @patch("git_ops.commit", return_value=True)
    @patch("git_ops.add_all")
    def test_full_workflow(self, mock_add, mock_commit, mock_push):
        assert git_ops.commit_push("skill", "msg") is True
        mock_add.assert_called_once()
        mock_commit.assert_called_once_with("skill", "msg")
        mock_push.assert_called_once()

    @patch("git_ops.push")
    @patch("git_ops.commit", return_value=False)
    @patch("git_ops.add_all")
    def test_nothing_to_commit_skips_push(self, mock_add, mock_commit, mock_push):
        assert git_ops.commit_push("skill", "msg") is False
        mock_push.assert_not_called()


# ---------------------------------------------------------------------------
# has_changes()
# ---------------------------------------------------------------------------

class TestHasChanges:
    @patch("git_ops._run")
    def test_dirty_tree(self, mock_run):
        mock_run.return_value = _mock_result(stdout=" M some/file.py\n")
        assert git_ops.has_changes() is True

    @patch("git_ops._run")
    def test_clean_tree(self, mock_run):
        mock_run.return_value = _mock_result(stdout="")
        assert git_ops.has_changes() is False


# ---------------------------------------------------------------------------
# last_hash()
# ---------------------------------------------------------------------------

class TestLastHash:
    @patch("git_ops._run")
    def test_returns_hash(self, mock_run):
        mock_run.return_value = _mock_result(stdout="abc1234\n")
        assert git_ops.last_hash() == "abc1234"


# ---------------------------------------------------------------------------
# branch_create() / branch_switch()
# ---------------------------------------------------------------------------

class TestBranching:
    @patch("git_ops._run_list")
    def test_branch_create(self, mock_run):
        mock_run.return_value = _mock_result()
        git_ops.branch_create("feature/test")
        mock_run.assert_called_once_with(["git", "checkout", "-b", "feature/test"])

    @patch("git_ops._run_list")
    def test_branch_switch(self, mock_run):
        mock_run.return_value = _mock_result()
        git_ops.branch_switch("main")
        mock_run.assert_called_once_with(["git", "checkout", "main"])

    @patch("git_ops._run_list")
    def test_branch_create_failure(self, mock_run):
        """branch_create raises on git failure (check=True default)."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, "git")
        with pytest.raises(CalledProcessError):
            git_ops.branch_create("bad/branch")

    @patch("git_ops._run_list")
    def test_branch_switch_failure(self, mock_run):
        """branch_switch raises on git failure (check=True default)."""
        from subprocess import CalledProcessError
        mock_run.side_effect = CalledProcessError(1, "git")
        with pytest.raises(CalledProcessError):
            git_ops.branch_switch("nonexistent")


# ---------------------------------------------------------------------------
# pr_create()
# ---------------------------------------------------------------------------

class TestPrCreate:
    @patch("git_ops._run_list")
    def test_successful_pr(self, mock_run):
        mock_run.return_value = _mock_result(
            stdout="https://github.com/org/repo/pull/42\n"
        )
        url = git_ops.pr_create("title", "body")
        assert url == "https://github.com/org/repo/pull/42"

    @patch("git_ops._run_list")
    def test_pr_failure(self, mock_run):
        mock_run.return_value = _mock_result(
            stderr="error", returncode=1,
        )
        assert git_ops.pr_create("title", "body") is None


# ---------------------------------------------------------------------------
# _get_alias()
# ---------------------------------------------------------------------------

class TestPrMerge:
    @patch("git_ops._run_list")
    def test_successful_squash_merge(self, mock_run):
        # First call: check state → OPEN, second: merge → success, third: branch name lookup
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stdout=""),
            _mock_result(stdout='{"headRefName": "squidsquad/skill/42"}'),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is True
        assert msg == "merged"
        # Verify squash merge was called
        merge_call = mock_run.call_args_list[1]
        assert "--squash" in merge_call[0][0]
        assert "--delete-branch" in merge_call[0][0]

    @patch("git_ops._run_list")
    def test_already_merged(self, mock_run):
        mock_run.return_value = _mock_result(stdout='{"state": "MERGED"}')
        success, msg = git_ops.pr_merge(42)
        assert success is True
        assert msg == "already merged"
        # Should only call once (state check), no merge attempt
        assert mock_run.call_count == 1

    @patch("git_ops._run_list")
    def test_closed_without_merge(self, mock_run):
        mock_run.return_value = _mock_result(stdout='{"state": "CLOSED"}')
        success, msg = git_ops.pr_merge(42)
        assert success is False
        assert "closed" in msg.lower()

    @patch("git_ops._run_list")
    def test_merge_conflict(self, mock_run):
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stderr="not mergeable: merge conflict", returncode=1),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is False
        assert "merge conflict" in msg

    @patch("git_ops._run_list")
    def test_unexpected_failure(self, mock_run):
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stderr="permission denied", returncode=1),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is False
        assert "merge failed" in msg

    @patch("git_ops._run_list")
    def test_custom_strategy(self, mock_run):
        mock_run.side_effect = [
            _mock_result(stdout='{"state": "OPEN"}'),
            _mock_result(stdout=""),
            _mock_result(stdout='{"headRefName": "feature"}'),
        ]
        git_ops.pr_merge(42, strategy="rebase")
        merge_call = mock_run.call_args_list[1]
        assert "--rebase" in merge_call[0][0]

    @patch("git_ops._run_list")
    def test_state_check_fails_still_attempts_merge(self, mock_run):
        # State check fails (non-zero), merge succeeds, branch lookup
        mock_run.side_effect = [
            _mock_result(returncode=1, stderr="not found"),
            _mock_result(stdout=""),
            _mock_result(stdout='{"headRefName": "feature"}'),
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is True
        assert msg == "merged"


    @patch("git_ops._run_list")
    def test_forge_adapter_routing(self, mock_run):
        """When forge provider is non-GitHub, pr_merge uses the adapter."""
        mock_adapter = MagicMock()
        mock_adapter.view_pr.return_value = {"state": "OPEN"}
        mock_adapter.merge_pr.return_value = (True, "merged")

        mock_config = {"provider": "forgejo", "endpoint": "http://localhost:3000"}

        with patch.dict("sys.modules", {
            "forge_adapter": MagicMock(
                get_adapter=MagicMock(return_value=mock_adapter),
                _read_forge_config=MagicMock(return_value=mock_config),
            ),
        }):
            # Need to re-import to pick up the mock
            success, msg = git_ops.pr_merge(42)

        assert success is True
        assert msg == "merged"
        mock_adapter.view_pr.assert_called_once_with(42)
        mock_adapter.merge_pr.assert_called_once_with(42, "squash")
        # gh CLI should NOT be called when adapter handles it
        mock_run.assert_not_called()


class TestGetAlias:
    def test_fallback_to_role(self):
        """When config module unavailable, returns role name."""
        # _get_alias catches all exceptions and falls back to role
        with patch.dict("sys.modules", {"config": None}):
            result = git_ops._get_alias("skill")
            assert result == "skill"


# ---------------------------------------------------------------------------
# _parse_args()
# ---------------------------------------------------------------------------

class TestParseArgs:
    def test_help_exits(self):
        with patch.object(sys, "argv", ["git_ops.py", "--help"]):
            with pytest.raises(SystemExit):
                git_ops._parse_args()

    def test_no_args_exits(self):
        with patch.object(sys, "argv", ["git_ops.py"]):
            with pytest.raises(SystemExit):
                git_ops._parse_args()

    def test_parses_command(self):
        with patch.object(sys, "argv", ["git_ops.py", "pull"]):
            cmd, rest = git_ops._parse_args()
            assert cmd == "pull"
            assert rest == []

    def test_parses_command_with_args(self):
        with patch.object(sys, "argv", ["git_ops.py", "commit", "skill", "msg"]):
            cmd, rest = git_ops._parse_args()
            assert cmd == "commit"
            assert rest == ["skill", "msg"]


# ---------------------------------------------------------------------------
# _is_state_file()
# ---------------------------------------------------------------------------

class TestIsStateFile:
    def test_squidsquad_files(self):
        assert git_ops._is_state_file(".squidsquad/skill/working-state.md") is True
        assert git_ops._is_state_file(".squidsquad/pm/planning/CONTEXT.md") is True

    def test_claude_files(self):
        assert git_ops._is_state_file(".claude/scheduled_tasks.lock") is True
        assert git_ops._is_state_file(".claude/settings.local.json") is True

    def test_code_files(self):
        assert git_ops._is_state_file("references/scripts/git_ops.py") is False
        assert git_ops._is_state_file("tests/test_git_ops.py") is False
        assert git_ops._is_state_file("src/main.py") is False


# ---------------------------------------------------------------------------
# commit_code()
# ---------------------------------------------------------------------------

class TestCommitCode:
    @patch("git_ops._run_list")
    @patch("git_ops._run")
    @patch("subprocess.run")
    def test_splits_code_from_state(self, mock_subproc, mock_run, mock_run_list):
        """commit_code only stages non-.squidsquad/ files."""
        # git status --porcelain: XY<space>path (3 chars prefix)
        mock_run.side_effect = [
            _mock_result(stdout=" M references/scripts/git_ops.py\n M .squidsquad/skill/working-state.md\n"),
            _mock_result(stdout="squidsquad/skill/375\n"),  # current branch
            _mock_result(stdout="main\n"),  # branch --show-current after switch back
        ]
        # rev-parse --verify (branch exists)
        mock_run_list.side_effect = [
            _mock_result(returncode=0),  # branch exists
            _mock_result(),  # git checkout
            _mock_result(),  # git add (code file)
            _mock_result(),  # git push -u
            _mock_result(),  # git checkout main
        ]
        # git commit
        mock_subproc.return_value = _mock_result(stdout="1 file changed")

        result = git_ops.commit_code("skill", "squidsquad/skill/375", "test")
        assert result is True

        # Verify only the code file was staged (not .squidsquad/)
        add_calls = [c for c in mock_run_list.call_args_list if c[0][0][0:2] == ["git", "add"]]
        assert len(add_calls) == 1
        assert add_calls[0][0][0][2] == "references/scripts/git_ops.py"

    @patch("git_ops._run")
    def test_no_code_changes_returns_false(self, mock_run):
        """commit_code returns False when only .squidsquad/ files changed."""
        mock_run.return_value = _mock_result(stdout=" M .squidsquad/skill/working-state.md\n")
        assert git_ops.commit_code("skill", "squidsquad/skill/375", "test") is False

    @patch("git_ops._run")
    def test_excludes_claude_state_files(self, mock_run):
        """commit_code excludes .claude/ state files from feature branches."""
        mock_run.return_value = _mock_result(
            stdout=" M .claude/scheduled_tasks.lock\n M .squidsquad/skill/working-state.md\n"
        )
        assert git_ops.commit_code("skill", "squidsquad/skill/375", "test") is False

    @patch("git_ops._run")
    def test_no_changes_returns_false(self, mock_run):
        mock_run.return_value = _mock_result(stdout="")
        assert git_ops.commit_code("skill", "squidsquad/skill/375", "test") is False


# ---------------------------------------------------------------------------
# commit_state()
# ---------------------------------------------------------------------------

class TestCommitState:
    @patch("git_ops._run")
    @patch("git_ops._run_list")
    @patch("subprocess.run")
    def test_only_stages_squidsquad_files(self, mock_subproc, mock_run_list, mock_run):
        """commit_state only stages .squidsquad/ files on main."""
        mock_run.side_effect = [
            _mock_result(stdout=" M references/scripts/git_ops.py\n M .squidsquad/skill/working-state.md\n"),
            _mock_result(stdout="main\n"),  # current branch
            _mock_result(),  # push
        ]
        mock_run_list.return_value = _mock_result()  # git add
        mock_subproc.return_value = _mock_result(stdout="1 file changed")

        result = git_ops.commit_state("skill", "state update")
        assert result is True

        add_calls = [c for c in mock_run_list.call_args_list if c[0][0][0:2] == ["git", "add"]]
        assert len(add_calls) == 1
        assert add_calls[0][0][0][2] == ".squidsquad/skill/working-state.md"

    @patch("git_ops._run")
    def test_errors_if_not_on_main(self, mock_run):
        """commit_state returns False if not on main branch."""
        mock_run.side_effect = [
            _mock_result(stdout=" M .squidsquad/skill/working-state.md\n"),
            _mock_result(stdout="squidsquad/skill/375\n"),  # not on main
        ]
        assert git_ops.commit_state("skill", "state update") is False

    @patch("git_ops._run")
    def test_no_state_changes_returns_false(self, mock_run):
        mock_run.return_value = _mock_result(stdout=" M references/scripts/git_ops.py\n")
        assert git_ops.commit_state("skill", "state update") is False


# ---------------------------------------------------------------------------
# branch_exists() / branch_delete() / current_branch()
# ---------------------------------------------------------------------------

class TestBranchUtilities:
    @patch("git_ops._run_list")
    def test_branch_exists_local(self, mock_run):
        mock_run.return_value = _mock_result(returncode=0)
        assert git_ops.branch_exists("squidsquad/skill/375") is True

    @patch("git_ops._run_list")
    def test_branch_not_exists(self, mock_run):
        mock_run.return_value = _mock_result(returncode=1)
        assert git_ops.branch_exists("nonexistent") is False

    @patch("git_ops._run_list")
    def test_branch_delete_success(self, mock_run):
        mock_run.return_value = _mock_result()
        assert git_ops.branch_delete("squidsquad/skill/375") is True

    @patch("git_ops._run")
    def test_current_branch(self, mock_run):
        mock_run.return_value = _mock_result(stdout="main\n")
        assert git_ops.current_branch() == "main"


# ---------------------------------------------------------------------------
# _safe_checkout()
# ---------------------------------------------------------------------------

class TestSafeCheckout:
    """#2064: _safe_checkout handles unstaged changes blocking checkout."""

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_already_on_target(self, mock_run, mock_run_list):
        mock_run.return_value = _mock_result(stdout="main\n")
        assert git_ops._safe_checkout("main") is True
        mock_run_list.assert_not_called()

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_direct_checkout_succeeds(self, mock_run, mock_run_list):
        mock_run.return_value = _mock_result(stdout="squidsquad/skill/42\n")
        mock_run_list.return_value = _mock_result()
        assert git_ops._safe_checkout("main") is True

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_stash_fallback_on_dirty_tree(self, mock_run, mock_run_list):
        """Direct checkout fails, stash+checkout+pop succeeds."""
        mock_run.side_effect = [
            _mock_result(stdout="squidsquad/skill/42\n"),
            _mock_result(),  # git stash -q
            _mock_result(),  # git stash pop -q
        ]
        mock_run_list.side_effect = [
            _mock_result(returncode=1, stderr="unstaged changes"),
            _mock_result(),  # second checkout succeeds
        ]
        assert git_ops._safe_checkout("main") is True
        assert mock_run_list.call_count == 2

    @patch("git_ops._run_list")
    @patch("git_ops._run")
    def test_returns_false_when_all_fails(self, mock_run, mock_run_list):
        mock_run.side_effect = [
            _mock_result(stdout="squidsquad/skill/42\n"),
            _mock_result(),  # stash
            _mock_result(),  # stash pop
        ]
        mock_run_list.side_effect = [
            _mock_result(returncode=1, stderr="error"),
            _mock_result(returncode=1, stderr="still error"),
        ]
        assert git_ops._safe_checkout("main") is False
