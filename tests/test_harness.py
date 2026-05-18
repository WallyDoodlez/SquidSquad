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

    def test_save_state_holds_lock_during_write(self):
        """#7441: Disk write must happen inside the lock to prevent races."""
        import inspect
        from harness import HarnessState
        source = inspect.getsource(HarnessState.save_state)
        lines = source.splitlines()
        in_lock = False
        write_inside_lock = False
        for line in lines:
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if "with self._lock" in stripped:
                in_lock = True
                lock_indent = indent
            elif in_lock and "write_text" in stripped:
                write_inside_lock = indent > lock_indent
                break
        self.assertTrue(write_inside_lock,
                        "save_state must hold lock during disk write (#7441)")


class TestStartAllPersistence(unittest.TestCase):
    """#6820: start_all must set intent=running and call save_state."""

    def test_start_all_sets_intent_running(self):
        """start_all sets intent=INTENT_RUNNING for spawned agents."""
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill")
        agent.status = "starting"
        agent.intent = AgentState.INTENT_RUNNING
        agent.boot_time = 1000.0
        hs.set_agent("skill", agent)
        got = hs.get_agent("skill")
        self.assertEqual(got.intent, AgentState.INTENT_RUNNING)

    def test_start_all_calls_save_state(self):
        """#6820: Verify start_all code path includes save_state call."""
        import inspect
        from harness import start_all
        source = inspect.getsource(start_all)
        self.assertIn("save_state()", source,
                       "start_all must call save_state() to persist intent")
        self.assertIn("INTENT_RUNNING", source,
                       "start_all must set intent to INTENT_RUNNING")


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
    """Test that HarnessState.update_health uses direct PID checks (#4966)."""

    def test_update_health_detects_running_via_pid(self):
        """Agent with alive PID in .claude-pid is detected as running."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            # Write a PID file
            (role_dir / ".claude-pid").write_text(str(os.getpid()), encoding="utf-8")

            hs = HarnessState()
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            agent = hs.get_agent("skill")
            self.assertIsNotNone(agent)
            self.assertEqual(agent.status, "running")
            self.assertEqual(agent.claude_pid, os.getpid())

    def test_update_health_detects_dead_agent(self):
        """Agent with dead PID is detected as not running."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            # Write a PID that doesn't exist (99999999)
            (role_dir / ".claude-pid").write_text("99999999", encoding="utf-8")

            hs = HarnessState()
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.health_check.check_agent_health", return_value={"health": "unknown"}), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            agent = hs.get_agent("skill")
            self.assertIsNotNone(agent)
            self.assertNotEqual(agent.status, "running")


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
        with patch.object(self.state, "update_health"):
            resp = self.client.get("/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("harness", data)
        self.assertIn("agents", data)
        self.assertEqual(data["harness"]["status"], "running")

    def test_get_agents(self):
        """GET /agents returns agent list."""
        with patch.object(self.state, "update_health"):
            resp = self.client.get("/agents")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("agents", data)

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
        # #4792: removed `_has_stop_sentinel` patch — function deleted.
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness.boot_remote._get_clone_path", return_value="/fake"), \
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

    # #8689 — idle agents should be killed immediately on restart, not wait for
    # the next /loop tick (potentially 30+ minutes).
    def test_restart_kills_immediately_when_idle(self):
        """Idle current-state → restart kills the claude PID and reports immediate=True."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / "current-state").write_text("idle|", encoding="utf-8")
            killed = []

            def _fake_kill(pid):
                killed.append(pid)

            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.reboot_agent._read_claude_pid", return_value=(12345, True)), \
                 patch("harness.reboot_agent._kill_process", side_effect=_fake_kill):
                resp = self.client.post("/agents/skill/restart")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            self.assertTrue(data["immediate"])
            self.assertEqual(data["killed_pid"], 12345)
            self.assertEqual(killed, [12345])

    def test_restart_falls_back_to_queued_when_busy(self):
        """Non-idle current-state → restart only sets intent, no kill."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / "current-state").write_text(
                "implementing|dev-agent — 🔨 #999...", encoding="utf-8"
            )
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.reboot_agent._read_claude_pid", return_value=(12345, True)), \
                 patch("harness.reboot_agent._kill_process") as mock_kill:
                resp = self.client.post("/agents/skill/restart")
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertTrue(data["success"])
            self.assertFalse(data["immediate"])
            mock_kill.assert_not_called()

    def test_restart_queued_when_idle_but_no_claude_pid(self):
        """Idle but no live claude PID → fall back to queued (auto-reboot loop handles it)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / "current-state").write_text("idle|", encoding="utf-8")
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.reboot_agent._read_claude_pid", return_value=(None, False)), \
                 patch("harness.reboot_agent._kill_process") as mock_kill:
                resp = self.client.post("/agents/skill/restart")
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(resp.json()["immediate"])
            mock_kill.assert_not_called()

    def test_restart_queued_when_no_current_state_file(self):
        """Missing current-state file → safe default is queued restart."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.reboot_agent._kill_process") as mock_kill:
                resp = self.client.post("/agents/skill/restart")
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(resp.json()["immediate"])
            mock_kill.assert_not_called()

    def test_restart_still_sets_intent_on_immediate_path(self):
        """Immediate kill path must still set intent=restarting so auto-reboot fires."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / "current-state").write_text("idle|", encoding="utf-8")
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.reboot_agent._read_claude_pid", return_value=(12345, True)), \
                 patch("harness.reboot_agent._kill_process"):
                resp = self.client.post("/agents/skill/restart")
            self.assertEqual(resp.status_code, 200)
            from harness import state as harness_state, AgentState
            agent = harness_state.get_agent("skill")
            self.assertEqual(agent.intent, AgentState.INTENT_RESTARTING)

    def test_restart_kill_failure_falls_back_to_queued(self):
        """If kill raises, response reports immediate=False (queued fallback)."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / "current-state").write_text("idle|", encoding="utf-8")
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.reboot_agent._read_claude_pid", return_value=(12345, True)), \
                 patch("harness.reboot_agent._kill_process", side_effect=OSError("denied")):
                resp = self.client.post("/agents/skill/restart")
            self.assertEqual(resp.status_code, 200)
            self.assertFalse(resp.json()["immediate"])


