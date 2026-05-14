"""Tests for references/scripts/squidsquad_cli.py — mocked HTTP, no real harness."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import squidsquad_cli


# ---------------------------------------------------------------------------
# Port discovery
# ---------------------------------------------------------------------------

class TestReadPort:
    def test_reads_valid_port(self, tmp_path):
        port_file = tmp_path / ".harness-port"
        port_file.write_text("8080", encoding="utf-8")
        with patch.object(squidsquad_cli, "HARNESS_PORT_FILE", port_file):
            assert squidsquad_cli._read_port() == 8080

    def test_returns_none_when_missing(self, tmp_path):
        with patch.object(squidsquad_cli, "HARNESS_PORT_FILE", tmp_path / "nope"):
            assert squidsquad_cli._read_port() is None

    def test_returns_none_on_empty_file(self, tmp_path):
        port_file = tmp_path / ".harness-port"
        port_file.write_text("", encoding="utf-8")
        with patch.object(squidsquad_cli, "HARNESS_PORT_FILE", port_file):
            assert squidsquad_cli._read_port() is None

    def test_returns_none_on_non_integer(self, tmp_path):
        port_file = tmp_path / ".harness-port"
        port_file.write_text("not-a-number", encoding="utf-8")
        with patch.object(squidsquad_cli, "HARNESS_PORT_FILE", port_file):
            assert squidsquad_cli._read_port() is None

    def test_strips_whitespace(self, tmp_path):
        port_file = tmp_path / ".harness-port"
        port_file.write_text("  9090  \n", encoding="utf-8")
        with patch.object(squidsquad_cli, "HARNESS_PORT_FILE", port_file):
            assert squidsquad_cli._read_port() == 9090


class TestDiscoverHarness:
    def test_returns_port_when_alive(self):
        with patch.object(squidsquad_cli, "_read_port", return_value=8080), \
             patch.object(squidsquad_cli, "_harness_alive", return_value=True):
            assert squidsquad_cli._discover_harness() == 8080

    def test_returns_none_when_no_port_file(self):
        with patch.object(squidsquad_cli, "_read_port", return_value=None):
            assert squidsquad_cli._discover_harness() is None

    def test_returns_none_when_port_exists_but_dead(self):
        with patch.object(squidsquad_cli, "_read_port", return_value=8080), \
             patch.object(squidsquad_cli, "_harness_alive", return_value=False):
            assert squidsquad_cli._discover_harness() is None


# ---------------------------------------------------------------------------
# CLI main() dispatch
# ---------------------------------------------------------------------------

class TestMainDispatch:
    def test_help_shows_usage(self, capsys):
        with patch.object(sys, "argv", ["cli", "--help"]):
            result = squidsquad_cli.main()
        assert result == 0
        assert "Usage:" in capsys.readouterr().out

    def test_no_args_shows_usage(self, capsys):
        with patch.object(sys, "argv", ["cli"]):
            result = squidsquad_cli.main()
        assert result == 0
        assert "Usage:" in capsys.readouterr().out

    def test_unknown_command_returns_2(self, capsys):
        with patch.object(sys, "argv", ["cli", "bogus"]):
            result = squidsquad_cli.main()
        assert result == 2
        assert "Unknown command" in capsys.readouterr().err

    def test_restart_without_role_returns_2(self, capsys):
        with patch.object(sys, "argv", ["cli", "restart"]):
            result = squidsquad_cli.main()
        assert result == 2

    def test_dispatches_start(self):
        with patch.object(sys, "argv", ["cli", "start"]), \
             patch.object(squidsquad_cli, "cmd_start", return_value=0) as mock:
            result = squidsquad_cli.main()
        assert result == 0
        mock.assert_called_once()

    def test_dispatches_stop_all(self):
        with patch.object(sys, "argv", ["cli", "stop"]), \
             patch.object(squidsquad_cli, "cmd_stop", return_value=0) as mock:
            result = squidsquad_cli.main()
        mock.assert_called_once_with(None)

    def test_dispatches_stop_role(self):
        with patch.object(sys, "argv", ["cli", "stop", "skill"]), \
             patch.object(squidsquad_cli, "cmd_stop", return_value=0) as mock:
            result = squidsquad_cli.main()
        mock.assert_called_once_with("skill")

    def test_dispatches_restart_role(self):
        with patch.object(sys, "argv", ["cli", "restart", "pm"]), \
             patch.object(squidsquad_cli, "cmd_restart", return_value=0) as mock:
            result = squidsquad_cli.main()
        mock.assert_called_once_with("pm")

    def test_dispatches_status(self):
        with patch.object(sys, "argv", ["cli", "status"]), \
             patch.object(squidsquad_cli, "cmd_status", return_value=0) as mock:
            result = squidsquad_cli.main()
        mock.assert_called_once()

    def test_dispatches_shutdown(self):
        with patch.object(sys, "argv", ["cli", "shutdown"]), \
             patch.object(squidsquad_cli, "cmd_shutdown", return_value=0) as mock:
            result = squidsquad_cli.main()
        mock.assert_called_once()


# ---------------------------------------------------------------------------
# Commands — no harness running
# ---------------------------------------------------------------------------

class TestCommandsNoHarness:
    """Commands should handle missing harness gracefully."""

    def test_stop_no_harness(self, capsys):
        with patch.object(squidsquad_cli, "_discover_harness", return_value=None):
            result = squidsquad_cli.cmd_stop()
        assert result == 1
        assert "not running" in capsys.readouterr().err.lower()

    def test_restart_no_harness(self, capsys):
        with patch.object(squidsquad_cli, "_discover_harness", return_value=None):
            result = squidsquad_cli.cmd_restart("skill")
        assert result == 1

    def test_status_no_harness(self, capsys):
        with patch.object(squidsquad_cli, "_discover_harness", return_value=None):
            result = squidsquad_cli.cmd_status()
        assert result == 1

    def test_shutdown_no_harness(self, capsys):
        with patch.object(squidsquad_cli, "_discover_harness", return_value=None):
            result = squidsquad_cli.cmd_shutdown()
        assert result == 0  # Nothing to shut down is OK


# ---------------------------------------------------------------------------
# Commands — with mocked harness
# ---------------------------------------------------------------------------

class TestCommandsWithHarness:
    """Commands with a mocked harness API."""

    def test_status_prints_agents(self, capsys):
        status_response = {
            "harness": {"status": "running", "port": 8080, "uptime_human": "5m"},
            "agents": [
                {"role": "skill", "status": "running"},
                {"role": "pm", "status": "stopped"},
            ],
        }
        with patch.object(squidsquad_cli, "_discover_harness", return_value=8080), \
             patch.object(squidsquad_cli, "_api_call", return_value=status_response):
            result = squidsquad_cli.cmd_status()
        assert result == 0
        out = capsys.readouterr().out
        assert "skill" in out
        assert "pm" in out

    def test_status_no_agents(self, capsys):
        with patch.object(squidsquad_cli, "_discover_harness", return_value=8080), \
             patch.object(squidsquad_cli, "_api_call", return_value={"harness": {}, "agents": []}):
            result = squidsquad_cli.cmd_status()
        assert result == 0
        assert "No agents" in capsys.readouterr().out

    def test_stop_single_role(self, capsys):
        with patch.object(squidsquad_cli, "_discover_harness", return_value=8080), \
             patch.object(squidsquad_cli, "_api_call", return_value={"message": "stopped"}) as mock_api:
            result = squidsquad_cli.cmd_stop("skill")
        assert result == 0
        mock_api.assert_called_once_with(8080, "POST", "/agents/skill/stop")

    def test_stop_all(self, capsys):
        with patch.object(squidsquad_cli, "_discover_harness", return_value=8080), \
             patch.object(squidsquad_cli, "_api_call", return_value={
                 "results": [{"role": "skill", "success": True}]
             }) as mock_api:
            result = squidsquad_cli.cmd_stop()
        assert result == 0
        mock_api.assert_called_once_with(8080, "POST", "/agents/all/stop")

    def test_restart_success(self, capsys):
        with patch.object(squidsquad_cli, "_discover_harness", return_value=8080), \
             patch.object(squidsquad_cli, "_api_call", return_value={
                 "success": True, "message": "restarted"
             }):
            result = squidsquad_cli.cmd_restart("skill")
        assert result == 0

    def test_restart_failure(self, capsys):
        with patch.object(squidsquad_cli, "_discover_harness", return_value=8080), \
             patch.object(squidsquad_cli, "_api_call", return_value={
                 "success": False, "message": "not found"
             }):
            result = squidsquad_cli.cmd_restart("nonexistent")
        assert result == 1


class TestApiCallErrorDetails:
    """#7619: _api_call must include error details in URLError message."""

    def test_error_message_includes_exception(self, capsys):
        """URLError output should contain the actual exception details (#7842)."""
        import urllib.error
        error_msg = "Connection refused"
        with patch("squidsquad_cli.urllib.request.urlopen",
                   side_effect=urllib.error.URLError(error_msg)):
            with pytest.raises(SystemExit):
                squidsquad_cli._api_call(7373, "GET", "/status")
        stderr = capsys.readouterr().err
        assert error_msg in stderr, \
            f"URLError details must appear in stderr, got: {stderr!r}"
