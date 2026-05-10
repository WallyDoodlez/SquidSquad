"""Tests for references/scripts/forgejo_setup.py — Forgejo deployment automation."""

import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import forgejo_setup


class TestCheckDocker:
    @patch("subprocess.run")
    def test_docker_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        result = forgejo_setup.check_docker()
        assert result["ok"] is False
        assert "not found" in result["message"].lower()

    @patch("subprocess.run")
    def test_docker_version_fails(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="error")
        result = forgejo_setup.check_docker()
        assert result["ok"] is False

    @patch("subprocess.run")
    @patch("socket.socket")
    def test_docker_ready(self, mock_socket, mock_run):
        # docker --version, docker compose version, docker info all succeed
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker 24.0")
        # Ports are free
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 1  # port not in use
        mock_sock_instance.__enter__ = lambda s: mock_sock_instance
        mock_sock_instance.__exit__ = MagicMock(return_value=False)
        mock_socket.return_value = mock_sock_instance
        result = forgejo_setup.check_docker()
        assert result["ok"] is True

    @patch("subprocess.run")
    @patch("socket.socket")
    def test_port_conflict(self, mock_socket, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker 24.0")
        mock_sock_instance = MagicMock()
        mock_sock_instance.connect_ex.return_value = 0  # port in use
        mock_sock_instance.__enter__ = lambda s: mock_sock_instance
        mock_sock_instance.__exit__ = MagicMock(return_value=False)
        mock_socket.return_value = mock_sock_instance
        result = forgejo_setup.check_docker()
        assert result["ok"] is False
        assert "port" in result["message"].lower()


    @patch("subprocess.run")
    def test_our_container_running_skips_port_check(self, mock_run):
        """When squidsquad-forgejo container is running and using ports,
        check_docker should still return ok=True (port check is skipped)."""
        def run_side_effect(cmd, **kwargs):
            if "ps" in cmd and "--filter" in cmd:
                return MagicMock(
                    returncode=0, stdout="squidsquad-forgejo\n", stderr=""
                )
            return MagicMock(returncode=0, stdout="Docker 24.0", stderr="")

        mock_run.side_effect = run_side_effect
        result = forgejo_setup.check_docker()
        assert result["ok"] is True
        assert result["message"] == "Docker ready"


class TestStatus:
    @patch("urllib.request.urlopen")
    def test_forgejo_running(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"version": "9.0.0"}'
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        result = forgejo_setup.status()
        assert result["running"] is True
        assert result["version"] == "9.0.0"

    @patch("urllib.request.urlopen")
    def test_forgejo_not_running(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")
        result = forgejo_setup.status()
        assert result["running"] is False


class TestDefaultCompose:
    def test_generates_valid_yaml(self):
        yaml_content = forgejo_setup._default_compose_yaml()
        assert "forgejo" in yaml_content
        assert "3000" in yaml_content
        assert "2222" in yaml_content
        assert "codeberg.org/forgejo/forgejo" in yaml_content


class TestComposeTemplateExists:
    def test_template_exists(self):
        template = Path(__file__).resolve().parent.parent / "references" / "templates" / "forgejo-compose.yaml"
        assert template.exists()
        content = template.read_text()
        assert "forgejo" in content


class TestDeploy:
    """#6984: deploy() must have test coverage for all branches."""

    @patch("subprocess.run")
    def test_deploy_fails_when_docker_not_ready(self, mock_run):
        mock_run.side_effect = FileNotFoundError
        result = forgejo_setup.deploy()
        assert result["ok"] is False

    @patch("urllib.request.urlopen")
    @patch("subprocess.run")
    def test_deploy_fails_on_compose_error(self, mock_run, mock_urlopen, tmp_path):
        # Docker check succeeds, compose fails
        def run_side_effect(cmd, **kwargs):
            if "compose" in cmd and "up" in cmd:
                return MagicMock(returncode=1, stderr="compose error")
            return MagicMock(returncode=0, stdout="Docker 24.0")

        mock_run.side_effect = run_side_effect
        with patch.object(forgejo_setup, "DEPLOY_DIR", tmp_path), \
             patch.object(forgejo_setup, "COMPOSE_TEMPLATE", tmp_path / "nonexistent"), \
             patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 1
            mock_sock.__enter__ = lambda s: mock_sock
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_socket.return_value = mock_sock
            result = forgejo_setup.deploy()
        assert result["ok"] is False
        assert "compose" in result["message"].lower()

    @patch("urllib.request.urlopen")
    @patch("subprocess.run")
    def test_deploy_success(self, mock_run, mock_urlopen, tmp_path):
        mock_run.return_value = MagicMock(returncode=0, stdout="Docker 24.0")
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        with patch.object(forgejo_setup, "DEPLOY_DIR", tmp_path), \
             patch.object(forgejo_setup, "COMPOSE_TEMPLATE", tmp_path / "nonexistent"), \
             patch("socket.socket") as mock_socket:
            mock_sock = MagicMock()
            mock_sock.connect_ex.return_value = 1
            mock_sock.__enter__ = lambda s: mock_sock
            mock_sock.__exit__ = MagicMock(return_value=False)
            mock_socket.return_value = mock_sock
            result = forgejo_setup.deploy()
        assert result["ok"] is True
        assert result["url"]


class TestCreateRepo:
    """#6983: create_repo() must have test coverage for all branches."""

    @patch("urllib.request.urlopen")
    def test_create_repo_success(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"clone_url": "http://localhost:3000/squid/test.git"}'
        mock_resp.__enter__ = lambda s: mock_resp
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        result = forgejo_setup.create_repo("test", "token123")
        assert result["ok"] is True
        assert "test.git" in result["clone_url"]

    @patch("urllib.request.urlopen")
    def test_create_repo_already_exists(self, mock_urlopen):
        import urllib.error
        # First call (create) raises 409, second call (query) succeeds
        error_resp = MagicMock()
        error_resp.read.return_value = b'{"message": "repository already exists"}'
        mock_urlopen.side_effect = [
            urllib.error.HTTPError("url", 409, "Conflict", {}, error_resp),
        ]
        # Patch for the follow-up repo query
        with patch("urllib.request.urlopen") as mock_url2:
            mock_url2.side_effect = urllib.error.HTTPError(
                "url", 409, "Conflict", {},
                MagicMock(read=lambda: b'{"message": "repository already exists"}'),
            )
            result = forgejo_setup.create_repo("test", "token123")
        assert result["ok"] is True
        assert "already exists" in result["message"]

    @patch("urllib.request.urlopen")
    def test_create_repo_auth_failure(self, mock_urlopen):
        import urllib.error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            "url", 401, "Unauthorized", {},
            MagicMock(read=lambda: b"Unauthorized"),
        )
        result = forgejo_setup.create_repo("test", "bad-token")
        assert result["ok"] is False
        assert "401" in result["message"]

    @patch("urllib.request.urlopen")
    def test_create_repo_connection_error(self, mock_urlopen):
        mock_urlopen.side_effect = ConnectionError("refused")
        result = forgejo_setup.create_repo("test", "token123")
        assert result["ok"] is False


class TestTeardown:
    @patch("subprocess.run")
    def test_teardown_no_deployment(self, mock_run):
        with patch.object(forgejo_setup, "DEPLOY_DIR", Path("/nonexistent")):
            result = forgejo_setup.teardown()
        assert result["ok"] is True
        assert "no" in result["message"].lower()

    @patch("subprocess.run")
    def test_teardown_success(self, mock_run, tmp_path):
        mock_run.return_value = MagicMock(returncode=0)
        deploy_dir = tmp_path / "forgejo"
        deploy_dir.mkdir()
        with patch.object(forgejo_setup, "DEPLOY_DIR", deploy_dir):
            result = forgejo_setup.teardown()
        assert result["ok"] is True


# ---------------------------------------------------------------------------
# #4200 regression: credential leak in error messages
# ---------------------------------------------------------------------------

class TestCreateTokenCredentialSafety:
    """create_token must not leak credentials in error messages."""

    def test_http_error_does_not_expose_credentials(self):
        """#4200: HTTP error must show status code only, not headers/URL."""
        import urllib.error
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.HTTPError(
                url="http://localhost:3000/api/v1/users/admin/tokens",
                code=401,
                msg="Unauthorized",
                hdrs=None,
                fp=None,
            )
            result = forgejo_setup.create_token("admin", "s3cret_password")
        assert result["ok"] is False
        assert "HTTP 401" in result["message"]
        # Credentials must NOT appear in the error message
        assert "s3cret_password" not in result["message"]
        assert "admin:s3cret" not in result["message"]

    def test_connection_error_does_not_expose_details(self):
        """URLError must not expose internal details."""
        import urllib.error
        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = urllib.error.URLError("connection refused")
            result = forgejo_setup.create_token("admin", "password123")
        assert result["ok"] is False
        assert "connection error" in result["message"]
        assert "password123" not in result["message"]