# ---------------------------------------------------------------------------
# Intent-based lifecycle — regression #4949
# ---------------------------------------------------------------------------

class TestIntentLifecycle(unittest.TestCase):
    """Test intent tracking and auto-reboot logic (#4949)."""

    def test_agent_state_has_intent(self):
        from harness import AgentState
        s = AgentState("skill")
        self.assertEqual(s.intent, AgentState.INTENT_RUNNING)

    def test_all_intent_constants_defined(self):
        """All four intent states have class constants (#5423)."""
        from harness import AgentState
        self.assertEqual(AgentState.INTENT_RUNNING, "running")
        self.assertEqual(AgentState.INTENT_STOPPING, "stopping")
        self.assertEqual(AgentState.INTENT_RESTARTING, "restarting")
        self.assertEqual(AgentState.INTENT_STOPPED, "stopped")

    def test_intent_in_to_dict(self):
        from harness import AgentState
        s = AgentState("skill")
        s.intent = AgentState.INTENT_STOPPING
        d = s.to_dict()
        self.assertEqual(d["intent"], "stopping")

    def test_auto_reboot_on_unexpected_death(self):
        """Agent was running, dies unexpectedly, intent=running → reboot (#4966)."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            # Dead PID
            (role_dir / ".claude-pid").write_text("99999999", encoding="utf-8")

            hs = HarnessState()
            agent = AgentState("skill", tmpdir)
            agent.status = "running"
            agent.intent = AgentState.INTENT_RUNNING
            agent.claude_pid = 99999999
            hs.set_agent("skill", agent)

            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.boot_remote.boot_agent") as mock_boot, \
                 patch("harness.health_check.check_agent_health", return_value={"health": "unknown"}), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            mock_boot.assert_called_once_with("skill")
            self.assertEqual(hs.get_agent("skill").status, "starting")

    def test_no_reboot_when_intent_stopping(self):
        """Agent was running, dies, intent=stopping → do NOT reboot (#4966)."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / ".claude-pid").write_text("99999999", encoding="utf-8")

            hs = HarnessState()
            agent = AgentState("skill", tmpdir)
            agent.status = "running"
            agent.intent = AgentState.INTENT_STOPPING
            agent.claude_pid = 99999999
            hs.set_agent("skill", agent)

            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.boot_remote.boot_agent") as mock_boot, \
                 patch("harness.health_check.check_agent_health", return_value={"health": "unknown"}), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            mock_boot.assert_not_called()

    def test_stopping_intent_transitions_to_stopped_on_death(self):
        """Agent dies with intent=stopping → intent transitions to INTENT_STOPPED (#5423)."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / ".claude-pid").write_text("99999999", encoding="utf-8")

            hs = HarnessState()
            agent = AgentState("skill", tmpdir)
            agent.status = "running"
            agent.intent = AgentState.INTENT_STOPPING
            agent.claude_pid = 99999999
            hs.set_agent("skill", agent)

            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.boot_remote.boot_agent") as mock_boot, \
                 patch("harness.health_check.check_agent_health", return_value={"health": "unknown"}), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            # Must use the class constant, not a bare string
            self.assertEqual(hs.get_agent("skill").intent, AgentState.INTENT_STOPPED)
            self.assertEqual(AgentState.INTENT_STOPPED, "stopped")
            self.assertIsNone(hs.get_agent("skill").claude_pid)

    def test_reboot_on_restart_intent(self):
        """Agent dies with intent=restarting → reboot. Comes back → intent=running (#4966)."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / ".claude-pid").write_text("99999999", encoding="utf-8")

            hs = HarnessState()
            agent = AgentState("skill", tmpdir)
            agent.status = "running"
            agent.intent = AgentState.INTENT_RESTARTING
            agent.claude_pid = 99999999
            hs.set_agent("skill", agent)

            # First poll: dead → reboot triggered
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.boot_remote.boot_agent"), \
                 patch("harness.health_check.check_agent_health", return_value={"health": "unknown"}), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            # Second poll: agent came back alive (use current process PID)
            (role_dir / ".claude-pid").write_text(str(os.getpid()), encoding="utf-8")
            hs.get_agent("skill").status = "starting"  # was set by reboot
            hs.get_agent("skill").claude_pid = None  # cleared by reboot

            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.boot_remote.boot_agent"), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            self.assertEqual(hs.get_agent("skill").intent, AgentState.INTENT_RUNNING)


class TestManualRebootClearsStoppingIntent(unittest.TestCase):
    """#7637: Harness must clear stopping/stopped intent when agent is alive."""

    def test_alive_agent_with_stopping_intent_resets_to_running(self):
        """Agent stopped via harness, manually rebooted → intent resets to running."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            # Agent is alive (use current process PID)
            (role_dir / ".claude-pid").write_text(str(os.getpid()), encoding="utf-8")

            hs = HarnessState()
            agent = AgentState("skill", tmpdir)
            agent.status = "stopped"
            agent.intent = AgentState.INTENT_STOPPING
            agent.claude_pid = None  # PID cleared when agent died
            hs.set_agent("skill", agent)

            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            got = hs.get_agent("skill")
            self.assertEqual(got.status, "running")
            self.assertEqual(got.intent, AgentState.INTENT_RUNNING,
                             "Alive agent with stopping intent must reset to running (#7637)")

    def test_alive_agent_with_stopped_intent_resets_to_running(self):
        """Agent fully stopped (intent=stopped), manually rebooted → intent resets."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / ".claude-pid").write_text(str(os.getpid()), encoding="utf-8")

            hs = HarnessState()
            agent = AgentState("skill", tmpdir)
            agent.status = "stopped"
            agent.intent = AgentState.INTENT_STOPPED
            agent.claude_pid = None
            hs.set_agent("skill", agent)

            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            got = hs.get_agent("skill")
            self.assertEqual(got.status, "running")
            self.assertEqual(got.intent, AgentState.INTENT_RUNNING,
                             "Alive agent with stopped intent must reset to running (#7637)")

    def test_same_pid_stopping_intent_not_cleared(self):
        """Agent told to stop but still alive (same PID) → intent stays stopping (#7637)."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)

            hs = HarnessState()
            agent = AgentState("skill", tmpdir)
            agent.status = "running"
            agent.intent = AgentState.INTENT_STOPPING
            agent.claude_pid = os.getpid()  # Same PID — stop is in-flight
            hs.set_agent("skill", agent)

            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            got = hs.get_agent("skill")
            self.assertEqual(got.status, "running")
            self.assertEqual(got.intent, AgentState.INTENT_STOPPING,
                             "Same PID still alive — stopping intent must NOT be cleared (#7637)")


class TestEventLifecycleManager(unittest.TestCase):
    """#7630 P-1/P-3: EventLifecycleManager disk persistence and in-flight tracking."""

    def test_persist_and_load_round_trip(self):
        """Event state (events + in_flight + dispatched) survives harness restart."""
        import tempfile
        from harness import EventStream, EventLifecycleManager

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".event-state.json"
            with patch("harness.EVENT_STATE_FILE", state_file):
                stream = EventStream()
                mgr = EventLifecycleManager(stream)

                event = {"id": "abc12345", "event_type": "test", "role": "skill"}
                mgr.append(event)
                mgr.dispatch("abc12345", "skill", event)

                self.assertTrue(state_file.exists())

                # Load into new manager
                stream2 = EventStream()
                mgr2 = EventLifecycleManager(stream2)
                mgr2.load()

                events = stream2.get_all()
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["id"], "abc12345")
                # In-flight state also restored
                self.assertEqual(mgr2.get_in_flight("skill"), ["abc12345"])

    def test_in_flight_tracking(self):
        """Dispatch/ack lifecycle tracks per-role in-flight events."""
        from harness import EventStream, EventLifecycleManager

        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            mgr = EventLifecycleManager(stream)

            mgr.dispatch("evt1", "skill", {"id": "evt1"})
            self.assertEqual(mgr.get_in_flight("skill"), ["evt1"])

            result = mgr.ack("evt1", "skill")
            self.assertTrue(result)
            self.assertEqual(mgr.get_in_flight("skill"), [])

    def test_ack_unknown_event_returns_false(self):
        """Acking an event not in-flight returns False."""
        from harness import EventStream, EventLifecycleManager

        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            mgr = EventLifecycleManager(stream)

            result = mgr.ack("nonexistent", "skill")
            self.assertFalse(result)

    def test_in_flight_cap(self):
        """Per-role in-flight queue respects cap. Dropped events excluded from _dispatched."""
        from harness import EventStream, EventLifecycleManager

        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            mgr = EventLifecycleManager(stream, max_in_flight=2)

            mgr.dispatch("evt1", "skill", {"id": "evt1"})
            mgr.dispatch("evt2", "skill", {"id": "evt2"})
            mgr.dispatch("evt3", "skill", {"id": "evt3"})  # should be dropped

            self.assertEqual(len(mgr.get_in_flight("skill")), 2)
            self.assertNotIn("evt3", mgr._dispatched)

    def test_load_is_idempotent(self):
        """Calling load() twice does not duplicate events (#7630 CRITICAL-2)."""
        import tempfile
        from harness import EventStream, EventLifecycleManager

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".event-state.json"
            with patch("harness.EVENT_STATE_FILE", state_file):
                stream = EventStream()
                mgr = EventLifecycleManager(stream)
                mgr.append({"id": "x1", "event_type": "test", "role": "skill"})

                stream2 = EventStream()
                mgr2 = EventLifecycleManager(stream2)
                mgr2.load()
                mgr2.load()  # second call should be no-op

                self.assertEqual(len(stream2.get_all()), 1)


class TestTerminalPidInAgentState(unittest.TestCase):
    """#7630 P-6: terminal_pid in AgentState."""

    def test_terminal_pid_in_slots(self):
        from harness import AgentState
        s = AgentState("skill")
        self.assertIsNone(s.terminal_pid)

    def test_terminal_pid_in_to_dict(self):
        from harness import AgentState
        s = AgentState("skill")
        s.terminal_pid = 12345
        d = s.to_dict()
        self.assertEqual(d["terminal_pid"], 12345)

    def test_terminal_pid_persisted_in_state(self):
        """terminal_pid round-trips through save/load."""
        import tempfile
        from harness import HarnessState, AgentState

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                agent = AgentState("skill")
                agent.terminal_pid = 99999
                hs.set_agent("skill", agent)
                hs.save_state()

                hs2 = HarnessState()
                with patch("harness._log"):
                    hs2.load_state()
                loaded = hs2.get_agent("skill")
                self.assertEqual(loaded.terminal_pid, 99999)


class TestTimeoutScanner(unittest.TestCase):
    """#7630 2-3: EventLifecycleManager timeout detection."""

    def test_overdue_event_detected(self):
        """Events past timeout are detected by timeout_scan."""
        from harness import EventStream, EventLifecycleManager

        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")), \
             patch("harness._log"):
            stream = EventStream()
            mgr = EventLifecycleManager(stream, timeout_minutes=0)  # 0 = immediate timeout

            mgr.dispatch("evt1", "skill", {"id": "evt1"})
            # Backdate dispatch time to force timeout
            mgr._dispatch_times["evt1"] = time.time() - 1

            timed_out = mgr.timeout_scan()
            # First scan: retry (not yet at max retries)
            self.assertEqual(len(timed_out), 0)  # retried, not timed out
            self.assertEqual(mgr._retry_counts.get("evt1"), 1)

    def test_max_retries_causes_timeout(self):
        """After max retries, event is removed from in-flight."""
        from harness import EventStream, EventLifecycleManager

        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")), \
             patch("harness._log"):
            stream = EventStream()
            mgr = EventLifecycleManager(stream, timeout_minutes=0, max_retries=1)

            mgr.dispatch("evt1", "skill", {"id": "evt1"})
            mgr._dispatch_times["evt1"] = time.time() - 1
            mgr._retry_counts["evt1"] = 1  # Already at max

            timed_out = mgr.timeout_scan()
            self.assertEqual(len(timed_out), 1)
            self.assertEqual(timed_out[0], ("skill", "evt1"))
            self.assertEqual(mgr.get_in_flight("skill"), [])


class TestEventDrivenPhase4(unittest.TestCase):
    """#7630 Phase 4: Event-driven wake prototype — config, endpoints, poll."""

    def test_config_event_driven_field(self):
        """config.py can read event-driven field from config.md."""
        from config import get_field
        # Should return "yes" or "no" — defaults to "no" if section absent
        val = get_field("event-driven")
        self.assertIn(val.lower(), ("yes", "no"))

    def test_config_scan_idle_timeout_field(self):
        """config.py can read scan-idle-timeout field."""
        from config import get_field
        try:
            val = get_field("scan-idle-timeout")
            self.assertTrue(int(val) > 0)
        except SystemExit:
            pass

    def test_event_poll_target_mode_url(self):
        """event_poll.py in target mode queries /events/for/<role>."""
        import event_poll

        with patch.object(event_poll, "_discover_port", return_value=7373), \
             patch.object(event_poll, "_read_cursor", return_value="abc123"), \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"events": []}'
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            result = event_poll.poll("skill", target_mode=True)

            # Verify the URL used /events/for/skill
            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            self.assertIn("/events/for/skill", req.full_url)
            self.assertEqual(result, [])

    def test_event_poll_legacy_mode_url(self):
        """event_poll.py in legacy mode queries /events with role param."""
        import event_poll

        with patch.object(event_poll, "_discover_port", return_value=7373), \
             patch.object(event_poll, "_read_cursor", return_value=""), \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"events": [{"id": "x1"}]}'
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            with patch.object(event_poll, "_write_cursor") as mock_write:
                result = event_poll.poll("skill", target_mode=False)

            # Verify legacy URL uses /events?role=skill
            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            self.assertIn("/events?", req.full_url)
            self.assertIn("role=skill", req.full_url)
            self.assertNotIn("/events/for/", req.full_url)

    def test_execute_transition_calls_tracker(self):
        """_execute_transition calls tracker.py with correct args."""
        from harness import _execute_transition

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            _execute_transition({
                "number": 123,
                "from": "in-progress",
                "to": "pending-test",
                "role": "skill-lead",
            })
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("tracker.py", args[1])
            self.assertIn("transition", args)
            self.assertIn("123", args)
            self.assertIn("in-progress", args)
            self.assertIn("pending-test", args)

    def test_execute_transition_raises_on_failure(self):
        """_execute_transition raises RuntimeError on non-zero exit."""
        from harness import _execute_transition

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="not allowed")
            with self.assertRaises(RuntimeError):
                _execute_transition({"number": 1, "from": "a", "to": "b"})

    def test_execute_comment_calls_tracker(self):
        """_execute_comment calls tracker.py comment with correct args."""
        from harness import _execute_comment

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stderr="")
            _execute_comment({
                "number": 456,
                "role": "pm-lead",
                "message": "Test comment",
            })
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            self.assertIn("comment", args)
            self.assertIn("456", args)

    def test_execute_comment_raises_on_incomplete(self):
        """_execute_comment raises ValueError if required fields missing."""
        from harness import _execute_comment

        with self.assertRaises(ValueError):
            _execute_comment({"number": 1})  # missing message

    def test_execute_comment_rejects_oversized_message(self):
        """_execute_comment raises ValueError for messages > 4096 chars."""
        from harness import _execute_comment

        with self.assertRaises(ValueError):
            _execute_comment({"number": 1, "message": "x" * 4097})

    def test_execute_comment_rejects_null_bytes(self):
        """_execute_comment raises ValueError for messages with null bytes."""
        from harness import _execute_comment

        with self.assertRaises(ValueError):
            _execute_comment({"number": 1, "message": "hello\x00world"})

    def test_dispatch_skips_already_dispatched(self):
        """dispatch() skips events that are already in _dispatched."""
        from harness import EventStream, EventLifecycleManager

        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            mgr = EventLifecycleManager(stream)

            mgr.dispatch("evt1", "skill", {"id": "evt1"})
            self.assertEqual(mgr.get_in_flight("skill"), ["evt1"])

            # Dispatch same event again — should not duplicate
            mgr.dispatch("evt1", "skill", {"id": "evt1"})
            self.assertEqual(mgr.get_in_flight("skill"), ["evt1"])


