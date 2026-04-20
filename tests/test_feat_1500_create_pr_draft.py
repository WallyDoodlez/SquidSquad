"""Regression tests for #1500 — ForgejoAdapter.create_pr draft flag.

Verifies that ForgejoAdapter.create_pr correctly passes the draft flag
in the API payload, and that GitHubAdapter.create_pr appends --draft
only when draft=True.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import forge_adapter


def _make_forgejo_adapter():
    """Create a ForgejoAdapter with mocked token loading."""
    config = {
        "provider": "forgejo",
        "endpoint": "http://localhost:3000",
        "owner": "testowner",
        "repo": "testrepo",
    }
    with patch.object(forge_adapter.ForgejoAdapter, "_load_token", return_value="fake-token"):
        return forge_adapter.ForgejoAdapter(config)


def _make_github_adapter():
    """Create a GitHubAdapter."""
    config = {
        "provider": "github",
        "endpoint": "https://api.github.com",
        "owner": "testowner",
        "repo": "testrepo",
    }
    return forge_adapter.GitHubAdapter(config)


class TestForgejoCreatePrDraft:
    """#1500: ForgejoAdapter.create_pr must pass draft flag in payload."""

    def test_draft_true_in_payload(self):
        """#1500: draft=True should appear in the Forgejo API payload."""
        adapter = _make_forgejo_adapter()
        fake_response = {"number": 42, "html_url": "http://localhost:3000/pr/42"}
        with patch.object(adapter, "_api", return_value=fake_response) as mock_api:
            result = adapter.create_pr("Test PR", "body", "feature-branch", draft=True)
        mock_api.assert_called_once()
        call_args = mock_api.call_args
        payload = call_args[0][2]  # positional: method, path, data
        assert payload["draft"] is True
        assert result["number"] == 42

    def test_draft_false_in_payload(self):
        """#1500: draft=False should appear in the Forgejo API payload."""
        adapter = _make_forgejo_adapter()
        fake_response = {"number": 43, "html_url": "http://localhost:3000/pr/43"}
        with patch.object(adapter, "_api", return_value=fake_response) as mock_api:
            result = adapter.create_pr("Test PR", "body", "feature-branch", draft=False)
        payload = mock_api.call_args[0][2]
        assert payload["draft"] is False

    def test_draft_default_is_true(self):
        """#1500: draft parameter defaults to True."""
        adapter = _make_forgejo_adapter()
        fake_response = {"number": 44, "html_url": "http://localhost:3000/pr/44"}
        with patch.object(adapter, "_api", return_value=fake_response) as mock_api:
            adapter.create_pr("Test PR", "body", "feature-branch")
        payload = mock_api.call_args[0][2]
        assert payload["draft"] is True

    def test_base_branch_in_payload(self):
        """#1500: base and head branches should be in the payload."""
        adapter = _make_forgejo_adapter()
        fake_response = {"number": 45, "html_url": "http://localhost:3000/pr/45"}
        with patch.object(adapter, "_api", return_value=fake_response) as mock_api:
            adapter.create_pr("PR Title", "PR body", "my-branch", base="develop")
        payload = mock_api.call_args[0][2]
        assert payload["head"] == "my-branch"
        assert payload["base"] == "develop"

    def test_api_failure_returns_none(self):
        """#1500: If _api returns None, create_pr returns None."""
        adapter = _make_forgejo_adapter()
        with patch.object(adapter, "_api", return_value=None):
            result = adapter.create_pr("PR", "body", "branch")
        assert result is None


class TestGitHubCreatePrDraft:
    """#1500: GitHubAdapter.create_pr must pass --draft only when draft=True."""

    def test_draft_true_includes_flag(self):
        """#1500: draft=True should add --draft to gh CLI args."""
        adapter = _make_github_adapter()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/testowner/testrepo/pull/10\n"
        with patch.object(adapter, "_gh", return_value=mock_result) as mock_gh:
            adapter.create_pr("PR", "body", "branch", draft=True)
        args = mock_gh.call_args[0][0]
        assert "--draft" in args

    def test_draft_false_excludes_flag(self):
        """#1500: draft=False should NOT add --draft to gh CLI args."""
        adapter = _make_github_adapter()
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "https://github.com/testowner/testrepo/pull/11\n"
        with patch.object(adapter, "_gh", return_value=mock_result) as mock_gh:
            adapter.create_pr("PR", "body", "branch", draft=False)
        args = mock_gh.call_args[0][0]
        assert "--draft" not in args
