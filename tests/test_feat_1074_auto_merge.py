"""Tests for #1074 — Auto-merge PRs after QA passes.

Verifies that pr_merge() in git_ops.py calls the correct merge strategy,
handles already-merged PRs, closed PRs, merge conflicts, and successful merges.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import git_ops


def _mock_result(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


class TestPrMergeSquashStrategy:
    """#1074: pr_merge uses squash strategy by default."""

    @patch("git_ops._run_list")
    def test_merge_squash_default(self, mock_run_list):
        """#1074: pr_merge defaults to squash strategy and passes --delete-branch."""
        # First call: gh pr view (state check)
        state_json = json.dumps({"state": "OPEN"})
        # Second call: gh pr merge (success)
        # Third call: gh pr view (branch name extraction)
        branch_json = json.dumps({"headRefName": "squidsquad/skill/42"})
        mock_run_list.side_effect = [
            _mock_result(stdout=state_json),   # state check
            _mock_result(),                     # merge
            _mock_result(stdout=branch_json),   # branch name
        ]
        success, msg = git_ops.pr_merge(42)
        assert success is True
        assert msg == "merged"
        # Verify merge command includes --squash and --delete-branch
        merge_call = mock_run_list.call_args_list[1]
        merge_cmd = merge_call[0][0]
        assert "--squash" in merge_cmd
        assert "--delete-branch" in merge_cmd
        assert "42" in merge_cmd

    @patch("git_ops._run_list")
    def test_merge_rebase_strategy(self, mock_run_list):
        """#1074: pr_merge respects explicit rebase strategy."""
        state_json = json.dumps({"state": "OPEN"})
        branch_json = json.dumps({"headRefName": "squidsquad/skill/99"})
        mock_run_list.side_effect = [
            _mock_result(stdout=state_json),
            _mock_result(),
            _mock_result(stdout=branch_json),
        ]
        success, msg = git_ops.pr_merge(99, strategy="rebase")
        assert success is True
        merge_call = mock_run_list.call_args_list[1]
        merge_cmd = merge_call[0][0]
        assert "--rebase" in merge_cmd


class TestPrMergeAlreadyMerged:
    """#1074: pr_merge handles already-merged PRs gracefully."""

    @patch("git_ops._run_list")
    def test_already_merged_returns_success(self, mock_run_list):
        """#1074: If PR is already merged, return (True, 'already merged')."""
        state_json = json.dumps({"state": "MERGED"})
        mock_run_list.return_value = _mock_result(stdout=state_json)
        success, msg = git_ops.pr_merge(10)
        assert success is True
        assert msg == "already merged"
        # Should NOT attempt merge — only one call (state check)
        assert mock_run_list.call_count == 1


class TestPrMergeClosedPr:
    """#1074: pr_merge rejects closed-without-merge PRs."""

    @patch("git_ops._run_list")
    def test_closed_pr_returns_failure(self, mock_run_list):
        """#1074: If PR is closed without merge, return (False, 'PR closed without merge')."""
        state_json = json.dumps({"state": "CLOSED"})
        mock_run_list.return_value = _mock_result(stdout=state_json)
        success, msg = git_ops.pr_merge(15)
        assert success is False
        assert msg == "PR closed without merge"


class TestPrMergConflict:
    """#1074: pr_merge detects merge conflicts."""

    @patch("git_ops._run_list")
    def test_merge_conflict_detected(self, mock_run_list):
        """#1074: Merge conflict in stderr returns (False, 'merge conflict')."""
        state_json = json.dumps({"state": "OPEN"})
        mock_run_list.side_effect = [
            _mock_result(stdout=state_json),
            _mock_result(returncode=1, stderr="Pull request is not mergeable: merge conflict"),
        ]
        success, msg = git_ops.pr_merge(20)
        assert success is False
        assert msg == "merge conflict"


class TestPrMergeIssueExtraction:
    """#1074: pr_merge extracts linked issue number from branch name."""

    @patch("git_ops._run_list")
    def test_extracts_issue_from_squidsquad_branch(self, mock_run_list, capsys):
        """#1074: After merge, parses squidsquad/role/NUMBER branch to find issue."""
        state_json = json.dumps({"state": "OPEN"})
        branch_json = json.dumps({"headRefName": "squidsquad/skill/475"})
        mock_run_list.side_effect = [
            _mock_result(stdout=state_json),
            _mock_result(),
            _mock_result(stdout=branch_json),
        ]
        success, _ = git_ops.pr_merge(30)
        assert success is True
        captured = capsys.readouterr()
        assert "#475" in captured.out