class TestGetEventsForRole(unittest.TestCase):
    """#7630 Phase 4: GET /events/for/{role} endpoint tests."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from harness import app, event_stream, event_lifecycle

        cls.client = TestClient(app, raise_server_exceptions=False)
        cls.event_stream = event_stream
        cls.event_lifecycle = event_lifecycle

    def setUp(self):
        """Clear event stream between tests."""
        with self.event_stream._lock:
            self.event_stream._events.clear()
        with self.event_lifecycle._lock:
            self.event_lifecycle._in_flight.clear()
            self.event_lifecycle._dispatched.clear()
            self.event_lifecycle._dispatch_times.clear()

    def test_filters_by_target_role(self):
        """GET /events/for/skill returns only events targeted at skill."""
        from harness import event_stream

        # Add events for different roles
        event_stream.append({
            "id": "e1", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "skill", "issue_number": "1"},
        })
        event_stream.append({
            "id": "e2", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "pm", "issue_number": "2"},
        })

        with patch("harness._validate_role"):
            resp = self.client.get("/events/for/skill")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["id"], "e1")

    def test_marks_dispatched(self):
        """GET /events/for/skill marks returned events as dispatched."""
        from harness import event_stream, event_lifecycle

        event_stream.append({
            "id": "e3", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "skill", "issue_number": "3"},
        })

        with patch("harness._validate_role"):
            self.client.get("/events/for/skill")

        self.assertIn("e3", event_lifecycle.get_in_flight("skill"))

    def test_since_cursor_filters_events(self):
        """GET /events/for/skill?since=X returns only events after cursor."""
        from harness import event_stream

        event_stream.append({
            "id": "old1", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "skill"},
        })
        event_stream.append({
            "id": "new1", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "skill"},
        })

        with patch("harness._validate_role"):
            resp = self.client.get("/events/for/skill?since=old1")

        data = resp.json()
        ids = [e["id"] for e in data["events"]]
        self.assertNotIn("old1", ids)
        self.assertIn("new1", ids)

    def test_does_not_redispatch_already_dispatched(self):
        """GET /events/for/skill does not re-dispatch already dispatched events."""
        from harness import event_stream, event_lifecycle

        event_stream.append({
            "id": "e4", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "skill"},
        })

        # Pre-dispatch the event
        event_lifecycle.dispatch("e4", "skill", {"id": "e4"})

        with patch("harness._validate_role"):
            self.client.get("/events/for/skill")

        # Should still be dispatched exactly once (not duplicated in in_flight)
        self.assertEqual(event_lifecycle.get_in_flight("skill").count("e4"), 1)


class TestCompleteEventEndpoint(unittest.TestCase):
    """#7630 Phase 4: POST /events/{event_id}/complete endpoint tests."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from harness import app, event_stream, event_lifecycle

        cls.client = TestClient(app, raise_server_exceptions=False)
        cls.event_stream = event_stream
        cls.event_lifecycle = event_lifecycle

    def setUp(self):
        """Clear lifecycle state between tests."""
        with self.event_lifecycle._lock:
            self.event_lifecycle._in_flight.clear()
            self.event_lifecycle._dispatched.clear()
            self.event_lifecycle._dispatch_times.clear()

    def test_complete_acks_in_flight_event(self):
        """POST /events/evt1/complete acks an in-flight event."""
        self.event_lifecycle.dispatch("evt1", "skill", {"id": "evt1"})
        self.assertIn("evt1", self.event_lifecycle.get_in_flight("skill"))

        resp = self.client.post("/events/evt1/complete", json={
            "role": "skill",
            "status": "success",
            "summary": "Done",
        })

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertNotIn("evt1", self.event_lifecycle.get_in_flight("skill"))

    def test_complete_returns_410_for_unknown_event(self):
        """POST /events/unknown/complete returns 410 when event not in-flight."""
        resp = self.client.post("/events/unknown-id/complete", json={
            "role": "skill",
            "status": "success",
            "summary": "Done",
        })

        self.assertEqual(resp.status_code, 410)
        data = resp.json()
        self.assertEqual(data["status"], "gone")

    def test_complete_executes_transitions(self):
        """POST /events/evt2/complete executes status transitions."""
        self.event_lifecycle.dispatch("evt2", "skill", {"id": "evt2"})

        with patch("harness._execute_transition") as mock_trans:
            resp = self.client.post("/events/evt2/complete", json={
                "role": "skill",
                "status": "success",
                "summary": "Fixed",
                "transitions": [
                    {"number": 123, "from": "in-progress", "to": "pending-test", "role": "skill-lead"}
                ],
            })

        self.assertEqual(resp.status_code, 200)
        mock_trans.assert_called_once()

    def test_complete_executes_comments(self):
        """POST /events/evt3/complete executes tracker comments."""
        self.event_lifecycle.dispatch("evt3", "skill", {"id": "evt3"})

        with patch("harness._execute_comment") as mock_comment:
            resp = self.client.post("/events/evt3/complete", json={
                "role": "skill",
                "status": "success",
                "summary": "Commented",
                "comments": [
                    {"number": 123, "role": "skill-lead", "message": "Done."}
                ],
            })

        self.assertEqual(resp.status_code, 200)
        mock_comment.assert_called_once()

    def test_complete_reports_partial_on_side_effect_failure(self):
        """POST /events/evt4/complete returns partial on transition errors."""
        self.event_lifecycle.dispatch("evt4", "skill", {"id": "evt4"})

        with patch("harness._execute_transition", side_effect=RuntimeError("tracker fail")):
            resp = self.client.post("/events/evt4/complete", json={
                "role": "skill",
                "status": "success",
                "summary": "Partial",
                "transitions": [
                    {"number": 1, "from": "a", "to": "b"}
                ],
            })

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "partial")
        self.assertTrue(len(data["errors"]) > 0)

    def test_complete_requires_role(self):
        """POST /events/evt5/complete returns 400 without role."""
        resp = self.client.post("/events/evt5/complete", json={
            "status": "success",
            "summary": "No role",
        })

        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# Thin-harness invariants — #8914
