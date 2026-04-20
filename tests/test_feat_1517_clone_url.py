"""Regression tests for #1517 — forgejo_setup.py clone_url construction.

Verifies that create_repo correctly extracts clone_url from the API response,
and falls back to a constructed URL when the repo already exists or the
API response is missing clone_url.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import forgejo_setup


class TestCreateRepoCloneUrl:
    """#1517: create_repo must return the correct clone_url."""

    @patch("forgejo_setup.urllib.request.urlopen")
    def test_clone_url_from_api_response(self, mock_urlopen):
        """#1517: clone_url should come from the API response's clone_url field."""
        api_response = {
            "name": "my-project",
            "clone_url": "http://localhost:3000/squid/my-project.git",
            "html_url": "http://localhost:3000/squid/my-project",
        }
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(api_response).encode("utf-8")
        mock_resp.status = 201
        mock_urlopen.return_value = mock_resp

        result = forgejo_setup.create_repo("my-project", "fake-token")
        assert result["ok"] is True
        assert result["clone_url"] == "http://localhost:3000/squid/my-project.git"

    @patch("forgejo_setup.urllib.request.urlopen")
    def test_clone_url_fallback_when_repo_exists(self, mock_urlopen):
        """#1517: When repo already exists, clone_url should be fetched or constructed."""
        import urllib.error

        # First call: HTTPError (repo exists)
        error_body = b'{"message": "The repository with the same name already exists."}'
        http_error = urllib.error.HTTPError(
            url="http://localhost:3000/api/v1/user/repos",
            code=409,
            msg="Conflict",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=error_body)),
        )

        # Second call: successful repo lookup
        repo_data = {
            "name": "my-project",
            "clone_url": "http://localhost:3000/squid/my-project.git",
        }
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(repo_data).encode("utf-8")

        mock_urlopen.side_effect = [http_error, mock_resp]

        result = forgejo_setup.create_repo("my-project", "fake-token", owner="squid")
        assert result["ok"] is True
        assert result["clone_url"] == "http://localhost:3000/squid/my-project.git"

    @patch("forgejo_setup.urllib.request.urlopen")
    def test_clone_url_constructed_when_lookup_fails(self, mock_urlopen):
        """#1517: When repo exists but lookup fails, construct clone_url from parts."""
        import urllib.error

        # First call: HTTPError (repo exists)
        error_body = b'{"message": "The repository already exists."}'
        http_error = urllib.error.HTTPError(
            url="http://localhost:3000/api/v1/user/repos",
            code=409,
            msg="Conflict",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=error_body)),
        )

        # Second call: also fails
        mock_urlopen.side_effect = [http_error, Exception("connection refused")]

        result = forgejo_setup.create_repo("my-project", "fake-token", owner="squid")
        assert result["ok"] is True
        assert result["clone_url"] == f"{forgejo_setup.FORGEJO_URL}/squid/my-project.git"

    @patch("forgejo_setup.urllib.request.urlopen")
    def test_clone_url_empty_on_unrelated_error(self, mock_urlopen):
        """#1517: Non-'already exists' errors should return ok=False."""
        import urllib.error

        error_body = b'{"message": "Unauthorized"}'
        http_error = urllib.error.HTTPError(
            url="http://localhost:3000/api/v1/user/repos",
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=error_body)),
        )
        mock_urlopen.side_effect = http_error

        result = forgejo_setup.create_repo("my-project", "fake-token")
        assert result["ok"] is False
        assert result["clone_url"] == ""

    @patch("forgejo_setup.urllib.request.urlopen")
    def test_clone_url_empty_string_treated_correctly(self, mock_urlopen):
        """#1517: API response with empty clone_url should return empty string."""
        api_response = {
            "name": "my-project",
            "clone_url": "",
        }
        mock_resp = MagicMock()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_resp.read.return_value = json.dumps(api_response).encode("utf-8")
        mock_urlopen.return_value = mock_resp

        result = forgejo_setup.create_repo("my-project", "fake-token")
        assert result["ok"] is True
        assert result["clone_url"] == ""
