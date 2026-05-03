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
        self.assertEqual(s.intent, AgentState.INTENT_RUNNING)
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


class TestStatePersistence(unittest.TestCase):
    """#4966: .harness-state.json persistence for crash recovery."""

    def test_save_and_load_state(self):
        """State file round-trips agent data correctly."""
        import tempfile
        from harness import HarnessState, AgentState, HARNESS_STATE_FILE
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                # Save state
                hs = HarnessState()
                hs.port = 7373
                agent = AgentState("skill", "/clone/path")
                agent.intent = AgentState.INTENT_STOPPING
                agent.status = "running"
                agent.boot_time = 1000.0
                hs.set_agent("skill", agent)
                hs.save_state()

                # Verify file was written
                self.assertTrue(state_file.exists())
                data = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertEqual(data["agents"]["skill"]["intent"], "stopping")

                # Load into new state
                hs2 = HarnessState()
                with patch("harness._log"):
                    hs2.load_state()
                loaded = hs2.get_agent("skill")
                self.assertIsNotNone(loaded)
                self.assertEqual(loaded.intent, AgentState.INTENT_STOPPING)
                self.assertEqual(loaded.clone_path, "/clone/path")

    def test_load_missing_state_file(self):
        """load_state is a no-op when state file doesn't exist."""
        import tempfile
        from harness import HarnessState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / "nonexistent.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                hs.load_state()  # should not raise
                self.assertEqual(hs.all_agents(), [])

    def test_save_state_atomic_write(self):
        """State file is written atomically via .tmp rename."""
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                hs.set_agent("pm", AgentState("pm"))
                hs.save_state()
                # File should exist, .tmp should not
                self.assertTrue(state_file.exists())
                self.assertFalse(state_file.with_suffix(".tmp").exists())


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


class TestEndpointsViaTestClient(unittest.TestCase):
    """Test FastAPI endpoints using TestClient with mocked dependencies."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from harness import app, state, AgentState

        # Pre-populate state so endpoints have data to work with
        state.start_time = time.time()
        state.port = 7373

        cls.client = TestClient(app, raise_server_exceptions=False)
        cls.app = app
        cls.state = state

    def test_get_status(self):
        """GET /status returns harness and agent info."""
        with patch("harness.health_check.check_all_agents", return_value={
            "agents": [{"role": "skill", "health": "healthy", "clone_path": "/a"}],
            "all_healthy": True,
        }):
            resp = self.client.get("/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("harness", data)
        self.assertIn("agents", data)
        self.assertEqual(data["harness"]["status"], "running")

    def test_get_agents(self):
        """GET /agents returns agent list."""
        with patch("harness.health_check.check_all_agents", return_value={
            "agents": [
                {"role": "skill", "health": "healthy", "clone_path": "/a"},
                {"role": "pm", "health": "stalled", "clone_path": "/b"},
            ],
            "all_healthy": False,
        }):
            resp = self.client.get("/agents")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("agents", data)
        self.assertGreaterEqual(len(data["agents"]), 1)

    def test_post_agents_all_start(self):
        """POST /agents/all/start returns 200 with results."""
        mock_result = {"role": "skill", "action": "skip", "success": True,
                       "message": "skip: already running", "timestamp": 0}
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness.boot_remote.boot_agent", return_value=mock_result):
            resp = self.client.post("/agents/all/start")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 1)
        self.assertTrue(data["results"][0]["success"])

    def test_post_agents_all_stop_skips_stopping(self):
        """POST /agents/all/stop skips agents already stopping (#4949)."""
        from harness import state as harness_state, AgentState
        agent = AgentState("skill")
        agent.intent = AgentState.INTENT_STOPPING
        harness_state.set_agent("skill", agent)
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness.boot_remote._get_clone_path", return_value="/fake"):
            resp = self.client.post("/agents/all/stop")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["results"][0]["action"], "skip")
        self.assertIn("Already stopping", data["results"][0]["message"])

    def test_post_agent_start(self):
        """POST /agents/{role}/start spawns agent."""
        mock_result = {"role": "skill", "action": "spawn", "success": True,
                       "message": "spawned", "timestamp": 0}
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness.boot_remote.boot_agent", return_value=mock_result):
            # Clear any cached running state
            from harness import state as harness_state
            if harness_state.get_agent("skill"):
                harness_state.get_agent("skill").status = "stopped"
            resp = self.client.post("/agents/skill/start")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["success"])

    def test_post_agent_stop(self):
        """POST /agents/{role}/stop sets intent=stopping (#4966 — no .stop-after-cycle)."""
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]):
            resp = self.client.post("/agents/skill/stop")
        self.assertEqual(resp.status_code, 200)
        # Intent should be stopping — no sentinel file written (#4966)
        from harness import state as harness_state, AgentState
        agent = harness_state.get_agent("skill")
        self.assertEqual(agent.intent, AgentState.INTENT_STOPPING)

    def test_post_agent_restart(self):
        """POST /agents/{role}/restart calls reboot."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.reboot_agent.reboot", return_value=0):
                resp = self.client.post("/agents/skill/restart")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            self.assertEqual(data["action"], "restart")

    def test_post_agent_restart_sets_intent(self):
        """POST /agents/{role}/restart sets intent=restarting (#4966 — no .stop-after-cycle)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir):
                resp = self.client.post("/agents/skill/restart")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            # Intent should be restarting — no sentinel file (#4966)
            from harness import state as harness_state, AgentState
            agent = harness_state.get_agent("skill")
            self.assertEqual(agent.intent, AgentState.INTENT_RESTARTING)

    def test_post_shutdown_returns_202(self):
        """POST /shutdown returns 202 Accepted (non-blocking)."""
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness.boot_remote._get_clone_path", return_value="/fake"), \
             patch("harness.boot_remote._has_stop_sentinel", return_value=True), \
             patch("harness.os._exit"):  # Prevent actual exit
            resp = self.client.post("/shutdown")
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertEqual(data["status"], "shutting_down")

    def test_unknown_role_returns_404(self):
        """POST /agents/{unknown}/start returns 404."""
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]):
            resp = self.client.post("/agents/nonexistent/start")
        self.assertEqual(resp.status_code, 404)

    def test_agents_all_start_not_captured_by_role_param(self):
        """POST /agents/all/start should NOT hit the {role} handler."""
        mock_result = {"role": "skill", "action": "skip", "success": True,
                       "message": "skip", "timestamp": 0}
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness.boot_remote.boot_agent", return_value=mock_result):
            resp = self.client.post("/agents/all/start")
        # Should be 200 from start_all, not 404 from _validate_role("all")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("results", resp.json())