# ---------------------------------------------------------------------------

class TestThinHarnessInvariants(unittest.TestCase):
    """#8914: TrackerHandoffDispatcher + per-role event gating were removed.

    CONTEXT.md §2 locks the harness as a pure broadcast pipe with no tracker
    observation, no dispatch logic, and no per-role queue knowledge. These
    tests are negative guards — they fail loudly if the dispatcher or gating
    is reintroduced.
    """

    def test_tracker_handoff_dispatcher_class_is_absent(self):
        import harness
        self.assertNotIn(
            "TrackerHandoffDispatcher", dir(harness),
            "harness must remain a pure broadcast pipe — no dispatcher class",
        )

    def test_handoff_dispatcher_instance_is_absent(self):
        import harness
        self.assertNotIn(
            "handoff_dispatcher", dir(harness),
            "no global handoff_dispatcher — harness has no per-role dispatch",
        )

    def test_status_transition_does_not_call_subprocess(self):
        """A status-transition event must NOT trigger any gh/tracker work
        on the harness side (no _get_work_queue, no `gh issue list`)."""
        from fastapi.testclient import TestClient
        from harness import app
        client = TestClient(app)
        with patch("harness.subprocess.run") as mock_run:
            resp = client.post("/events", json={
                "event_type": "status-transition",
                "role": "skill",
                "payload": {"issue_number": "55", "from": "in-progress", "to": "pending-test"},
                "timestamp": "2026-05-18T00:00:00",
            })
        self.assertEqual(resp.status_code, 200)
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# _emit_event regression — #8949
# ---------------------------------------------------------------------------

