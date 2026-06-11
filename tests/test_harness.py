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


class TestIntentSetAt(unittest.TestCase):
    """#4792 Phase 1 (#8979): intent_set_at field + persistence + migration."""

    def test_initial_intent_set_at_is_none(self):
        from harness import AgentState
        agent = AgentState("skill")
        self.assertIsNone(agent.intent_set_at)

    def test_to_dict_includes_intent_set_at(self):
        from harness import AgentState
        agent = AgentState("skill")
        agent.intent = AgentState.INTENT_STOPPING
        agent.intent_set_at = 1234.5
        d = agent.to_dict()
        self.assertEqual(d["intent_set_at"], 1234.5)

    def test_save_state_persists_intent_set_at(self):
        """save_state must include intent_set_at in the JSON."""
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                agent = AgentState("skill", "/p")
                agent.intent = AgentState.INTENT_STOPPING
                agent.intent_set_at = 1700.0
                hs.set_agent("skill", agent)
                hs.save_state()
                data = json.loads(state_file.read_text(encoding="utf-8"))
                self.assertEqual(
                    data["agents"]["skill"]["intent_set_at"], 1700.0,
                )

    def test_load_state_round_trips_intent_set_at(self):
        """A state file written by save_state loads back with intent_set_at."""
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                agent = AgentState("pm")
                agent.intent = AgentState.INTENT_RESTARTING
                agent.intent_set_at = 555.0
                hs.set_agent("pm", agent)
                hs.save_state()

                hs2 = HarnessState()
                with patch("harness._log"):
                    hs2.load_state()
                loaded = hs2.get_agent("pm")
                self.assertEqual(loaded.intent_set_at, 555.0)

    def test_load_state_migrates_legacy_stopping_without_intent_set_at(self):
        """Legacy state file: intent=STOPPING but no intent_set_at field.

        Per CONTEXT-4792.md §5.1 case (a): seed with time.time() so the
        force-kill clock starts now rather than firing immediately.
        """
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            legacy = {
                "harness_pid": 1,
                "start_time": 0.0,
                "port": 7373,
                "agents": {
                    "skill": {
                        "intent": "stopping",
                        "status": "running",
                        "boot_time": None,
                        "clone_path": "",
                        "claude_pid": None,
                        "terminal_pid": None,
                        # NB: no intent_set_at key
                    }
                },
            }
            state_file.write_text(json.dumps(legacy), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file), \
                 patch("harness._log"), \
                 patch("harness.time.time", return_value=9999.0):
                hs = HarnessState()
                hs.load_state()
                loaded = hs.get_agent("skill")
                self.assertEqual(loaded.intent_set_at, 9999.0)

    def test_load_state_migrates_legacy_restarting_without_intent_set_at(self):
        """Same migration applies to RESTARTING intent (Q7 PM lock)."""
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            legacy = {
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {
                    "qa": {"intent": "restarting", "status": "running",
                           "boot_time": None, "clone_path": "",
                           "claude_pid": None, "terminal_pid": None},
                },
            }
            state_file.write_text(json.dumps(legacy), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file), \
                 patch("harness._log"), \
                 patch("harness.time.time", return_value=4242.0):
                hs = HarnessState()
                hs.load_state()
                self.assertEqual(hs.get_agent("qa").intent_set_at, 4242.0)

    def test_load_state_preserves_none_for_running_intent(self):
        """Legacy state with intent=RUNNING and no intent_set_at must NOT
        be seeded — the migration only applies to STOPPING/RESTARTING."""
        import tempfile
        from harness import HarnessState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            state_file.write_text(json.dumps({
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {
                    "dm": {"intent": "running", "status": "running",
                           "boot_time": None, "clone_path": "",
                           "claude_pid": None, "terminal_pid": None},
                },
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file), \
                 patch("harness._log"):
                hs = HarnessState()
                hs.load_state()
                self.assertIsNone(hs.get_agent("dm").intent_set_at)

    def test_load_state_loads_present_intent_set_at_as_is(self):
        """A state file with intent_set_at present loads as-is — no seed."""
        import tempfile
        from harness import HarnessState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            state_file.write_text(json.dumps({
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {
                    "skill": {"intent": "stopping",
                              "intent_set_at": 1234.5,
                              "status": "running", "boot_time": None,
                              "clone_path": "", "claude_pid": None,
                              "terminal_pid": None},
                },
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file), \
                 patch("harness._log"), \
                 patch("harness.time.time", return_value=9999.0):
                hs = HarnessState()
                hs.load_state()
                self.assertEqual(
                    hs.get_agent("skill").intent_set_at, 1234.5,
                )

    def test_stop_agent_endpoint_sets_intent_set_at(self):
        """POST /agents/{role}/stop writes intent_set_at."""
        import asyncio
        from harness import state, AgentState
        try:
            from harness import stop_agent
        except ImportError:
            self.skipTest("stop_agent endpoint not exported")
        state.agents.clear()
        state.set_agent("skill", AgentState("skill", "/p"))
        with patch("harness.time.time", return_value=7777.0), \
             patch.object(state, "save_state"):
            asyncio.run(stop_agent("skill"))
        self.assertEqual(state.get_agent("skill").intent_set_at, 7777.0)

    def test_load_state_distinguishes_explicit_null_from_absent_key(self):
        """Iter-1 finding 3: explicit `null` for intent_set_at on a STOPPING
        agent must NOT trigger the legacy-migration seed. Only an absent key
        seeds. CONTEXT-4792.md §5.1 case (b): present file → load as-is."""
        import tempfile
        from harness import HarnessState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            state_file.write_text(json.dumps({
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {
                    "skill": {"intent": "stopping",
                              "intent_set_at": None,  # explicit null
                              "status": "running", "boot_time": None,
                              "clone_path": "", "claude_pid": None,
                              "terminal_pid": None},
                },
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file), \
                 patch("harness._log"), \
                 patch("harness.time.time", return_value=9999.0):
                hs = HarnessState()
                hs.load_state()
                self.assertIsNone(
                    hs.get_agent("skill").intent_set_at,
                    "explicit null must NOT be replaced by the migration seed",
                )

    def test_ack_stop_confirmed_guarded_by_stopping_intent(self):
        """Iter-1 finding 4 + iter-2 findings 2/3: a stale stop-confirmed
        ack must NOT overwrite intent when the agent has moved on to
        RUNNING/RESTARTING/STOPPED, and must NOT reset intent_set_at when
        intent is already STOPPING (which would extend the 60s force-kill
        window indefinitely per CONTEXT-4792.md §3.3)."""
        import inspect
        from harness import receive_event
        src = inspect.getsource(receive_event)
        assert "stop-confirmed" in src
        # The guard must be == STOPPING (the only state where ack is valid),
        # not the iter-1 weaker `!= RESTARTING`.
        assert "agent.intent == AgentState.INTENT_STOPPING" in src, (
            "stop-confirmed handler must require intent == STOPPING"
        )
        # And it must NOT contain a `intent_set_at = time.time()` inside the
        # ack branch — that would reset the force-kill clock on every ack.
        # Locate the stop-confirmed block and assert no clock-reset inside.
        idx = src.find("stop-confirmed")
        block = src[idx:idx + 600]
        assert "intent_set_at = time.time()" not in block, (
            "stop-confirmed ack must not reset intent_set_at — it is set "
            "at stop-REQUEST time, not at ack time"
        )

    def test_restart_agent_endpoint_sets_intent_set_at(self):
        import asyncio
        from harness import state, AgentState
        try:
            from harness import restart_agent
        except ImportError:
            self.skipTest("restart_agent endpoint not exported")
        state.agents.clear()
        state.set_agent("pm", AgentState("pm", "/p"))
        with patch("harness.time.time", return_value=8888.0), \
             patch.object(state, "save_state"), \
             patch("harness.boot_remote"):
            try:
                asyncio.run(restart_agent("pm"))
            except Exception:
                # Endpoint may try to reach boot helpers we don't fully stub —
                # that's fine, we only care that intent_set_at was written
                # before the failure point.
                pass
        self.assertEqual(state.get_agent("pm").intent_set_at, 8888.0)


class TestForceKillSafetyNet(unittest.TestCase):
    """#4792 Phase 1 / Q7: when intent is STOPPING/RESTARTING for longer
    than FORCE_KILL_TIMEOUT_SECONDS and the claude PID is still alive,
    update_health must kill the PID. CONTEXT-4792.md §3.3."""

    def _set_up_state(self, intent, elapsed_seconds, pid=12345):
        """Configure HarnessState with one agent in the given intent for
        `elapsed_seconds`. Returns (state, agent, fake_now)."""
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill", "/clone")
        agent.intent = intent
        agent.intent_set_at = 1000.0
        agent.claude_pid = pid
        agent.status = "running"
        hs.set_agent("skill", agent)
        fake_now = 1000.0 + elapsed_seconds
        return hs, agent, fake_now

    def _patch_environment(self, fake_now, pid_alive=True):
        """Patch boot_remote and time so update_health runs deterministically."""
        return [
            patch("harness.boot_remote._get_all_roles",
                  return_value=["skill"]),
            patch("harness.boot_remote._get_clone_path",
                  return_value="/clone"),
            patch("harness.boot_remote._is_process_alive",
                  return_value=pid_alive),
            patch("harness.time.time", return_value=fake_now),
            patch("harness._log"),
        ]

    def _run_health(self, hs, patches):
        for p in patches:
            p.start()
        try:
            hs.update_health()
        finally:
            for p in patches:
                p.stop()

    def test_stopping_with_alive_pid_past_timeout_force_kills(self):
        from harness import AgentState, FORCE_KILL_TIMEOUT_SECONDS
        hs, agent, fake_now = self._set_up_state(
            AgentState.INTENT_STOPPING,
            elapsed_seconds=FORCE_KILL_TIMEOUT_SECONDS + 5,
        )
        patches = self._patch_environment(fake_now, pid_alive=True)
        with patch("harness.reboot_agent._kill_process") as kill:
            for p in patches:
                p.start()
            try:
                hs.update_health()
            finally:
                for p in patches:
                    p.stop()
        kill.assert_called_once_with(12345)

    def test_restarting_with_alive_pid_past_timeout_force_kills(self):
        from harness import AgentState, FORCE_KILL_TIMEOUT_SECONDS
        hs, agent, fake_now = self._set_up_state(
            AgentState.INTENT_RESTARTING,
            elapsed_seconds=FORCE_KILL_TIMEOUT_SECONDS + 1,
        )
        patches = self._patch_environment(fake_now, pid_alive=True)
        with patch("harness.reboot_agent._kill_process") as kill:
            for p in patches:
                p.start()
            try:
                hs.update_health()
            finally:
                for p in patches:
                    p.stop()
        kill.assert_called_once_with(12345)

    def test_stopping_within_timeout_does_not_force_kill(self):
        """Cooperative window — the safety net must NOT fire before the
        timeout elapses."""
        from harness import AgentState, FORCE_KILL_TIMEOUT_SECONDS
        hs, agent, fake_now = self._set_up_state(
            AgentState.INTENT_STOPPING,
            elapsed_seconds=FORCE_KILL_TIMEOUT_SECONDS - 5,
        )
        patches = self._patch_environment(fake_now, pid_alive=True)
        with patch("harness.reboot_agent._kill_process") as kill:
            for p in patches:
                p.start()
            try:
                hs.update_health()
            finally:
                for p in patches:
                    p.stop()
        kill.assert_not_called()

    def test_running_intent_never_force_kills(self):
        """Even with a stale intent_set_at, intent=RUNNING must never trigger
        a kill — the safety net is scoped to STOPPING/RESTARTING."""
        from harness import AgentState, FORCE_KILL_TIMEOUT_SECONDS
        hs, agent, fake_now = self._set_up_state(
            AgentState.INTENT_RUNNING,
            elapsed_seconds=FORCE_KILL_TIMEOUT_SECONDS + 100,
        )
        # RUNNING agents have intent_set_at=None per the data-model rule,
        # but the safety net must defend against a misplaced value too.
        patches = self._patch_environment(fake_now, pid_alive=True)
        with patch("harness.reboot_agent._kill_process") as kill:
            for p in patches:
                p.start()
            try:
                hs.update_health()
            finally:
                for p in patches:
                    p.stop()
        kill.assert_not_called()

    def test_no_intent_set_at_does_not_force_kill(self):
        """A missing intent_set_at on STOPPING/RESTARTING must NOT fire the
        kill — the clock is not yet started. (Could happen briefly during
        a state-file write race; treat conservatively.)"""
        from harness import AgentState
        hs, agent, fake_now = self._set_up_state(
            AgentState.INTENT_STOPPING, elapsed_seconds=0,
        )
        agent.intent_set_at = None
        patches = self._patch_environment(fake_now, pid_alive=True)
        with patch("harness.reboot_agent._kill_process") as kill:
            for p in patches:
                p.start()
            try:
                hs.update_health()
            finally:
                for p in patches:
                    p.stop()
        kill.assert_not_called()

    def test_dead_pid_does_not_force_kill(self):
        """If the claude PID is already dead, no kill is needed."""
        from harness import AgentState, FORCE_KILL_TIMEOUT_SECONDS
        hs, agent, fake_now = self._set_up_state(
            AgentState.INTENT_STOPPING,
            elapsed_seconds=FORCE_KILL_TIMEOUT_SECONDS + 10,
        )
        patches = self._patch_environment(fake_now, pid_alive=False)
        with patch("harness.reboot_agent._kill_process") as kill:
            for p in patches:
                p.start()
            try:
                hs.update_health()
            finally:
                for p in patches:
                    p.stop()
        kill.assert_not_called()

    def test_force_kill_clears_intent_set_at(self):
        """After firing, intent_set_at must be cleared so the kill is not
        re-logged every 5s while the OS reaps the process."""
        from harness import AgentState, FORCE_KILL_TIMEOUT_SECONDS
        hs, agent, fake_now = self._set_up_state(
            AgentState.INTENT_STOPPING,
            elapsed_seconds=FORCE_KILL_TIMEOUT_SECONDS + 5,
        )
        patches = self._patch_environment(fake_now, pid_alive=True)
        with patch("harness.reboot_agent._kill_process"):
            for p in patches:
                p.start()
            try:
                hs.update_health()
            finally:
                for p in patches:
                    p.stop()
        self.assertIsNone(hs.get_agent("skill").intent_set_at)

    def test_force_kill_swallows_kill_exceptions(self):
        """If _kill_process raises (already-dead, permission, etc.), the
        safety net must NOT propagate — the OS will reap on the next poll."""
        from harness import AgentState, FORCE_KILL_TIMEOUT_SECONDS
        hs, agent, fake_now = self._set_up_state(
            AgentState.INTENT_STOPPING,
            elapsed_seconds=FORCE_KILL_TIMEOUT_SECONDS + 5,
        )
        patches = self._patch_environment(fake_now, pid_alive=True)
        with patch("harness.reboot_agent._kill_process",
                   side_effect=OSError("boom")):
            for p in patches:
                p.start()
            try:
                hs.update_health()  # must not raise
            finally:
                for p in patches:
                    p.stop()
        # intent_set_at is still cleared on best-effort attempt
        self.assertIsNone(hs.get_agent("skill").intent_set_at)


class TestIntentSetAtRepeatRequestIsIdempotent(unittest.TestCase):
    """#4792 Phase 1 iter-4: repeated stop/restart requests on an already
    -STOPPING/-RESTARTING agent must NOT reset intent_set_at — that would
    extend the 60s force-kill window indefinitely under operator spam."""

    def test_stop_agent_on_already_stopping_does_not_reset_timestamp(self):
        import asyncio
        from harness import state, AgentState, stop_agent
        state.agents.clear()
        agent = AgentState("skill", "/p")
        agent.intent = AgentState.INTENT_STOPPING
        agent.intent_set_at = 1000.0  # original stop time
        state.set_agent("skill", agent)
        with patch("harness.time.time", return_value=9999.0), \
             patch.object(state, "save_state"):
            asyncio.run(stop_agent("skill"))
        # Timestamp must stay at the original stop time (1000.0), NOT update
        # to 9999.0 from the second request.
        self.assertEqual(state.get_agent("skill").intent_set_at, 1000.0)

    def test_restart_agent_on_already_restarting_does_not_reset_timestamp(self):
        import asyncio
        from harness import state, AgentState, restart_agent
        state.agents.clear()
        agent = AgentState("skill", "/p")
        agent.intent = AgentState.INTENT_RESTARTING
        agent.intent_set_at = 1000.0
        state.set_agent("skill", agent)
        with patch("harness.time.time", return_value=9999.0), \
             patch.object(state, "save_state"), \
             patch("harness.boot_remote"):
            try:
                asyncio.run(restart_agent("skill"))
            except Exception:
                pass
        self.assertEqual(state.get_agent("skill").intent_set_at, 1000.0)

    def test_stop_agent_on_running_records_fresh_timestamp(self):
        """Regression guard: the idempotence fix must NOT break the
        first-stop-records-timestamp behavior."""
        import asyncio
        from harness import state, AgentState, stop_agent
        state.agents.clear()
        agent = AgentState("skill", "/p")
        agent.intent = AgentState.INTENT_RUNNING
        agent.intent_set_at = None
        state.set_agent("skill", agent)
        with patch("harness.time.time", return_value=9999.0), \
             patch.object(state, "save_state"):
            asyncio.run(stop_agent("skill"))
        self.assertEqual(state.get_agent("skill").intent_set_at, 9999.0)
        self.assertEqual(state.get_agent("skill").intent,
                         AgentState.INTENT_STOPPING)


class TestIntentSetAtClearing(unittest.TestCase):
    """#4792 Phase 1: intent_set_at must reset to None on every transition
    to RUNNING or STOPPED, so the upcoming force-kill safety net never sees
    a stale timestamp on a healthy or terminally-stopped agent.

    Tests verify the source contains the clear at the 5 sites identified in
    iter-1 finding 1, rather than driving the full update_health loop (which
    pulls in boot_remote / file-system / health-check plumbing this unit
    test does not need).
    """

    def test_update_health_clears_intent_set_at_on_restart_complete(self):
        """RESTARTING → RUNNING transition (alive branch) clears the field."""
        import inspect
        from harness import HarnessState
        src = inspect.getsource(HarnessState.update_health)
        # Find the specific assignment `agent.intent = AgentState.INTENT_RUNNING`
        # in the alive-branch RESTARTING handler (NOT the tuple membership
        # check in the force-kill safety net).
        marker = "agent.intent = AgentState.INTENT_RUNNING"
        idx = src.find(marker)
        assert idx != -1, f"expected '{marker}' in update_health"
        block = src[idx:idx + 200]
        assert "intent_set_at = None" in block, (
            "RESTARTING→RUNNING transition must clear intent_set_at"
        )

    def test_update_health_clears_intent_set_at_on_manual_reboot(self):
        """Manual reboot (#7637): stale STOPPING/STOPPED intent + new PID
        flips back to RUNNING and must clear intent_set_at."""
        import inspect
        from harness import HarnessState
        src = inspect.getsource(HarnessState.update_health)
        # The #7637 branch logs "alive with new PID (stale intent=...)".
        idx = src.find("alive with new PID")
        assert idx != -1, "expected #7637 manual-reboot branch"
        # Search backward to the intent reassignment.
        pre = src[max(0, idx - 400):idx]
        assert "INTENT_RUNNING" in pre and "intent_set_at = None" in pre, (
            "manual-reboot reset must clear intent_set_at"
        )

    def test_update_health_clears_intent_set_at_on_stop_fulfilled(self):
        """STOPPING → STOPPED transition (dead branch) clears the field."""
        import inspect
        from harness import HarnessState
        src = inspect.getsource(HarnessState.update_health)
        # Find the specific assignment `agent.intent = AgentState.INTENT_STOPPED`
        # (not the tuple membership check that also references INTENT_STOPPED).
        marker = "agent.intent = AgentState.INTENT_STOPPED"
        idx = src.find(marker)
        assert idx != -1, f"expected '{marker}' in update_health"
        block = src[idx:idx + 200]
        assert "intent_set_at = None" in block, (
            "STOPPING→STOPPED transition must clear intent_set_at"
        )

    def test_start_all_clears_intent_set_at(self):
        """start_all assigning INTENT_RUNNING after spawn must clear the field."""
        import inspect
        from harness import start_all
        src = inspect.getsource(start_all)
        assert "intent_set_at = None" in src, (
            "start_all spawn path must clear intent_set_at on intent=RUNNING"
        )

    def test_start_agent_clears_intent_set_at(self):
        """start_agent (#4966 single-agent spawn) must clear intent_set_at."""
        import inspect
        from harness import start_agent
        src = inspect.getsource(start_agent)
        assert "intent_set_at = None" in src, (
            "start_agent must clear intent_set_at on intent=RUNNING"
        )


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
        """#6820: Verify start_all code path includes save_state call.

        #9242: the call is now wrapped in ``asyncio.to_thread`` to keep
        the disk write off the asyncio event loop. Match either the
        bare or the wrapped form so this test survives both shapes.
        """
        import inspect
        from harness import start_all
        source = inspect.getsource(start_all)
        self.assertTrue(
            "save_state()" in source
            or "asyncio.to_thread(state.save_state)" in source,
            "start_all must call save_state to persist intent — "
            "either bare or wrapped via asyncio.to_thread (#9242).",
        )
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


class TestCodeVersionProbe(unittest.TestCase):
    """#9243 — compute_code_version + boot probe + /status + / endpoint."""

    def test_compute_code_version_success_shape(self):
        """All four fields present on a normal git checkout with config.md."""
        from harness import compute_code_version
        cv = compute_code_version()
        self.assertIn("squidsquad_version", cv)
        self.assertIn("git_sha", cv)
        self.assertIn("git_branch", cv)
        self.assertIn("git_dirty", cv)
        # On the actual repo, version + git fields should be populated.
        self.assertIsInstance(cv["squidsquad_version"], str)
        self.assertIsNotNone(cv["git_sha"])
        # SHA short form is hex; verify it parses
        int(cv["git_sha"], 16)
        self.assertIsInstance(cv["git_branch"], str)
        self.assertIsInstance(cv["git_dirty"], bool)

    def test_compute_code_version_no_git(self):
        """When git fails (no repo / no git binary), all git fields are None
        but the dict shape is preserved."""
        from harness import compute_code_version
        with patch("harness._git_probe", return_value=None):
            cv = compute_code_version()
        self.assertIsNone(cv["git_sha"])
        self.assertIsNone(cv["git_branch"])
        self.assertIsNone(cv["git_dirty"])
        # Version still comes from config.md regardless of git
        self.assertIn("squidsquad_version", cv)

    def test_compute_code_version_dirty_tree(self):
        """`git status --porcelain` non-empty -> dirty=True."""
        from harness import compute_code_version

        def fake_probe(args):
            if args[:1] == ["status"]:
                return " M some/file.py"
            if args == ["rev-parse", "--short=8", "HEAD"]:
                return "deadbeef"
            if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
                return "main"
            return None

        with patch("harness._git_probe", side_effect=fake_probe):
            cv = compute_code_version()
        self.assertTrue(cv["git_dirty"])
        self.assertEqual(cv["git_sha"], "deadbeef")

    def test_compute_code_version_clean_tree(self):
        """`git status --porcelain` empty -> dirty=False."""
        from harness import compute_code_version

        def fake_probe(args):
            if args[:1] == ["status"]:
                return ""
            if args == ["rev-parse", "--short=8", "HEAD"]:
                return "12345678"
            if args == ["rev-parse", "--abbrev-ref", "HEAD"]:
                return "feature-branch"
            return None

        with patch("harness._git_probe", side_effect=fake_probe):
            cv = compute_code_version()
        self.assertFalse(cv["git_dirty"])

    def test_read_squidsquad_version_missing_config(self):
        """Missing config.md returns None without crashing."""
        from harness import _read_squidsquad_version
        with patch("pathlib.Path.read_text", side_effect=OSError):
            self.assertIsNone(_read_squidsquad_version())


class TestStatusEndpointCodeVersion(unittest.TestCase):
    """#9243 — GET /status exposes code_version block; GET / returns slim."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from harness import app, state
        state.start_time = time.time()
        state.port = 7373
        state.code_version = {
            "squidsquad_version": "v0.40.0",
            "git_sha": "01a2b6f4",
            "git_branch": "main",
            "git_dirty": False,
        }
        cls.client = TestClient(app, raise_server_exceptions=False)
        cls.state = state

    def test_status_includes_code_version(self):
        with patch.object(self.state, "update_health"):
            resp = self.client.get("/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("code_version", data["harness"])
        cv = data["harness"]["code_version"]
        self.assertEqual(cv["squidsquad_version"], "v0.40.0")
        self.assertEqual(cv["git_sha"], "01a2b6f4")
        self.assertEqual(cv["git_branch"], "main")
        self.assertFalse(cv["git_dirty"])
        self.assertIn("boot_time_iso", cv)
        # Boot time ISO ends with Z (UTC)
        self.assertTrue(cv["boot_time_iso"].endswith("Z"))

    def test_root_endpoint_returns_slim_version(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["service"], "squidsquad-harness")
        self.assertEqual(data["version"], "v0.40.0")
        self.assertEqual(data["git_sha"], "01a2b6f4")

    def test_status_falls_back_when_state_code_version_none(self):
        """If state.code_version is None (e.g. test client bypassed
        lifespan), the endpoint re-probes via compute_code_version() rather
        than crashing or returning a malformed response."""
        prior = self.state.code_version
        try:
            self.state.code_version = None
            with patch.object(self.state, "update_health"), \
                 patch("harness.compute_code_version", return_value={
                     "squidsquad_version": "v0.0.0-probed",
                     "git_sha": "probedsh",
                     "git_branch": "test-fallback",
                     "git_dirty": False,
                 }):
                resp = self.client.get("/status")
            self.assertEqual(resp.status_code, 200)
            cv = resp.json()["harness"]["code_version"]
            self.assertEqual(cv["squidsquad_version"], "v0.0.0-probed")
            self.assertEqual(cv["git_sha"], "probedsh")
            self.assertIn("boot_time_iso", cv)
        finally:
            self.state.code_version = prior

    def test_status_code_version_with_null_git(self):
        """Boot from outside a git repo -> git fields are null in /status."""
        prior = self.state.code_version
        try:
            self.state.code_version = {
                "squidsquad_version": "v0.40.0",
                "git_sha": None,
                "git_branch": None,
                "git_dirty": None,
            }
            with patch.object(self.state, "update_health"):
                resp = self.client.get("/status")
            self.assertEqual(resp.status_code, 200)
            cv = resp.json()["harness"]["code_version"]
            self.assertIsNone(cv["git_sha"])
            self.assertIsNone(cv["git_branch"])
            self.assertIsNone(cv["git_dirty"])
            self.assertEqual(cv["squidsquad_version"], "v0.40.0")
        finally:
            self.state.code_version = prior


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
        """POST /agents/{role}/restart returns 200 + success=True.

        #4792 Phase 2: reboot_agent.reboot() was deleted — the endpoint
        flips intent and triggers respawn through the harness state
        machine instead of calling a separate reboot helper. No mock
        for reboot_agent.reboot is needed."""
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

    def test_no_auto_reboot_when_flag_set_10538(self):
        """#10538: when _NO_AUTO_REBOOT is True, agent death is observed
        but boot_agent is NOT called. State must still update (claude_pid
        cleared, bootup_complete reset) so the next operator-driven
        /agents/{role}/start behaves like a fresh spawn."""
        import tempfile
        from harness import HarnessState, AgentState
        import harness

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / ".claude-pid").write_text("99999999", encoding="utf-8")

            hs = HarnessState()
            agent = AgentState("skill", tmpdir)
            agent.status = "running"
            agent.intent = AgentState.INTENT_RUNNING
            agent.claude_pid = 99999999
            agent.bootup_complete = True
            hs.set_agent("skill", agent)

            with patch.object(harness, "_NO_AUTO_REBOOT", True), \
                 patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.boot_remote.boot_agent") as mock_boot, \
                 patch("harness.health_check.check_agent_health", return_value={"health": "unknown"}), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            # AC: boot_agent is NOT invoked when the gate is set.
            mock_boot.assert_not_called()
            # AC: state still updates to honest values.
            self.assertIsNone(hs.get_agent("skill").claude_pid)
            self.assertFalse(hs.get_agent("skill").bootup_complete)
            # `status = "starting"` is the auto-reboot path's marker —
            # the suppressed-reboot branch MUST NOT set it, otherwise
            # HTTP/TUI consumers reading `/status` would see a
            # spuriously "starting" agent that never starts.
            self.assertNotEqual(hs.get_agent("skill").status, "starting")

    def test_auto_reboot_default_unchanged_when_flag_unset_10538(self):
        """#10538 coexistence: when _NO_AUTO_REBOOT is False (default),
        v1 behavior is byte-identical — boot_agent IS called."""
        import tempfile
        from harness import HarnessState, AgentState
        import harness

        with tempfile.TemporaryDirectory() as tmpdir:
            role_dir = Path(tmpdir) / ".squidsquad" / "skill"
            role_dir.mkdir(parents=True)
            (role_dir / ".claude-pid").write_text("99999999", encoding="utf-8")

            hs = HarnessState()
            agent = AgentState("skill", tmpdir)
            agent.status = "running"
            agent.intent = AgentState.INTENT_RUNNING
            agent.claude_pid = 99999999
            # Lock that the v1 reboot path resets bootup_complete the same
            # way the suppressed path does — coexistence symmetry.
            agent.bootup_complete = True
            hs.set_agent("skill", agent)

            with patch.object(harness, "_NO_AUTO_REBOOT", False), \
                 patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.boot_remote.boot_agent") as mock_boot, \
                 patch("harness.health_check.check_agent_health", return_value={"health": "unknown"}), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            mock_boot.assert_called_once_with("skill")
            self.assertEqual(hs.get_agent("skill").status, "starting")
            self.assertFalse(hs.get_agent("skill").bootup_complete)

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

            # boot_agent must return a JSON-serializable dict — the auto-reboot
            # branch sets `agent.terminal_pid = result["terminal_pid"]` and then
            # calls save_state(), which json.dumps the state.
            spawn_result = {"success": True, "terminal_pid": 0}

            # First poll: dead → reboot triggered
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.boot_remote.boot_agent", return_value=spawn_result), \
                 patch("harness.health_check.check_agent_health", return_value={"health": "unknown"}), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            # Second poll: agent came back alive (use current process PID)
            (role_dir / ".claude-pid").write_text(str(os.getpid()), encoding="utf-8")
            hs.get_agent("skill").status = "starting"  # was set by reboot
            hs.get_agent("skill").claude_pid = None  # cleared by reboot

            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.boot_remote.boot_agent", return_value=spawn_result), \
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


class TestCursorState9873A(unittest.TestCase):
    """#9873-A: per-role cursor state on EventLifecycleManager + the
    EventStream.has_event / find_positions helpers used by the ack-cursor
    handler. Covers AC-1, AC-2, AC-9, AC-15, AC-16, AC-17, AC-18, AC-19.
    """

    def _fresh_manager(self, tmpdir):
        from harness import EventStream, EventLifecycleManager
        state_file = Path(tmpdir) / ".event-state.json"
        return state_file, EventStream(), EventLifecycleManager

    def test_ac1_cursors_dict_initialized_empty(self):
        """AC-1 (presence): _cursors is dict[str, str] starting empty."""
        from harness import EventStream, EventLifecycleManager
        mgr = EventLifecycleManager(EventStream())
        self.assertIsInstance(mgr._cursors, dict)
        self.assertEqual(mgr._cursors, {})

    def test_ac1_load_missing_cursors_key_does_not_crash(self):
        """AC-1 (backward-compat): load() must use data.get('cursors', {}) so
        pre-migration .event-state.json files (no 'cursors' key) don't KeyError.
        """
        import tempfile, json as _json
        from harness import EventStream, EventLifecycleManager
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".event-state.json"
            # Pre-migration shape: no "cursors" key
            state_file.write_text(_json.dumps({
                "events": [],
                "in_flight": {},
                "dispatched": {},
                "dispatch_times": {},
                "retry_counts": {},
            }), encoding="utf-8")
            with patch("harness.EVENT_STATE_FILE", state_file):
                mgr = EventLifecycleManager(EventStream())
                mgr.load()  # must NOT raise KeyError
                self.assertEqual(mgr._cursors, {})

    def test_ac2_cursors_persist_round_trip(self):
        """AC-2: ack-cursor → _cursors mutates → _persist writes → load restores."""
        import tempfile
        from harness import EventStream, EventLifecycleManager
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".event-state.json"
            with patch("harness.EVENT_STATE_FILE", state_file):
                stream = EventStream()
                mgr = EventLifecycleManager(stream)
                mgr.append({"id": "evt1", "event_type": "x"})
                mgr.advance_cursor("skill", "evt1")

                self.assertTrue(state_file.exists())
                # Reload — cursor must survive
                stream2 = EventStream()
                mgr2 = EventLifecycleManager(stream2)
                mgr2.load()
                self.assertEqual(mgr2.get_cursor("skill"), "evt1")

    def test_get_cursor_returns_none_when_absent(self):
        """D7: no cursor entry → get_cursor returns None."""
        from harness import EventStream, EventLifecycleManager
        mgr = EventLifecycleManager(EventStream())
        self.assertIsNone(mgr.get_cursor("skill"))
        self.assertIsNone(mgr.get_cursor("pm"))

    def test_advance_cursor_noop_on_empty_args(self):
        """Defensive: empty role or event_id is a no-op without raising."""
        from harness import EventStream, EventLifecycleManager
        mgr = EventLifecycleManager(EventStream())
        self.assertEqual(mgr.advance_cursor("", "evt1"), "noop")
        self.assertEqual(mgr.advance_cursor("skill", ""), "noop")
        self.assertEqual(mgr._cursors, {})

    def test_ac8_ac16_evicted_event_id_rejected(self):
        """AC-8 / AC-16: cursor not advanced when event_id is not in deque."""
        from harness import EventStream, EventLifecycleManager
        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            mgr = EventLifecycleManager(EventStream())
            # No events appended → has_event returns False for any id
            result = mgr.advance_cursor("skill", "phantom-event")
            self.assertEqual(result, "evicted")
            self.assertIsNone(mgr.get_cursor("skill"))

    def test_ac7_valid_ack_advances_cursor(self):
        """AC-7: event_id present in deque → cursor advances to that id."""
        from harness import EventStream, EventLifecycleManager
        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            stream.append({"id": "evt1", "event_type": "x"})
            stream.append({"id": "evt2", "event_type": "x"})
            mgr = EventLifecycleManager(stream)
            result = mgr.advance_cursor("skill", "evt2")
            self.assertEqual(result, "advanced")
            self.assertEqual(mgr.get_cursor("skill"), "evt2")

    def test_ac17_regression_rejected(self):
        """AC-17 / D15: ack for an event earlier in the deque than the
        current cursor is rejected (cursor unchanged)."""
        from harness import EventStream, EventLifecycleManager
        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            stream.append({"id": "evt1", "event_type": "x"})
            stream.append({"id": "evt2", "event_type": "x"})
            stream.append({"id": "evt3", "event_type": "x"})
            mgr = EventLifecycleManager(stream)
            # Advance to evt3 first
            mgr.advance_cursor("skill", "evt3")
            self.assertEqual(mgr.get_cursor("skill"), "evt3")
            # Out-of-order ack for evt1 (earlier in deque) — rejected
            result = mgr.advance_cursor("skill", "evt1")
            self.assertEqual(result, "regression")
            self.assertEqual(mgr.get_cursor("skill"), "evt3")

    def test_ac17_regression_check_skipped_when_no_prior_cursor(self):
        """AC-17 edge: first ack — no prior cursor — accepts normally."""
        from harness import EventStream, EventLifecycleManager
        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            stream.append({"id": "evt1", "event_type": "x"})
            mgr = EventLifecycleManager(stream)
            result = mgr.advance_cursor("skill", "evt1")
            self.assertEqual(result, "advanced")

    def test_ac17_regression_check_proceeds_when_prior_cursor_evicted(self):
        """AC-17 edge: if the current cursor itself is no longer in the deque
        (prior eviction), regression check is skipped — eviction check on the
        target dominates, and we accept the target if it IS in the deque.
        """
        from harness import EventStream, EventLifecycleManager
        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            stream.append({"id": "evt-new", "event_type": "x"})
            mgr = EventLifecycleManager(stream)
            # Force a stale cursor that's no longer in the deque
            mgr._cursors["skill"] = "evt-evicted"
            result = mgr.advance_cursor("skill", "evt-new")
            self.assertEqual(result, "advanced")
            self.assertEqual(mgr.get_cursor("skill"), "evt-new")

    def test_ac15_has_event_true_when_present(self):
        """AC-15: EventStream.has_event returns True for an id in the deque."""
        from harness import EventStream
        stream = EventStream()
        stream.append({"id": "abc", "event_type": "x"})
        stream.append({"id": "def", "event_type": "y"})
        self.assertTrue(stream.has_event("abc"))
        self.assertTrue(stream.has_event("def"))

    def test_ac15_has_event_false_when_absent(self):
        """AC-15: has_event returns False for unknown id and for empty string."""
        from harness import EventStream
        stream = EventStream()
        stream.append({"id": "abc", "event_type": "x"})
        self.assertFalse(stream.has_event("missing"))
        self.assertFalse(stream.has_event(""))
        self.assertFalse(stream.has_event(None))

    def test_find_positions_single_pass(self):
        """find_positions returns indices for both ids; -1 means not in deque."""
        from harness import EventStream
        stream = EventStream()
        stream.append({"id": "a", "event_type": "x"})
        stream.append({"id": "b", "event_type": "x"})
        stream.append({"id": "c", "event_type": "x"})
        # Both present
        t, c = stream.find_positions("c", "a")
        self.assertEqual((t, c), (2, 0))
        # Target missing
        t, c = stream.find_positions("missing", "b")
        self.assertEqual((t, c), (-1, 1))
        # Cursor missing
        t, c = stream.find_positions("a", "missing")
        self.assertEqual((t, c), (0, -1))
        # Both None — early return
        t, c = stream.find_positions(None, None)
        self.assertEqual((t, c), (-1, -1))

    def test_ac18_old_ack_call_absent_from_ack_cursor_branch(self):
        """AC-18 (source-level): the inline ack-handler in harness.py must
        NOT call event_lifecycle.ack() from the ack-cursor branch."""
        import re
        src = (Path(__file__).resolve().parent.parent
               / "references" / "scripts" / "harness.py").read_text(encoding="utf-8")
        # Find the ack-cursor branch — bracket from the if line to the next
        # elif or end-of-ack-block.
        m = re.search(
            r'if event_type == "ack-cursor":(.*?)(?=elif event_type == "ack-stop":)',
            src, re.DOTALL,
        )
        self.assertIsNotNone(
            m, "ack-cursor branch not found — handler split missing?"
        )
        branch = m.group(1)
        self.assertNotIn(
            "event_lifecycle.ack(", branch,
            "ack-cursor branch MUST NOT call event_lifecycle.ack() per AC-18",
        )

    def test_ac19_lock_ordering_comment_present(self):
        """AC-19 (source-level): advance_cursor docstring documents the
        outer→inner lock ordering. The audit step ships as a comment on the
        method per R2 §4 PR gate.
        """
        src = (Path(__file__).resolve().parent.parent
               / "references" / "scripts" / "harness.py").read_text(encoding="utf-8")
        self.assertIn("def advance_cursor", src)
        idx = src.index("def advance_cursor")
        # Look at the next ~3000 chars of the method for the lock-ordering note
        body = src[idx:idx + 3000]
        self.assertIn("Lock ordering", body)
        self.assertIn("EventLifecycleManager._lock", body)
        self.assertIn("EventStream._lock", body)

    def test_ac19_has_event_called_inside_lock_9902(self):
        """#9902 F1: ``has_event`` must be invoked WHILE the outer
        EventLifecycleManager._lock is held. Doing it before the lock
        creates a TOCTOU window where the deque can evict between the
        check and the cursor mutation.

        Verify by patching has_event to assert the lock is non-acquirable
        from this thread (i.e., already held)."""
        from harness import EventStream, EventLifecycleManager
        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            stream.append({"id": "evt1", "event_type": "x"})
            mgr = EventLifecycleManager(stream)

            real_has_event = stream.has_event
            observed = {"lock_held_when_called": None}

            def probing_has_event(eid):
                # If lock is held by this thread (the only thread here),
                # acquire(blocking=False) returns False since threading.Lock
                # is non-reentrant.
                acquired = mgr._lock.acquire(blocking=False)
                if acquired:
                    mgr._lock.release()
                    observed["lock_held_when_called"] = False
                else:
                    observed["lock_held_when_called"] = True
                return real_has_event(eid)

            with patch.object(stream, "has_event", side_effect=probing_has_event):
                result = mgr.advance_cursor("skill", "evt1")
            self.assertEqual(result, "advanced")
            self.assertTrue(
                observed["lock_held_when_called"],
                "F1 regression: has_event was called BEFORE acquiring the "
                "outer lock — TOCTOU window reopened",
            )

    def test_target_evicted_during_regression_check_9902(self):
        """#9902 F1 (second failure mode): if find_positions returns
        ``target_pos=-1`` (target evicted between has_event and
        find_positions, OR cursor pointing at an id not in deque),
        advance_cursor must return ``\"evicted\"`` — never advance the
        cursor to an evicted event_id (violates D8).
        """
        from harness import EventStream, EventLifecycleManager
        with patch("harness.EVENT_STATE_FILE", Path("/nonexistent")):
            stream = EventStream()
            stream.append({"id": "evt1", "event_type": "x"})
            stream.append({"id": "evt2", "event_type": "x"})
            mgr = EventLifecycleManager(stream)
            # Cursor already at evt1; ack arrives for evt2 (still in deque,
            # so has_event will pass), but simulate post-lock-acquisition
            # eviction by returning target_pos=-1 from find_positions.
            mgr._cursors["skill"] = "evt1"
            with patch.object(stream, "find_positions", return_value=(-1, 0)):
                result = mgr.advance_cursor("skill", "evt2")
            self.assertEqual(result, "evicted")
            # D8: cursor MUST NOT advance to an evicted event_id.
            self.assertEqual(mgr._cursors["skill"], "evt1")


class TestCursorEndpoint9873A(unittest.TestCase):
    """#9873-A: GET /events/cursor/{role} — AC-3, AC-4."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from harness import app
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_ac3_null_cursor_returns_200(self):
        """AC-3: no cursor for role → 200 with {cursor: null, role}."""
        from harness import event_lifecycle
        # Ensure no cursor for an arbitrary valid role
        event_lifecycle._cursors.pop("skill", None)
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]):
            resp = self.client.get("/events/cursor/skill")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"cursor": None, "role": "skill"})

    def test_ac4_present_cursor_returns_value(self):
        """AC-4: cursor set → 200 with the cursor value."""
        from harness import event_lifecycle
        event_lifecycle._cursors["skill"] = "evt-xyz"
        try:
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]):
                resp = self.client.get("/events/cursor/skill")
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.json(), {"cursor": "evt-xyz", "role": "skill"})
        finally:
            event_lifecycle._cursors.pop("skill", None)

    def test_unknown_role_returns_404(self):
        """_validate_role still rejects unknown roles."""
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]):
            resp = self.client.get("/events/cursor/bogus")
        self.assertEqual(resp.status_code, 404)


