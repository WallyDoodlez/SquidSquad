"""Tests for the SquidSquad Harness (harness.py) and CLI (squidsquad_cli.py).

Tests harness state model, port management, API endpoint routing, CLI port
discovery, and config.py integration. Does NOT start uvicorn or spawn real
agents — all external dependencies are mocked.
"""

import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add scripts to path
SCRIPT_DIR = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestAgentState(unittest.TestCase):
    """Test the AgentState dataclass."""

    def test_initial_state(self):
        from harness import AgentState
        s = AgentState("skill", "/some/path")
        self.assertEqual(s.role, "skill")
        self.assertEqual(s.status, "unknown")
        self.assertEqual(s.clone_path, "/some/path")
        self.assertIsNone(s.boot_time)
        self.assertIsNone(s.last_health_check)

    def test_to_dict(self):
        from harness import AgentState
        s = AgentState("pm")
        s.status = "running"
        s.boot_time = 1000.0
        d = s.to_dict()
        self.assertEqual(d["role"], "pm")
        self.assertEqual(d["status"], "running")
        self.assertEqual(d["boot_time"], 1000.0)


class TestHarnessState(unittest.TestCase):
    """Test the HarnessState model."""

    def test_set_and_get_agent(self):
        from harness import HarnessState, AgentState
        state = HarnessState()
        agent = AgentState("skill")
        agent.status = "running"
        state.set_agent("skill", agent)
        got = state.get_agent("skill")
        self.assertEqual(got.status, "running")

    def test_all_agents_empty(self):
        from harness import HarnessState
        state = HarnessState()
        self.assertEqual(state.all_agents(), [])

    def test_all_agents_returns_dicts(self):
        from harness import HarnessState, AgentState
        state = HarnessState()
        state.set_agent("pm", AgentState("pm"))
        state.set_agent("skill", AgentState("skill"))
        agents = state.all_agents()
        self.assertEqual(len(agents), 2)
        self.assertIsInstance(agents[0], dict)
        roles = {a["role"] for a in agents}
        self.assertEqual(roles, {"pm", "skill"})


class TestPortManagement(unittest.TestCase):
    """Test find_free_port and port reading."""

    def test_find_free_port_default_available(self):
        """When the default port is free, it should be returned."""
        from harness import find_free_port
        import socket
        # Use a high port unlikely to be taken
        port = find_free_port(59999)
        self.assertEqual(port, 59999)

    def test_find_free_port_fallback(self):
        """When default port is taken, should return a different free port."""
        from harness import find_free_port
        import socket
        # Bind the default port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 59998))
        try:
            port = find_free_port(59998)
            self.assertNotEqual(port, 59998)
            self.assertGreater(port, 0)
        finally:
            s.close()


class TestCLIPortDiscovery(unittest.TestCase):
    """Test CLI port discovery from .harness-port file."""

    def test_read_port_missing_file(self):
        from squidsquad_cli import _read_port
        # Patch HARNESS_PORT_FILE to a nonexistent path
        with patch("squidsquad_cli.HARNESS_PORT_FILE", Path("/nonexistent/.harness-port")):
            self.assertIsNone(_read_port())

    def test_read_port_valid_file(self):
        from squidsquad_cli import _read_port
        tmp = REPO_ROOT / ".squidsquad" / ".harness-port.test"
        try:
            tmp.write_text("7373", encoding="utf-8")
            with patch("squidsquad_cli.HARNESS_PORT_FILE", tmp):
                self.assertEqual(_read_port(), 7373)
        finally:
            tmp.unlink(missing_ok=True)

    def test_read_port_invalid_content(self):
        from squidsquad_cli import _read_port
        tmp = REPO_ROOT / ".squidsquad" / ".harness-port.test"
        try:
            tmp.write_text("not-a-number", encoding="utf-8")
            with patch("squidsquad_cli.HARNESS_PORT_FILE", tmp):
                self.assertIsNone(_read_port())
        finally:
            tmp.unlink(missing_ok=True)


class TestConfigIntegration(unittest.TestCase):
    """Test that config.py recognizes harness fields."""

    def test_harness_fields_in_field_map(self):
        import config
        self.assertIn("harness-enabled", config.FIELD_MAP)
        self.assertIn("harness-port", config.FIELD_MAP)

    def test_harness_field_section(self):
        import config
        section, field = config.FIELD_MAP["harness-enabled"]
        self.assertEqual(section, "Harness")
        self.assertEqual(field, "Enabled")

        section, field = config.FIELD_MAP["harness-port"]
        self.assertEqual(section, "Harness")
        self.assertEqual(field, "Port")


class TestHarnessEndpoints(unittest.TestCase):
    """Test FastAPI endpoints using TestClient (if available) or mock."""

    def test_validate_role_accepts_configured(self):
        """_validate_role should accept roles from config."""
        from harness import _validate_role
        with patch("harness.boot_remote._get_all_roles", return_value=["skill", "qa"]):
            self.assertEqual(_validate_role("skill"), "skill")
            self.assertEqual(_validate_role("pm"), "pm")  # Always allowed

    def test_validate_role_rejects_unknown(self):
        """_validate_role should raise 404 for unknown roles."""
        from harness import _validate_role, HTTPException
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]):
            with self.assertRaises(HTTPException) as ctx:
                _validate_role("nonexistent")
            self.assertEqual(ctx.exception.status_code, 404)


class TestCLIUsage(unittest.TestCase):
    """Test CLI argument parsing and usage."""

    def test_usage_on_no_args(self):
        """CLI with no args should print usage and exit 0."""
        from squidsquad_cli import main
        with patch("sys.argv", ["squidsquad"]):
            with patch("builtins.print"):
                rc = main()
                self.assertEqual(rc, 0)

    def test_unknown_command(self):
        """CLI with unknown command should exit 2."""
        from squidsquad_cli import main
        with patch("sys.argv", ["squidsquad", "foobar"]):
            with patch("builtins.print"):
                rc = main()
                self.assertEqual(rc, 2)

    def test_restart_requires_role(self):
        """CLI restart without role should exit 2."""
        from squidsquad_cli import main
        with patch("sys.argv", ["squidsquad", "restart"]):
            with patch("builtins.print"):
                rc = main()
                self.assertEqual(rc, 2)


class TestHarnessHealthPolling(unittest.TestCase):
    """Test that HarnessState.update_health maps health_check output correctly."""

    def test_update_health_maps_statuses(self):
        from harness import HarnessState

        mock_report = {
            "agents": [
                {"role": "skill", "health": "healthy", "clone_path": "/a"},
                {"role": "pm", "health": "stalled", "clone_path": "/b"},
                {"role": "dm", "health": "stopped", "clone_path": "/c"},
            ],
            "all_healthy": False,
        }

        state = HarnessState()
        with patch("harness.health_check.check_all_agents", return_value=mock_report):
            state.update_health()

        self.assertEqual(state.get_agent("skill").status, "running")
        self.assertEqual(state.get_agent("pm").status, "stalled")
        self.assertEqual(state.get_agent("dm").status, "stopped")


if __name__ == "__main__":
    unittest.main()