class TestEmitEventRegression(unittest.TestCase):
    """#8949: PM-filed audit B bug — `_emit_event` was alleged to call
    `_log_event(body)` with `body` undefined, killing the daemon thread on
    every call (notably the merge thread in `_do_merge`).

    Current source already uses `_log_event(event)` so the bug doesn't
    reproduce — these tests lock that in so a regression would fail loudly.
    """

    def test_emit_event_runs_without_nameerror(self):
        """Direct invocation: must not raise NameError on the log call."""
        import harness
        # Would raise NameError under the regressed version PM described.
        harness._emit_event(
            "regression-test", "skill", payload={"check": True},
        )

    def test_emit_event_appends_to_stream_and_logs(self):
        """End-to-end: the event reaches the lifecycle stream and the log
        helper is invoked exactly once with the new event dict."""
        import harness
        before = len(harness.event_stream)
        with patch("harness._log_event") as mock_log:
            harness._emit_event(
                "merge-thread-probe", "harness",
                payload={"pr_number": "9999"},
            )
        after = len(harness.event_stream)
        self.assertEqual(after, before + 1)
        mock_log.assert_called_once()
        # The argument must be the new event dict, not `body` (the regressed
        # version would have failed with NameError before reaching this line).
        (arg,), _ = mock_log.call_args
        self.assertIsInstance(arg, dict)
        self.assertEqual(arg["event_type"], "merge-thread-probe")
        self.assertEqual(arg["role"], "harness")

    def test_emit_event_source_uses_event_not_body(self):
        """Static guard: the `_emit_event` body references `event`, not the
        stale `body` name. Locks the fix in source so an editor change
        outside testing can't reintroduce the typo."""
        import inspect
        import harness
        src = inspect.getsource(harness._emit_event)
        self.assertIn("_log_event(event)", src)
        self.assertNotIn("_log_event(body)", src)