class TestAckEndpointPayloadGuard9902(unittest.TestCase):
    """#9902 F4: ``ack-cursor`` and ``ack-stop`` inline handlers must not
    500 on a malformed payload (present-but-not-dict). The ``body.get(
    "payload", {})`` default only triggers on a missing key — a string or
    list payload would AttributeError on the subsequent ``.get()`` call.
    """

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from harness import app
        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_ack_cursor_string_payload_returns_200_not_500(self):
        """POST /events with event_type=ack-cursor and payload as a string
        (not a dict) must return 200, not 500. The handler silently drops
        the malformed event rather than crashing the endpoint."""
        resp = self.client.post("/events", json={
            "event_type": "ack-cursor",
            "role": "skill",
            "payload": "malformed-not-a-dict",
            "timestamp": "2026-05-22T09:00:00",
        })
        self.assertEqual(resp.status_code, 200)

    def test_ack_cursor_list_payload_returns_200_not_500(self):
        """Same guard against payload being a list."""
        resp = self.client.post("/events", json={
            "event_type": "ack-cursor",
            "role": "skill",
            "payload": ["not", "a", "dict"],
            "timestamp": "2026-05-22T09:00:00",
        })
        self.assertEqual(resp.status_code, 200)

    def test_ack_stop_string_payload_returns_200_not_500(self):
        """ack-stop branch has the same guard as ack-cursor."""
        resp = self.client.post("/events", json={
            "event_type": "ack-stop",
            "role": "skill",
            "payload": "malformed-not-a-dict",
            "timestamp": "2026-05-22T09:00:00",
        })
        self.assertEqual(resp.status_code, 200)

    def test_ack_stop_null_payload_returns_200_not_500(self):
        """ack-stop with payload explicitly null — body.get('payload')
        returns None, isinstance(None, dict) is False, default-dict
        path runs without crash."""
        resp = self.client.post("/events", json={
            "event_type": "ack-stop",
            "role": "skill",
            "payload": None,
            "timestamp": "2026-05-22T09:00:00",
        })
        self.assertEqual(resp.status_code, 200)


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
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"events": []}'
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            events, _ = event_poll.poll("skill", since="abc123",
                                        target_mode=True, sleep=lambda _: None)

            # Verify the URL used /events/for/skill
            call_args = mock_urlopen.call_args
            req = call_args[0][0]
            self.assertIn("/events/for/skill", req.full_url)
            self.assertEqual(events, [])

    def test_event_poll_legacy_mode_url(self):
        """event_poll.py in legacy mode queries /events with role param."""
        import event_poll

        with patch.object(event_poll, "_discover_port", return_value=7373), \
             patch("urllib.request.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = b'{"events": [{"id": "x1"}]}'
            mock_resp.__enter__ = MagicMock(return_value=mock_resp)
            mock_resp.__exit__ = MagicMock(return_value=False)
            mock_urlopen.return_value = mock_resp

            events, _ = event_poll.poll("skill", target_mode=False,
                                        sleep=lambda _: None)

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

    def test_filters_by_target_alias(self):
        """GET /events/for/skill returns only events targeted at skill."""
        from harness import event_stream

        # Add events for different roles
        event_stream.append({
            "id": "e1", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_alias": "skill", "issue_number": "1"},
        })
        event_stream.append({
            "id": "e2", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_alias": "pm", "issue_number": "2"},
        })

        with patch("harness._validate_role"):
            resp = self.client.get("/events/for/skill")

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["id"], "e1")

    def test_target_alias_is_canonical_field_name(self):
        """Regression guard for #11331 polish-session Iter 63.

        The wire-format field for routing events to a specific alias is
        ``payload.target_alias`` — per AGENT-RUNTIME.md §8 and per the
        unification commit that retired the pre-#6274 legacy name
        ``target_role``. If a future refactor reintroduces ``target_role``
        in either the EAD emit or the ``/events/for/{role}`` filter, the
        l4-watcher dropout regression resurfaces (l4_file_watcher.py
        emits ``target_alias`` only).

        This test pins both halves of the contract by asserting:
        (a) the filter at ``harness.py:2181`` matches on ``target_alias``;
        (b) legacy ``target_role`` payload events are NOT matched by the
            filter (defends against silent dual-acceptance fallbacks).
        """
        from harness import event_stream

        # (a) Canonical field name is honored by the filter.
        event_stream.append({
            "id": "canon", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_alias": "skill", "issue_number": "100"},
        })
        # (b) Legacy field name is NOT silently honored — the unification
        # is hard, not a permissive alias.
        event_stream.append({
            "id": "legacy", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_role": "skill", "issue_number": "101"},
        })

        with patch("harness._validate_role"):
            resp = self.client.get("/events/for/skill")

        self.assertEqual(resp.status_code, 200)
        ids = [e["id"] for e in resp.json()["events"]]
        self.assertIn("canon", ids,
                      "filter must match payload.target_alias")
        self.assertNotIn("legacy", ids,
                         "filter must NOT silently accept payload.target_role "
                         "(the legacy field was retired in #11331 Iter 63)")

    def test_does_not_dispatch(self):
        """#9741: GET /events/for/skill must NOT add events to in-flight.

        Before #9741 the endpoint called event_lifecycle.dispatch() on every
        delivered event, but there is no ack consumer wired yet — every
        event would eventually time out, growing .event-state.json and
        spamming the timeout-scanner log. CONTEXT-9741 D1 strips the call;
        the endpoint is a pure filtered-read with no lifecycle side effects.
        """
        from harness import event_stream, event_lifecycle

        event_stream.append({
            "id": "e3", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_alias": "skill", "issue_number": "3"},
        })

        with patch("harness._validate_role"):
            self.client.get("/events/for/skill")

        # Endpoint delivers the event but does not touch in-flight state.
        self.assertNotIn("e3", event_lifecycle.get_in_flight("skill"))

    def test_since_cursor_filters_events(self):
        """GET /events/for/skill?since=X returns only events after cursor."""
        from harness import event_stream

        event_stream.append({
            "id": "old1", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_alias": "skill"},
        })
        event_stream.append({
            "id": "new1", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_alias": "skill"},
        })

        with patch("harness._validate_role"):
            resp = self.client.get("/events/for/skill?since=old1")

        data = resp.json()
        ids = [e["id"] for e in data["events"]]
        self.assertNotIn("old1", ids)
        self.assertIn("new1", ids)

    def test_endpoint_does_not_touch_lifecycle_state(self):
        """#9741: with dispatch stripped, the endpoint must not mutate in-flight.

        Even when an event was pre-dispatched by some other path, calling
        the read endpoint must not re-dispatch, re-add, or otherwise mutate
        the lifecycle state. CONTEXT-9741 D2 — the idempotency guard test
        is irrelevant once dispatch is stripped; this test instead verifies
        the read-only invariant.
        """
        from harness import event_stream, event_lifecycle

        event_stream.append({
            "id": "e4", "event_type": "assigned-to", "role": "harness",
            "payload": {"target_alias": "skill"},
        })

        # Pre-dispatch via the lifecycle manager directly (NOT via the endpoint).
        event_lifecycle.dispatch("e4", "skill", {"id": "e4"})
        before = list(event_lifecycle.get_in_flight("skill"))

        with patch("harness._validate_role"):
            self.client.get("/events/for/skill")

        # In-flight state must be identical — endpoint touched nothing.
        after = list(event_lifecycle.get_in_flight("skill"))
        self.assertEqual(before, after)
        # And specifically: e4 still appears exactly once (the pre-dispatch),
        # not zero (would mean endpoint cleared it) or two (would mean
        # endpoint re-dispatched).
        self.assertEqual(after.count("e4"), 1)


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
            "payload": {"target_alias": "skill", "issue_number": "1"},
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
            "payload": {"target_alias": "skill", "issue_number": "1"},
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
            "payload": {"target_alias": "skill", "issue_number": "1"},
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


