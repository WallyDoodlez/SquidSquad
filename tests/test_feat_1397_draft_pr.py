"""Tests for #1397 — PR draft workflow.

Verifies that pr_create() in git_ops.py creates PRs as drafts by default,
both via the gh CLI path and the forge adapter path.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

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


class TestPrCreateDraftFlag:
    """#1397: pr_create must always create PRs as drafts."""

    @patch("git_ops._run_list")
    def test_gh_cli_uses_draft_flag(self, mock_run_list):
        """#1397: gh pr create command includes --draft flag."""
        mock_run_list.return_value = _mock_result(stdout="https://github.com/org/repo/pull/1")
        git_ops.pr_create("Test PR", "Test body")
        cmd = mock_run_list.call_args[0][0]
        assert "--draft" in cmd

    @patch("git_ops._run_list")
    def test_gh_cli_passes_title_and_body(self, mock_run_list):
        """#1397: gh pr create passes correct title and body."""
        mock_run_list.return_value = _mock_result(stdout="https://github.com/org/repo/pull/5")
        git_ops.pr_create("My Feature", "Detailed description")
        cmd = mock_run_list.call_args[0][0]
        assert "My Feature" in cmd
        assert "Detailed description" in cmd

    @patch("git_ops._run_list")
    def test_returns_pr_url_on_success(self, mock_run_list):
        """#1397: pr_create returns the PR URL on success."""
        expected_url = "https://github.com/org/repo/pull/7"
        mock_run_list.return_value = _mock_result(stdout=expected_url)
        url = git_ops.pr_create("Title", "Body")
        assert url == expected_url

    @patch("git_ops._run_list")
    def test_returns_none_on_failure(self, mock_run_list):
        """#1397: pr_create returns None when gh pr create fails."""
        mock_run_list.return_value = _mock_result(returncode=1, stderr="error")
        url = git_ops.pr_create("Title", "Body")
        assert url is None


class TestPrCreateForgeAdapter:
    """#1397: pr_create uses draft=True when going through forge adapter."""

    @patch("git_ops._run_list")
    def test_forge_adapter_draft_flag(self, mock_run_list):
        """#1397: forge adapter path passes draft=True to create_pr."""
        mock_adapter = MagicMock()
        mock_adapter.create_pr.return_value = {"url": "https://forge.example.com/pr/1"}

        mock_config = {"provider": "gitea", "url": "https://forge.example.com"}

        mock_run_list.return_value = _mock_result(stdout="feature-branch")

        with patch.dict("sys.modules", {
            "forge_adapter": MagicMock(
                get_adapter=MagicMock(return_value=mock_adapter),
                _read_forge_config=MagicMock(return_value=mock_config),
            ),
        }):
            # Re-import to pick up the mocked module
            import importlib
            importlib.reload(git_ops)
            url = git_ops.pr_create("Forge PR", "Forge body")

        # Restore original module state
        importlib.reload(git_ops)

        mock_adapter.create_pr.assert_called_once()
        _, kwargs = mock_adapter.create_pr.call_args
        assert kwargs.get("draft") is True


class TestPrCreateDocstring:
    """#1397: pr_create documents the draft workflow."""

    def test_docstring_mentions_draft(self):
        """#1397: pr_create docstring explicitly states PRs start as drafts."""
        assert "draft" in git_ops.pr_create.__doc__.lower()