# ---------------------------------------------------------------------------
# Intent-based lifecycle — regression #4949
# ---------------------------------------------------------------------------

class TestIntentLifecycle(unittest.TestCase):
    """Test intent tracking and auto-reboot logic (#4949)."""

    def test_agent_state_has_intent(self):
        from harness import AgentState
        s = AgentState("skill")
        self.assertEqual(s.intent, AgentState.INTENT_RUNNING)

    def test_intent_in_to_dict(self):
        from harness import AgentState
        s = AgentState("skill")
        s.intent = AgentState.INTENT_STOPPING
        d = s.to_dict()
        self.assertEqual(d["intent"], "stopping")

    def test_auto_reboot_on_unexpected_death(self):
        """Agent was running, dies unexpectedly, intent=running → reboot."""
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill", "/tmp/clone")
        agent.status = "running"
        agent.intent = AgentState.INTENT_RUNNING
        hs.set_agent("skill", agent)

        # Simulate health check returning "stopped"
        mock_report = {
            "agents": [{"role": "skill", "health": "stopped", "clone_path": "/tmp/clone"}]
        }
        with patch("harness.health_check.check_all_agents", return_value=mock_report), \
             patch("harness.boot_remote.boot_agent") as mock_boot:
            hs.update_health()

        mock_boot.assert_called_once_with("skill")
        self.assertEqual(hs.get_agent("skill").status, "starting")

    def test_no_reboot_when_intent_stopping(self):
        """Agent was running, dies, intent=stopping → do NOT reboot."""
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill", "/tmp/clone")
        agent.status = "running"
        agent.intent = AgentState.INTENT_STOPPING
        hs.set_agent("skill", agent)

        mock_report = {
            "agents": [{"role": "skill", "health": "stopped", "clone_path": "/tmp/clone"}]
        }
        with patch("harness.health_check.check_all_agents", return_value=mock_report), \
             patch("harness.boot_remote.boot_agent") as mock_boot:
            hs.update_health()

        mock_boot.assert_not_called()

    def test_reboot_on_restart_intent(self):
        """Agent dies with intent=restarting → reboot and reset intent."""
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill", "/tmp/clone")
        agent.status = "running"
        agent.intent = AgentState.INTENT_RESTARTING
        hs.set_agent("skill", agent)

        # First health check: agent dies → reboot triggered
        mock_report_dead = {
            "agents": [{"role": "skill", "health": "stopped", "clone_path": "/tmp/clone"}]
        }
        with patch("harness.health_check.check_all_agents", return_value=mock_report_dead), \
             patch("harness.boot_remote.boot_agent"):
            hs.update_health()

        # Second health check: agent came back → intent reset to running
        mock_report_alive = {
            "agents": [{"role": "skill", "health": "healthy", "clone_path": "/tmp/clone"}]
        }
        with patch("harness.health_check.check_all_agents", return_value=mock_report_alive), \
             patch("harness.boot_remote.boot_agent"):
            hs.update_health()

        self.assertEqual(hs.get_agent("skill").intent, AgentState.INTENT_RUNNING)


if __name__ == "__main__":
    unittest.main()
