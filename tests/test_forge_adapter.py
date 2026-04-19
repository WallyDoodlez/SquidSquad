"""Tests for references/scripts/forge_adapter.py — forge backend abstraction."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import forge_adapter


class TestReadForgeConfig:
    def test_defaults_to_github(self, tmp_path):
        with patch.object(forge_adapter, "CONFIG_MD", tmp_path / "missing"):
            config = forge_adapter._read_forge_config()
        assert config["provider"] == "github"
        assert config["endpoint"] == "https://api.github.com"

    def test_reads_forgejo_config(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text(
            "## Forge Backend\n\n"
            "- **Provider**: forgejo\n"
            "- **Endpoint**: http://localhost:3000\n"
            "- **Owner**: testuser\n"
            "- **Repo**: myproject\n"
        )
        with patch.object(forge_adapter, "CONFIG_MD", config_file):
            config = forge_adapter._read_forge_config()
        assert config["provider"] == "forgejo"
        assert config["endpoint"] == "http://localhost:3000"
        assert config["owner"] == "testuser"
        assert config["repo"] == "myproject"

    def test_missing_section_returns_defaults(self, tmp_path):
        config_file = tmp_path / "config.md"
        config_file.write_text("## Other Section\n\n- **Foo**: bar\n")
        with patch.object(forge_adapter, "CONFIG_MD", config_file):
            config = forge_adapter._read_forge_config()
        assert config["provider"] == "github"


class TestGetAdapter:
    def setup_method(self):
        forge_adapter.reset_cache()

    def test_github_default(self):
        config = {"provider": "github", "endpoint": "https://api.github.com",
                  "owner": "test", "repo": "repo"}
        adapter = forge_adapter.get_adapter(config)
        assert isinstance(adapter, forge_adapter.GitHubAdapter)

    def test_forgejo_provider(self):
        config = {"provider": "forgejo", "endpoint": "http://localhost:3000",
                  "owner": "test", "repo": "repo"}
        adapter = forge_adapter.get_adapter(config)
        assert isinstance(adapter, forge_adapter.ForgejoAdapter)

    def test_forgejo_local_provider(self):
        config = {"provider": "forgejo-local", "endpoint": "http://localhost:3000",
                  "owner": "test", "repo": "repo"}
        adapter = forge_adapter.get_adapter(config)
        assert isinstance(adapter, forge_adapter.ForgejoAdapter)

    def test_forgejo_remote_provider(self):
        config = {"provider": "forgejo-remote", "endpoint": "https://forge.example.com",
                  "owner": "test", "repo": "repo"}
        adapter = forge_adapter.get_adapter(config)
        assert isinstance(adapter, forge_adapter.ForgejoAdapter)

    def test_unknown_falls_back_to_github(self):
        config = {"provider": "unknown", "endpoint": "", "owner": "t", "repo": "r"}
        adapter = forge_adapter.get_adapter(config)
        assert isinstance(adapter, forge_adapter.GitHubAdapter)

    def test_caches_adapter(self):
        config = {"provider": "github", "endpoint": "", "owner": "t", "repo": "r"}
        a1 = forge_adapter.get_adapter(config)
        a2 = forge_adapter.get_adapter()
        assert a1 is a2

    def test_reset_cache(self):
        config = {"provider": "github", "endpoint": "", "owner": "t", "repo": "r"}
        a1 = forge_adapter.get_adapter(config)
        forge_adapter.reset_cache()
        config2 = {"provider": "forgejo", "endpoint": "http://localhost:3000",
                    "owner": "t", "repo": "r"}
        a2 = forge_adapter.get_adapter(config2)
        assert type(a1) != type(a2)


class TestGitHubAdapter:
    def _make_adapter(self):
        return forge_adapter.GitHubAdapter({
            "provider": "github", "endpoint": "https://api.github.com",
            "owner": "test", "repo": "repo",
        })

    @patch("subprocess.run")
    def test_list_issues(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"number": 1, "title": "Bug", "labels": []}]),
        )
        adapter = self._make_adapter()
        result = adapter.list_issues(labels=["role:skill"])
        assert len(result) == 1
        assert result[0]["number"] == 1

    @patch("subprocess.run")
    def test_add_comment(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = self._make_adapter()
        assert adapter.add_comment(42, "test comment") is True

    @patch("subprocess.run")
    def test_check_connection(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        adapter = self._make_adapter()
        ok, msg = adapter.check_connection()
        assert ok is True


class TestForgejoAdapter:
    def _make_adapter(self):
        adapter = forge_adapter.ForgejoAdapter({
            "provider": "forgejo", "endpoint": "http://localhost:3000",
            "owner": "testuser", "repo": "myproject",
        })
        adapter._token = "test-token"
        return adapter

    def test_repo_path(self):
        adapter = self._make_adapter()
        assert adapter._repo_path() == "/repos/testuser/myproject"

    def test_provider_is_forgejo(self):
        adapter = self._make_adapter()
        assert adapter.provider == "forgejo"


class TestForgejoAdapterErrorHandling:
    """Error-handling tests for ForgejoAdapter._api() (#1494)."""

    def _make_adapter(self):
        adapter = forge_adapter.ForgejoAdapter({
            "provider": "forgejo", "endpoint": "http://localhost:3000",
            "owner": "testuser", "repo": "myproject",
        })
        adapter._token = "test-token"
        return adapter

    @patch("urllib.request.urlopen")
    def test_http_401_returns_none(self, mock_urlopen):
        """HTTP 401 (bad token) returns None."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://localhost", 401, "Unauthorized", {}, None
        )
        adapter = self._make_adapter()
        result = adapter._api("GET", "/api/v1/repos/test/test")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_http_404_returns_none(self, mock_urlopen):
        """HTTP 404 (missing repo) returns None."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://localhost", 404, "Not Found", {}, None
        )
        adapter = self._make_adapter()
        result = adapter._api("GET", "/repos/test/test")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_http_500_returns_none(self, mock_urlopen):
        """HTTP 500 (server error) returns None."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://localhost", 500, "Internal Server Error", {}, None
        )
        adapter = self._make_adapter()
        result = adapter._api("GET", "/repos/test/test")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_connection_error_returns_none(self, mock_urlopen):
        """Connection refused returns None."""
        mock_urlopen.side_effect = ConnectionRefusedError("Connection refused")
        adapter = self._make_adapter()
        result = adapter._api("GET", "/repos/test/test")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_timeout_returns_none(self, mock_urlopen):
        """Timeout returns None."""
        import socket
        mock_urlopen.side_effect = socket.timeout("timed out")
        adapter = self._make_adapter()
        result = adapter._api("GET", "/repos/test/test")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_malformed_json_returns_none(self, mock_urlopen):
        """Malformed JSON response returns None."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json {{"
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        adapter = self._make_adapter()
        result = adapter._api("GET", "/repos/test/test")
        assert result is None

    @patch("urllib.request.urlopen")
    def test_valid_response_parsed(self, mock_urlopen):
        """Valid JSON response is parsed correctly."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"number": 42, "title": "test"}'
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        adapter = self._make_adapter()
        result = adapter._api("GET", "/repos/test/test")
        assert result == {"number": 42, "title": "test"}

    @patch("urllib.request.urlopen")
    def test_list_issues_empty_on_error(self, mock_urlopen):
        """list_issues returns empty list on API error."""
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "http://localhost", 500, "Error", {}, None
        )
        adapter = self._make_adapter()
        result = adapter.list_issues()
        assert result == []


class TestBaseAdapter:
    def test_edit_labels_calls_both(self):
        adapter = forge_adapter.ForgeAdapter({
            "provider": "test", "endpoint": "", "owner": "", "repo": "",
        })
        added = []
        removed = []
        adapter.add_labels = lambda n, l: added.extend(l) or True
        adapter.remove_labels = lambda n, l: removed.extend(l) or True
        adapter.edit_labels(1, add=["a", "b"], remove=["c"])
        assert added == ["a", "b"]
        assert removed == ["c"]
