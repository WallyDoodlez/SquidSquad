"""Tests for #3296 — task-begin/task-end in git_ops.py.

Verifies task-level branch boundary commands: branch checkout, missing branch
error, and task-end return to working branch. Branch+PR is the only mode
(#9478) — the disabled no-op tests have been removed.
"""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops


def _mock_config_enabled(field):
    """No-op config mock — branch+PR is the only mode (#9478)."""
    return None


class TestTaskBegin:
    """Tests for git_ops.task_begin()."""

    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._run_list")
    def test_checks_out_existing_local_branch(self, mock_run_list, mock_checkout):
        """TC-1: task-begin checks out existing local branch."""
        def side_effect(cmd, check=False):
            result = MagicMock()
            if "rev-parse" in cmd and "refs/heads/" in str(cmd):
                result.returncode = 0  # local branch exists
            else:
                result.returncode = 1
            return result

        mock_run_list.side_effect = side_effect

        with patch("config.get_field", side_effect=_mock_config_enabled):
            git_ops.task_begin("skill", "9999")

        mock_checkout.assert_called_once_with("squidsquad/task/9999")

    @patch("git_ops._run_list")
    def test_checks_out_from_remote(self, mock_run_list):
        """TC-1b: task-begin fetches from remote when no local branch."""
        calls = []

        def side_effect(cmd, check=False):
            calls.append(cmd)
            result = MagicMock()
            if "rev-parse" in cmd and "refs/heads/" in str(cmd):
                result.returncode = 1  # no local
            elif "rev-parse" in cmd and "refs/remotes/" in str(cmd):
                result.returncode = 0  # remote exists
            elif "checkout" in cmd and "-b" in cmd:
                result.returncode = 0  # checkout succeeds
            else:
                result.returncode = 1
            return result

        mock_run_list.side_effect = side_effect

        with patch("config.get_field", side_effect=_mock_config_enabled):
            git_ops.task_begin("skill", "9999")

        checkout_calls = [c for c in calls if "checkout" in c and "-b" in c]
        assert len(checkout_calls) == 1
        assert "origin/squidsquad/task/9999" in checkout_calls[0]

    @patch("git_ops._run_list")
    def test_missing_branch_exits_nonzero(self, mock_run_list):
        """TC-3: task-begin exits non-zero when branch doesn't exist."""
        def side_effect(cmd, check=False):
            result = MagicMock()
            result.returncode = 1  # nothing exists
            return result

        mock_run_list.side_effect = side_effect

        with patch("config.get_field", side_effect=_mock_config_enabled):
            with pytest.raises(SystemExit) as exc_info:
                git_ops.task_begin("skill", "8888")
        assert exc_info.value.code == 1

    def test_derives_correct_branch_name(self):
        """task-begin derives squidsquad/<role>/<number> branch name."""
        checked = []

        def mock_run_list(cmd, check=False):
            if "rev-parse" in cmd:
                checked.append(str(cmd))
            result = MagicMock()
            result.returncode = 1
            return result

        with patch("git_ops._run_list", side_effect=mock_run_list), \
             patch("config.get_field", side_effect=_mock_config_enabled):
            with pytest.raises(SystemExit):
                git_ops.task_begin("qa", "3100")

        assert any("squidsquad/task/3100" in c for c in checked)


class TestTaskEnd:
    """Tests for git_ops.task_end()."""

    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._run")
    @patch("git_ops._get_working_branch", return_value="main")
    def test_returns_to_working_branch(self, mock_branch, mock_run, mock_checkout):
        """TC-2: task-end returns to working branch."""
        mock_run.return_value = MagicMock(stdout="", returncode=0)

        with patch("config.get_field", side_effect=_mock_config_enabled):
            git_ops.task_end("skill", "9999")

        mock_checkout.assert_called_with("main")

    @patch("git_ops._safe_checkout", return_value=True)
    @patch("git_ops._run")
    @patch("git_ops._get_working_branch", return_value="main")
    def test_warns_on_uncommitted_changes(self, mock_branch, mock_run, mock_checkout, capsys):
        """task-end warns when uncommitted changes remain."""
        mock_run.return_value = MagicMock(stdout="M references/scripts/foo.py\n", returncode=0)

        with patch("config.get_field", side_effect=_mock_config_enabled):
            git_ops.task_end("skill", "9999")

        captured = capsys.readouterr()
        assert "uncommitted" in captured.err.lower() or "WARNING" in captured.err


class TestTaskBoundaryTemplates:
    """Verify task-begin/task-end references in sub-skill templates."""

    def test_qa_verification_uses_task_begin(self):
        """TC-6: verifier verification.md uses task-begin/task-end."""
        path = SCRIPTS.parent / "sub-skills" / "roles" / "verifier" / "verification.md"
        content = path.read_text(encoding="utf-8")
        assert "task-begin" in content
        assert "task-end" in content
        assert "branch-switch" not in content, "Old branch-switch calls should be removed"

    def test_skill_triage_uses_task_begin(self):
        """TC-8: worker triage uses task-begin/task-end."""
        path = SCRIPTS.parent / "sub-skills" / "roles" / "worker" / "triage-issues.md"
        content = path.read_text(encoding="utf-8")
        assert "task-begin" in content
        assert "task-end" in content

    def test_skill_implement_uses_task_begin(self):
        """TC-8b: worker implement uses task-begin/task-end."""
        path = SCRIPTS.parent / "sub-skills" / "roles" / "worker" / "implement-tasks.md"
        content = path.read_text(encoding="utf-8")
        assert "task-begin" in content
        assert "task-end" in content

    def test_dm_delivery_uses_task_begin(self):
        """TC-9: DM delivery uses task-begin/task-end."""
        path = SCRIPTS.parent / "sub-skills" / "roles" / "dm" / "delivery-packaging.md"
        content = path.read_text(encoding="utf-8")
        assert "task-begin" in content
        assert "task-end" in content


class TestCyclePreCleanup:
    """Verify cycle_pre.py hacks removed (#3296)."""

    def test_no_qa_first_item_branch_hack(self):
        """TC-7: cycle_pre.py no longer has QA first-item branch checkout."""
        path = SCRIPTS / "cycle_pre.py"
        content = path.read_text(encoding="utf-8")
        # The old code had: branch_workflow and first_item and first_item.get("branch")
        assert 'first_item.get("branch")' not in content, \
            "QA first-item branch checkout hack should be removed"

    def test_no_setup_skill_branch_call(self):
        """TC-8c: cycle_pre.py no longer calls _setup_skill_branch."""
        path = SCRIPTS / "cycle_pre.py"
        content = path.read_text(encoding="utf-8")
        assert "_setup_skill_branch(working_state" not in content, \
            "_setup_skill_branch call should be removed"