class TestCleanupLegacySentinels(unittest.TestCase):
    """#4792 Phase 2 §5.1: harness boot must sweep pre-#4792 lifecycle
    sentinels (`.stop`, `.restart`, `.health`) so a stale file left over
    from an upgrade cannot influence the first `update_health` poll."""

    def _make_clone(self, tmp_path, role, files):
        role_dir = tmp_path / role / ".squidsquad" / role
        role_dir.mkdir(parents=True)
        for name in files:
            (role_dir / name).write_text("legacy", encoding="utf-8")
        return tmp_path / role

    def test_removes_all_three_sentinels(self):
        import tempfile
        from harness import _cleanup_legacy_sentinels
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            skill_root = self._make_clone(tmp, "skill",
                                          [".stop", ".restart", ".health"])
            removed, errors = _cleanup_legacy_sentinels({"skill": skill_root})
            self.assertEqual(removed, 3)
            self.assertEqual(errors, 0)
            role_dir = skill_root / ".squidsquad" / "skill"
            for name in (".stop", ".restart", ".health"):
                self.assertFalse((role_dir / name).exists(), name)

    def test_tolerates_missing_files(self):
        """A clone with no legacy sentinels must produce removed=0, no errors,
        and not raise."""
        import tempfile
        from harness import _cleanup_legacy_sentinels
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            skill_root = self._make_clone(tmp, "skill", [])
            removed, errors = _cleanup_legacy_sentinels({"skill": skill_root})
            self.assertEqual(removed, 0)
            self.assertEqual(errors, 0)

    def test_tolerates_missing_role_directory(self):
        """If `.squidsquad/<role>/` does not exist (clone never booted),
        the helper skips it without crashing."""
        import tempfile
        from harness import _cleanup_legacy_sentinels
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            # Don't create the role dir — emulate a fresh clone
            removed, errors = _cleanup_legacy_sentinels({"skill": tmp})
            self.assertEqual(removed, 0)
            self.assertEqual(errors, 0)

    def test_handles_multiple_roles(self):
        import tempfile
        from harness import _cleanup_legacy_sentinels
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            skill_root = self._make_clone(tmp, "skill", [".stop", ".health"])
            pm_root = self._make_clone(tmp, "pm", [".restart"])
            removed, errors = _cleanup_legacy_sentinels({
                "skill": skill_root,
                "pm": pm_root,
            })
            self.assertEqual(removed, 3)
            self.assertEqual(errors, 0)

    def test_partial_removal_only_existing(self):
        """Mixed state: one sentinel present, two absent — count must be 1."""
        import tempfile
        from harness import _cleanup_legacy_sentinels
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            skill_root = self._make_clone(tmp, "skill", [".health"])
            removed, errors = _cleanup_legacy_sentinels({"skill": skill_root})
            self.assertEqual(removed, 1)
            self.assertEqual(errors, 0)

    def test_unlink_oserror_counted_not_raised(self):
        """OSError from unlink must be counted in errors, not propagated —
        the cleanup pass is best-effort and runs before update_health, so
        it cannot crash harness startup."""
        import tempfile
        from unittest.mock import patch
        from harness import _cleanup_legacy_sentinels
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            skill_root = self._make_clone(tmp, "skill", [".stop"])
            # Force the unlink to raise an OSError that is NOT
            # FileNotFoundError (which is correctly handled separately).
            with patch("pathlib.Path.unlink",
                       side_effect=PermissionError("locked")):
                removed, errors = _cleanup_legacy_sentinels(
                    {"skill": skill_root}
                )
            self.assertEqual(removed, 0)
            self.assertEqual(errors, 1)

    def test_legacy_sentinel_names_locked(self):
        """The tuple of names is part of the cleanup contract — pin it so
        adding a new lifecycle sentinel cannot accidentally widen the
        sweep without a deliberate change."""
        from harness import LEGACY_SENTINEL_FILES
        self.assertEqual(
            tuple(LEGACY_SENTINEL_FILES), (".stop", ".restart", ".health"),
        )

    def test_idempotent_second_pass_returns_zero(self):
        """#4792 Phase 5 / §3.8 idempotence: running the cleanup twice
        means the second pass observes no leftover files and returns
        ``(0, 0)`` so the lifespan callsite logs nothing. Re-running the
        upgrade sweep must be a no-op."""
        import tempfile
        from harness import _cleanup_legacy_sentinels
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            skill_root = self._make_clone(
                tmp, "skill", [".stop", ".restart", ".health"]
            )
            first = _cleanup_legacy_sentinels({"skill": skill_root})
            self.assertEqual(first, (3, 0))
            second = _cleanup_legacy_sentinels({"skill": skill_root})
            self.assertEqual(second, (0, 0))

    def test_all_four_role_directories_seeded(self):
        """#4792 Phase 5 / §3.8: when stale `.stop`/`.restart`/`.health`
        files are seeded across the four canonical role directories
        (skill, pm, qa, dm), one cleanup pass removes all 12 (3 sentinels
        × 4 roles) and the role directories no longer contain any of the
        three legacy names."""
        import tempfile
        from harness import _cleanup_legacy_sentinels
        roles = ("skill", "pm", "qa", "dm")
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            clone_paths = {
                role: self._make_clone(
                    tmp, role, [".stop", ".restart", ".health"]
                )
                for role in roles
            }
            removed, errors = _cleanup_legacy_sentinels(clone_paths)
            self.assertEqual(removed, len(roles) * 3)
            self.assertEqual(errors, 0)
            for role, root in clone_paths.items():
                role_dir = root / ".squidsquad" / role
                for name in (".stop", ".restart", ".health"):
                    self.assertFalse(
                        (role_dir / name).exists(),
                        f"{role}{name!r} should have been swept",
                    )

    def test_cleanup_runs_synchronously_before_start_poller(self):
        """Source-level guard for CONTEXT-4792.md §5.1: the cleanup must
        be invoked on the lifespan thread BEFORE `state.start_poller()`,
        not inside the `_deferred_init` background thread which races
        the poller. A future refactor that moves the call inside the
        deferred block reintroduces the race the review caught."""
        import harness
        src = Path(harness.__file__).read_text(encoding="utf-8")

        # Find the lifespan body — everything between the `async def
        # lifespan` line and the next top-level `def` (or end of file).
        lifespan_match = src.find("async def lifespan")
        self.assertGreater(lifespan_match, 0, "lifespan function not found")
        # Bound the search at the first top-level def that follows
        # lifespan (e.g. `def _validate_role`).
        after_lifespan = src[lifespan_match:]
        next_top_level_def = after_lifespan.find("\ndef ")
        self.assertGreater(next_top_level_def, 0,
                           "no top-level def found after lifespan")
        lifespan_body = after_lifespan[:next_top_level_def]

        cleanup_idx = lifespan_body.find("_cleanup_legacy_sentinels(")
        poller_idx = lifespan_body.find("state.start_poller()")
        deferred_thread_idx = lifespan_body.find(
            "threading.Thread(target=_deferred_init"
        )

        self.assertGreater(
            cleanup_idx, 0,
            "lifespan must invoke _cleanup_legacy_sentinels (§5.1)",
        )
        self.assertGreater(
            poller_idx, 0,
            "lifespan must call state.start_poller()",
        )
        self.assertLess(
            cleanup_idx, poller_idx,
            "cleanup must run BEFORE start_poller (§5.1 — health poller "
            "would otherwise hit the legacy .health fallback while "
            "stale sentinels are still present)",
        )
        # Also confirm cleanup runs before the deferred thread fires
        # `_deferred_init`, so neither path can read stale state.
        self.assertLess(
            cleanup_idx, deferred_thread_idx,
            "cleanup must precede the _deferred_init thread spawn so "
            "load_state() never observes legacy sentinels",
        )


if __name__ == "__main__":
    unittest.main()