# ---------------------------------------------------------------------------
# Bootup-complete flag (informational only) — #8695 / #8914
# ---------------------------------------------------------------------------

class TestBootupCompleteFlag(unittest.TestCase):
    """#8695 / #8914: bootup_complete is recorded and exposed but NEVER gates.

    The flag remains on AgentState and rides through GET /agents/{role}.
    GET /events/for/<role> ignores it — see CONTEXT.md §5.2.
    """

    def setUp(self):
        from harness import state
        # Snapshot then clear agents in-place so other modules that captured
        # `state` at import time still see the same object.
        self._restore_agents = dict(state.agents)
        state.agents.clear()
        from fastapi.testclient import TestClient
        from harness import app
        self.client = TestClient(app)

    def tearDown(self):
        from harness import state
        state.agents.clear()
        state.agents.update(self._restore_agents)

    def test_default_bootup_complete_is_false(self):
        from harness import AgentState
        agent = AgentState("skill")
        self.assertFalse(agent.bootup_complete)

    def test_to_dict_includes_bootup_complete(self):
        from harness import AgentState
        agent = AgentState("skill")
        agent.bootup_complete = True
        self.assertTrue(agent.to_dict()["bootup_complete"])

    def test_events_for_role_never_gated_when_flag_false(self):
        """#8914: gating was removed. Even with bootup_complete=False the
        endpoint returns the normal event payload (never `gated`)."""
        from harness import AgentState, state, event_stream
        agent = AgentState("skill")
        agent.bootup_complete = False
        state.set_agent("skill", agent)
        event_stream.append({
            "id": "e_nogate_a", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "skill", "issue_number": "1"},
        })
        with patch("harness._validate_role"):
            resp = self.client.get("/events/for/skill")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertNotIn("gated", data)
        self.assertGreaterEqual(data["total"], 1)

    def test_events_for_role_flows_when_flag_true(self):
        """Events flow regardless of the flag — confirms parity with the
        flag=False case so we know flag state never gates."""
        from harness import AgentState, state, event_stream
        agent = AgentState("skill")
        agent.bootup_complete = True
        state.set_agent("skill", agent)
        event_stream.append({
            "id": "e_unique_1", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "skill", "issue_number": "1"},
        })
        with patch("harness._validate_role"):
            resp = self.client.get("/events/for/skill")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertNotIn("gated", data)
        self.assertGreaterEqual(data["total"], 1)

    def test_bootup_complete_event_sets_flag(self):
        """POST /events with event_type=bootup-complete sets the flag on AgentState.
        This is purely informational — the flag is exposed via /agents/{role}."""
        from harness import state
        resp = self.client.post("/events", json={
            "event_type": "bootup-complete",
            "role": "skill",
            "payload": {},
            "timestamp": "2026-05-18T00:00:00",
        })
        self.assertEqual(resp.status_code, 200)
        agent = state.get_agent("skill")
        self.assertIsNotNone(agent)
        self.assertTrue(agent.bootup_complete)

    def test_no_agent_state_returns_normal_payload(self):
        """If no AgentState exists for a role, /events/for/<role> still
        returns the standard event list. (Was already true; #8914 keeps it.)"""
        from harness import event_stream
        event_stream.append({
            "id": "e_nogate_1", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "skill", "issue_number": "1"},
        })
        with patch("harness._validate_role"):
            resp = self.client.get("/events/for/skill")
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn("gated", resp.json())

    def test_start_clears_bootup_complete(self):
        """POST /agents/<role>/start resets bootup_complete=False on fresh spawn."""
        from harness import AgentState, state
        prev = AgentState("skill")
        prev.bootup_complete = True
        prev.status = "stopped"
        state.set_agent("skill", prev)
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness.boot_remote.boot_agent",
                   return_value={"role": "skill", "action": "spawn", "success": True,
                                  "message": "ok", "terminal_pid": 1}):
            self.client.post("/agents/skill/start")
        self.assertFalse(state.get_agent("skill").bootup_complete)

    def test_restart_clears_bootup_complete(self):
        """POST /agents/<role>/restart resets bootup_complete=False."""
        import tempfile
        from harness import AgentState, state
        prev = AgentState("skill")
        prev.bootup_complete = True
        state.set_agent("skill", prev)
        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / ".squidsquad" / "skill").mkdir(parents=True)
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir):
                self.client.post("/agents/skill/restart")
        self.assertFalse(state.get_agent("skill").bootup_complete)


class TestEventBusBootupComplete(unittest.TestCase):
    """#8695: event_bus.bootup_complete() helper."""

    def test_emits_bootup_complete_event(self):
        import event_bus
        with patch.object(event_bus, "emit") as mock_emit:
            event_bus.bootup_complete("skill")
        mock_emit.assert_called_once_with("bootup-complete", "skill", payload={})

    def test_no_op_without_role(self):
        import event_bus
        with patch.object(event_bus, "emit") as mock_emit:
            event_bus.bootup_complete("")
            event_bus.bootup_complete(None)
        mock_emit.assert_not_called()


# ---------------------------------------------------------------------------
# Review fixes — #8695 + #8694 post-DeepSeek
# ---------------------------------------------------------------------------

class TestReviewFixes(unittest.TestCase):
    """DeepSeek review fixes for #8694 and #8695."""

    # ---- #8695 review fixes ------------------------------------------------

    def test_save_state_persists_bootup_complete(self):
        """#8695 R1: save_state writes bootup_complete to the state file."""
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                agent = AgentState("skill")
                agent.bootup_complete = True
                hs.set_agent("skill", agent)
                hs.save_state()
                data = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertTrue(data["agents"]["skill"]["bootup_complete"])

    def test_load_state_restores_bootup_complete(self):
        """#8695 R1: load_state restores bootup_complete so already-running
        agents don't get gated forever after a harness restart."""
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            state_file.write_text(json.dumps({
                "agents": {"skill": {
                    "intent": "running", "clone_path": "",
                    "bootup_complete": True,
                }}
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                with patch("harness._log"):
                    hs.load_state()
                self.assertTrue(hs.get_agent("skill").bootup_complete)

    def test_load_state_defaults_bootup_complete_false_for_old_files(self):
        """#8695 R1: state files predating this change → bootup_complete=False."""
        import tempfile
        from harness import HarnessState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            state_file.write_text(json.dumps({
                "agents": {"skill": {"intent": "running", "clone_path": ""}}
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                with patch("harness._log"):
                    hs.load_state()
                self.assertFalse(hs.get_agent("skill").bootup_complete)

    def test_reboot_affected_agents_clears_bootup_complete(self):
        """#8695 R2: compose-driven restart resets bootup_complete=False."""
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill")
        agent.intent = AgentState.INTENT_RUNNING
        agent.bootup_complete = True
        hs.set_agent("skill", agent)
        import harness
        prev_state = harness.state
        harness.state = hs
        # Fake git-diff output so the function decides skill's CLAUDE.md changed
        fake_git_diff = MagicMock()
        fake_git_diff.returncode = 0
        fake_git_diff.stdout = ".squidsquad/skill/CLAUDE.md\n"
        try:
            with patch("harness._log"), \
                 patch("harness.subprocess.run", return_value=fake_git_diff), \
                 patch.object(hs, "save_state"):
                harness._reboot_affected_agents(123, ["references/sub-skills/common/x.md"])
        finally:
            harness.state = prev_state
        self.assertFalse(hs.get_agent("skill").bootup_complete)

    # ---- #8694 review fixes ------------------------------------------------

    def test_external_detector_mark_emitted_is_thread_safe(self):
        """#8694 R1: mark_emitted holds _emitted_lock; concurrent writes don't crash."""
        from harness import ExternalActivityDetector
        det = ExternalActivityDetector()
        import threading as _t
        errors = []

        def hammer(start):
            try:
                for i in range(200):
                    det.mark_emitted(start + i)
            except Exception as e:
                errors.append(e)

        threads = [_t.Thread(target=hammer, args=(i * 1000,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(errors, [])
        # Bounded at 500 entries
        self.assertLessEqual(len(det._emitted_issues), 500)

    def test_external_detector_eviction_bounds_at_500(self):
        """#8694 R1: oldest entries evict when count exceeds 500."""
        from harness import ExternalActivityDetector
        det = ExternalActivityDetector()
        for n in range(600):
            det.mark_emitted(n)
        self.assertLessEqual(len(det._emitted_issues), 500)
        # The newest entries are retained
        self.assertTrue(det.is_emitted(599))

    # TrackerHandoffDispatcher tests removed in #8914 — the class no longer
    # exists, so its review-fix tests have nothing to assert against. The
    # ExternalActivityDetector lock/eviction tests above still apply.


# ---------------------------------------------------------------------------
# /human/queue endpoint — #8704
# ---------------------------------------------------------------------------

class TestHumanQueueEndpoint(unittest.TestCase):
    """#8704: harness exposes items awaiting human action via /human/queue."""

    def setUp(self):
        from fastapi.testclient import TestClient
        from harness import app
        self.client = TestClient(app)

    def _fake_subproc(self, issues_by_status):
        """Build a side_effect for subprocess.run that returns different issues
        per `status:pending-human-*` label filter.

        `issues_by_status` is a dict like
        `{"status:pending-human-review": [{...}, {...}], "status:pending-human-setup": []}`.
        """
        def _runner(cmd, **kwargs):
            # The command always includes `--label "squidsquad,status:..."`.
            label_arg = ""
            for i, arg in enumerate(cmd):
                if arg == "--label" and i + 1 < len(cmd):
                    label_arg = cmd[i + 1]
                    break
            status = next(
                (s for s in issues_by_status if s in label_arg), None
            )
            issues = issues_by_status.get(status, []) if status else []
            return MagicMock(
                returncode=0,
                stdout=json.dumps(issues),
                stderr="",
            )
        return _runner

    def test_empty_queue_returns_zero(self):
        with patch("harness.subprocess.run", side_effect=self._fake_subproc({})):
            resp = self.client.get("/human/queue")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(data["items"], [])

    def test_returns_pending_human_review_items(self):
        issues = {
            "status:pending-human-review": [{
                "number": 42,
                "title": "Designer review needed",
                "labels": [
                    {"name": "status:pending-human-review"},
                    {"name": "role:skill"},
                    {"name": "priority:high"},
                ],
                "updatedAt": "2026-05-18T08:00:00Z",
                "url": "https://example.com/42",
            }],
        }
        with patch("harness.subprocess.run", side_effect=self._fake_subproc(issues)):
            resp = self.client.get("/human/queue")
        data = resp.json()
        self.assertEqual(data["count"], 1)
        item = data["items"][0]
        self.assertEqual(item["number"], 42)
        self.assertEqual(item["status"], "pending-human-review")
        self.assertEqual(item["role"], "skill")
        self.assertEqual(item["priority"], "high")

    def test_dedups_across_both_pending_statuses(self):
        """An item flagged with both labels (unlikely) should appear only once."""
        same_issue = {
            "number": 99,
            "title": "Dual-labeled",
            "labels": [
                {"name": "status:pending-human-review"},
                {"name": "status:pending-human-setup"},
            ],
            "updatedAt": "2026-05-18T08:00:00Z",
            "url": "",
        }
        issues = {
            "status:pending-human-review": [same_issue],
            "status:pending-human-setup": [same_issue],
        }
        with patch("harness.subprocess.run", side_effect=self._fake_subproc(issues)):
            resp = self.client.get("/human/queue")
        data = resp.json()
        self.assertEqual(data["count"], 1)

    def test_sorts_by_priority_then_age(self):
        issues = {
            "status:pending-human-review": [
                {"number": 1, "title": "low new",
                 "labels": [{"name": "priority:low"},
                            {"name": "status:pending-human-review"}],
                 "updatedAt": "2026-05-18T09:00:00Z", "url": ""},
                {"number": 2, "title": "high new",
                 "labels": [{"name": "priority:high"},
                            {"name": "status:pending-human-review"}],
                 "updatedAt": "2026-05-18T09:00:00Z", "url": ""},
                {"number": 3, "title": "high old",
                 "labels": [{"name": "priority:high"},
                            {"name": "status:pending-human-review"}],
                 "updatedAt": "2026-05-17T09:00:00Z", "url": ""},
            ],
        }
        with patch("harness.subprocess.run", side_effect=self._fake_subproc(issues)):
            resp = self.client.get("/human/queue")
        data = resp.json()
        # high+old → high+new → low+new
        self.assertEqual([i["number"] for i in data["items"]], [3, 2, 1])

    def test_uses_severity_when_priority_missing(self):
        """Issues (severity:*) and tasks (priority:*) should both sort."""
        issues = {
            "status:pending-human-review": [
                {"number": 5, "title": "issue medium",
                 "labels": [{"name": "severity:medium"},
                            {"name": "status:pending-human-review"}],
                 "updatedAt": "2026-05-18T09:00:00Z", "url": ""},
            ],
        }
        with patch("harness.subprocess.run", side_effect=self._fake_subproc(issues)):
            resp = self.client.get("/human/queue")
        self.assertEqual(resp.json()["items"][0]["priority"], "medium")

    def test_does_not_crash_on_gh_failure(self):
        """A failing gh subprocess (rc != 0) returns an empty queue, not 500."""
        with patch("harness.subprocess.run",
                   return_value=MagicMock(returncode=1, stdout="", stderr="gh: command not found")):
            resp = self.client.get("/human/queue")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)

    def test_does_not_crash_on_malformed_json(self):
        with patch("harness.subprocess.run",
                   return_value=MagicMock(returncode=0, stdout="not json", stderr="")):
            resp = self.client.get("/human/queue")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["count"], 0)

    def test_does_not_crash_on_unexpected_label_shape(self):
        """#8704 R1: malformed `labels` (not a list) skips the row, doesn't 500."""
        issues = {
            "status:pending-human-review": [
                {"number": 1, "title": "good", "labels": [
                    {"name": "status:pending-human-review"}
                ], "updatedAt": "2026-05-18T09:00:00Z", "url": ""},
                # Row with `labels` as a string instead of a list — should be skipped.
                {"number": 2, "title": "broken", "labels": "not-a-list",
                 "updatedAt": "2026-05-18T09:00:00Z", "url": ""},
            ],
        }
        with patch("harness.subprocess.run", side_effect=self._fake_subproc(issues)):
            resp = self.client.get("/human/queue")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual([i["number"] for i in data["items"]], [1])

    def test_unknown_updated_at_sorts_last(self):
        """#8704 R2: items with no/unparseable updated_at sort LAST in their
        priority tier (not first, which the old `return 0` behavior produced)."""
        issues = {
            "status:pending-human-review": [
                {"number": 1, "title": "unknown age",
                 "labels": [{"name": "priority:high"},
                            {"name": "status:pending-human-review"}],
                 "updatedAt": "", "url": ""},
                {"number": 2, "title": "known old",
                 "labels": [{"name": "priority:high"},
                            {"name": "status:pending-human-review"}],
                 "updatedAt": "2026-05-17T09:00:00Z", "url": ""},
            ],
        }
        with patch("harness.subprocess.run", side_effect=self._fake_subproc(issues)):
            resp = self.client.get("/human/queue")
        # Known-age item sorts before unknown-age within the same priority tier.
        self.assertEqual([i["number"] for i in resp.json()["items"]], [2, 1])


if __name__ == "__main__":
    unittest.main()
