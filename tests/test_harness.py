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
from unittest.mock import MagicMock, call, patch

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
        """A state file written by save_state loads back with intent_set_at.

        Uses STOPPING — a STOPPING intent (and its force-kill clock) must
        survive a harness restart so an operator stop is not lost. (RESTARTING
        is intentionally NOT round-tripped — see
        test_load_state_resets_restarting_to_running, #12244 P0.)
        """
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                agent = AgentState("pm")
                agent.intent = AgentState.INTENT_STOPPING
                agent.intent_set_at = 555.0
                hs.set_agent("pm", agent)
                hs.save_state()

                hs2 = HarnessState()
                with patch("harness._log"):
                    hs2.load_state()
                loaded = hs2.get_agent("pm")
                self.assertEqual(loaded.intent, AgentState.INTENT_STOPPING)
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

    def test_load_state_resets_legacy_restarting_to_running(self):
        """#12244 P0: a restored RESTARTING intent (legacy file, no
        intent_set_at key) is reset to RUNNING with intent_set_at cleared —
        NOT seeded. RESTARTING is a transient in-flight state that must not
        survive a harness restart (it would force-kill a healthy agent)."""
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
                self.assertEqual(
                    hs.get_agent("qa").intent, AgentState.INTENT_RUNNING)
                self.assertIsNone(hs.get_agent("qa").intent_set_at)

    def test_load_state_resets_restarting_to_running(self):
        """#12244 P0: a restored RESTARTING intent WITH a present (stale)
        intent_set_at is reset to RUNNING and the force-kill clock cleared.
        This is the core fix for the operator-reported 'working agent killed +
        respawned' loop: without it, the stale timestamp (< now -
        FORCE_KILL_TIMEOUT) makes the first health poll force-kill a healthy
        agent that outlived the harness restart, then respawn it."""
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            state_file.write_text(json.dumps({
                "harness_pid": 1, "start_time": 0.0, "port": 7373,
                "agents": {
                    "skill": {"intent": "restarting",
                              "intent_set_at": 100.0,  # stale, pre-restart
                              "status": "running", "boot_time": None,
                              "clone_path": "", "claude_pid": 4321,
                              "terminal_pid": None},
                },
            }), encoding="utf-8")
            with patch("harness.HARNESS_STATE_FILE", state_file), \
                 patch("harness._log"), \
                 patch("harness.time.time", return_value=9999.0):
                hs = HarnessState()
                hs.load_state()
                loaded = hs.get_agent("skill")
                self.assertEqual(loaded.intent, AgentState.INTENT_RUNNING)
                self.assertIsNone(loaded.intent_set_at)

    def test_load_state_preserves_none_for_running_intent(self):
        """Legacy state with intent=RUNNING and no intent_set_at must NOT
        be seeded — the migration only applies to STOPPING (RESTARTING is
        reset to RUNNING before the seeding path, #12244 P0)."""
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
        """Iter-1 finding 4 + iter-2 findings 2/3 (+ #13148): the stop-path
        ack-stop handler recognizes the SETTLED result enum
        ('checkpointed'/'aborted'/'drained' per AGENT-RUNTIME §10 Q11), not the
        obsolete 'stop-confirmed'. A stale stop ack must NOT overwrite intent
        when the agent has moved on to RUNNING/RESTARTING/STOPPED, and must NOT
        reset intent_set_at when intent is already STOPPING (which would extend
        the 60s force-kill window indefinitely per CONTEXT-4792.md §3.3)."""
        import inspect
        from harness import receive_event
        src = inspect.getsource(receive_event)
        # #13148: settled enum recognized (replaces obsolete "stop-confirmed").
        assert '"checkpointed"' in src and '"aborted"' in src and '"drained"' in src, (
            "stop-path ack-stop handler must recognize the settled enum "
            "(checkpointed/aborted/drained), not the obsolete 'stop-confirmed'"
        )
        # The guard must be == STOPPING (the only state where ack is valid),
        # not the iter-1 weaker `!= RESTARTING`.
        assert "agent.intent == AgentState.INTENT_STOPPING" in src, (
            "stop-path ack handler must require intent == STOPPING"
        )
        # And it must NOT contain a `intent_set_at = time.time()` inside the
        # ack branch — that would reset the force-kill clock on every ack.
        # Locate the stop-enum block and assert no clock-reset inside.
        idx = src.find("_stop_result in (")
        assert idx != -1, "expected the settled-enum membership check"
        block = src[idx:idx + 700]
        assert "intent_set_at = time.time()" not in block, (
            "stop ack must not reset intent_set_at — it is set "
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
            # #12294: update_health now resolves liveness via the image-verified
            # helper, so control that instead of the bare liveness check; pin
            # write-back to a no-op so the self-heal doesn't touch /clone.
            patch("harness.process_utils.is_claude_process_alive",
                  return_value=pid_alive),
            patch("harness.reboot_agent.write_claude_pid", return_value=True),
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


class TestCrashLoopBackoff(unittest.TestCase):
    """#12244 P2: repeated fast deaths back off (exponential, capped) instead
    of a tight respawn loop — protects against the Claude session/usage-limit
    exit-1 loop and any other fast-crash cause without parsing claude output."""

    def _make_dead_agent(self, last_spawn_at, fast_deaths=0, status="running",
                         reboot_blocked_until=None, claude_pid=12345):
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill", "/clone")
        agent.status = status
        agent.intent = AgentState.INTENT_RUNNING
        agent.claude_pid = claude_pid
        agent.last_spawn_at = last_spawn_at
        agent.consecutive_fast_deaths = fast_deaths
        agent.reboot_blocked_until = reboot_blocked_until
        hs.set_agent("skill", agent)
        return hs, agent

    def _run(self, hs, fake_now, pid_alive=False):
        """Run one update_health with the claude PID dead (unless pid_alive).
        Returns the boot_agent mock so callers can assert respawn vs backoff."""
        boot = patch("harness.boot_remote.boot_agent",
                     return_value={"success": True, "terminal_pid": 999,
                                   "action": "spawn"})
        patches = [
            patch("harness.boot_remote._get_all_roles", return_value=["skill"]),
            patch("harness.boot_remote._get_clone_path", return_value="/clone"),
            patch("harness.boot_remote._is_process_alive",
                  return_value=pid_alive),
            # #12294: image-verified liveness is the path update_health uses now.
            patch("harness.process_utils.is_claude_process_alive",
                  return_value=pid_alive),
            patch("harness.reboot_agent.write_claude_pid", return_value=True),
            patch("harness.reboot_agent._read_claude_pid",
                  return_value=(None, False)),
            patch("harness.time.time", return_value=fake_now),
            patch("harness._log"),
            patch.object(hs, "save_state"),
        ]
        boot_mock = boot.start()
        for p in patches:
            p.start()
        try:
            hs.update_health()
        finally:
            for p in patches:
                p.stop()
            boot.stop()
        return boot_mock

    def test_fast_death_below_threshold_still_reboots(self):
        """The first/second fast death reboots immediately — backoff only
        engages once the streak crosses the threshold."""
        from harness import FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, _ = self._make_dead_agent(last_spawn_at=now - 10, fast_deaths=0)
        boot = self._run(hs, now)
        boot.assert_called_once_with("skill")
        agent = hs.get_agent("skill")
        self.assertEqual(agent.consecutive_fast_deaths, 1)
        self.assertLess(1, FAST_DEATH_THRESHOLD)

    def test_streak_crossing_threshold_backs_off_instead_of_rebooting(self):
        """The Nth consecutive fast death (N == threshold) holds off the
        respawn, sets a backoff deadline, and surfaces 'crash-looping'."""
        from harness import (FAST_DEATH_THRESHOLD, CRASH_BACKOFF_BASE_SECONDS)
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - 10, fast_deaths=FAST_DEATH_THRESHOLD - 1)
        boot = self._run(hs, now)
        boot.assert_not_called()
        agent = hs.get_agent("skill")
        self.assertEqual(agent.consecutive_fast_deaths, FAST_DEATH_THRESHOLD)
        self.assertEqual(agent.status, "crash-looping")
        self.assertEqual(
            agent.reboot_blocked_until, now + CRASH_BACKOFF_BASE_SECONDS)

    def test_backoff_is_exponential_and_capped(self):
        """Deeper streaks back off exponentially up to the cap."""
        from harness import (FAST_DEATH_THRESHOLD, CRASH_BACKOFF_BASE_SECONDS,
                             CRASH_BACKOFF_CAP_SECONDS)
        now = 10_000.0
        # streak after this death = threshold + 2 → over=2 → base * 4
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - 5, fast_deaths=FAST_DEATH_THRESHOLD + 1)
        self._run(hs, now)
        agent = hs.get_agent("skill")
        expected = min(CRASH_BACKOFF_BASE_SECONDS * 4, CRASH_BACKOFF_CAP_SECONDS)
        self.assertEqual(agent.reboot_blocked_until, now + expected)

    def test_slow_death_resets_streak_and_reboots(self):
        """A death AFTER the window is a one-off, not a crash loop — the streak
        resets and the agent reboots immediately."""
        from harness import FAST_DEATH_WINDOW_SECONDS
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - (FAST_DEATH_WINDOW_SECONDS + 60),
            fast_deaths=5)
        boot = self._run(hs, now)
        boot.assert_called_once_with("skill")
        self.assertEqual(hs.get_agent("skill").consecutive_fast_deaths, 0)

    def test_backoff_resumes_after_window_elapses(self):
        """A crash-looping agent whose backoff deadline has passed retries the
        respawn (streak preserved so a still-failing agent backs off longer)."""
        from harness import FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - 500, fast_deaths=FAST_DEATH_THRESHOLD,
            status="crash-looping", reboot_blocked_until=now - 1,
            claude_pid=None)
        boot = self._run(hs, now)
        boot.assert_called_once_with("skill")
        agent = hs.get_agent("skill")
        self.assertIsNone(agent.reboot_blocked_until)
        self.assertEqual(agent.status, "starting")
        # streak is NOT reset by a resume — only a surviving spawn resets it
        self.assertEqual(agent.consecutive_fast_deaths, FAST_DEATH_THRESHOLD)

    def test_backoff_does_not_resume_before_window(self):
        """Before the deadline, a crash-looping agent stays paused (no respawn,
        status preserved, not relabelled 'unknown')."""
        from harness import FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - 500, fast_deaths=FAST_DEATH_THRESHOLD,
            status="crash-looping", reboot_blocked_until=now + 120,
            claude_pid=None)
        boot = self._run(hs, now)
        boot.assert_not_called()
        self.assertEqual(hs.get_agent("skill").status, "crash-looping")

    def test_recovered_agent_clears_streak(self):
        """An agent that has been alive past the window clears its streak so a
        later isolated death reboots immediately."""
        from harness import FAST_DEATH_WINDOW_SECONDS, FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - (FAST_DEATH_WINDOW_SECONDS + 30),
            fast_deaths=FAST_DEATH_THRESHOLD, status="crash-looping",
            claude_pid=777)
        # pid_alive=True → the agent is alive again and has survived the window
        self._run(hs, now, pid_alive=True)
        agent = hs.get_agent("skill")
        self.assertEqual(agent.consecutive_fast_deaths, 0)
        self.assertIsNone(agent.reboot_blocked_until)
        self.assertEqual(agent.status, "running")

    def test_crash_looping_agent_can_still_be_stopped(self):
        """#12244 P2 (DS-review finding 1): an operator stop must win over a
        backoff. A crash-looping agent whose intent flips to STOPPING settles to
        stopped/STOPPED instead of wedging forever (is_dead and the resume
        branch never fire for STOPPING)."""
        from harness import AgentState, FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, agent = self._make_dead_agent(
            last_spawn_at=now - 500, fast_deaths=FAST_DEATH_THRESHOLD,
            status="crash-looping", reboot_blocked_until=now + 120,
            claude_pid=None)
        agent.intent = AgentState.INTENT_STOPPING
        boot = self._run(hs, now)
        boot.assert_not_called()
        settled = hs.get_agent("skill")
        self.assertEqual(settled.intent, AgentState.INTENT_STOPPED)
        self.assertEqual(settled.status, "stopped")
        self.assertIsNone(settled.reboot_blocked_until)

    def test_new_fields_round_trip_through_state_file(self):
        """to_dict + load_state persist the P2 fields across a harness restart."""
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".harness-state.json"
            with patch("harness.HARNESS_STATE_FILE", state_file):
                hs = HarnessState()
                agent = AgentState("skill", "/p")
                agent.last_spawn_at = 123.0
                agent.consecutive_fast_deaths = 4
                agent.reboot_blocked_until = 456.0
                hs.set_agent("skill", agent)
                hs.save_state()

                hs2 = HarnessState()
                with patch("harness._log"):
                    hs2.load_state()
                loaded = hs2.get_agent("skill")
                self.assertEqual(loaded.last_spawn_at, 123.0)
                self.assertEqual(loaded.consecutive_fast_deaths, 4)
                self.assertEqual(loaded.reboot_blocked_until, 456.0)

    # --- #12418 AC4: SessionEnd graceful-vs-crash refinement ---

    def _set_session_end(self, hs, at, reason="other", role="skill"):
        hs.get_agent(role).last_session_end = {"reason": reason, "at": at}

    def test_graceful_exit_not_counted_toward_streak(self):
        """#12418 AC4: a GRACEFUL exit (SessionEnd stamped AFTER last_spawn) at
        threshold-minus-one must NOT trip the crash-loop breaker — it does not
        increment the streak, so it respawns immediately instead of backing off."""
        from harness import FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - 10, fast_deaths=FAST_DEATH_THRESHOLD - 1)
        self._set_session_end(hs, at=now - 5)  # after spawn (now-10) → graceful
        boot = self._run(hs, now)
        boot.assert_called_once_with("skill")  # respawned, NOT backed off
        agent = hs.get_agent("skill")
        # Not-incremented (DS-C F2: NOT reset to 0 — so accumulated real crashes
        # aren't zeroable by a SessionEnd-spammer); stays below threshold.
        self.assertEqual(agent.consecutive_fast_deaths, FAST_DEATH_THRESHOLD - 1)
        self.assertNotEqual(agent.status, "crash-looping")

    def test_graceful_does_not_reset_accumulated_crashes(self):
        """DS-REVIEW-12418-C F2 guard: a graceful death must NOT zero an
        accumulated streak — otherwise a SessionEnd-spammer could escape the
        breaker. After a graceful death at streak N, the very next CRASH
        increments to N+1 and (if that crosses the threshold) backs off."""
        from harness import FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - 10, fast_deaths=FAST_DEATH_THRESHOLD - 1)
        self._set_session_end(hs, at=now - 5)  # graceful
        self._run(hs, now)  # respawn; streak still THRESHOLD-1
        agent = hs.get_agent("skill")
        # Now a real crash (no fresh SessionEnd — the spawn cleared it) crosses
        # the threshold → backoff. (The reboot loop re-stamped last_spawn_at to
        # `now`; advance the clock so the next death is still "fast".)
        agent.status = "running"
        agent.claude_pid = 12345
        boot2 = self._run(hs, now + 5)
        boot2.assert_not_called()
        self.assertEqual(hs.get_agent("skill").status, "crash-looping")

    def test_sessionend_at_none_does_not_crash(self):
        """DS-REVIEW-12418-C F1: a {"at": null} entry (from a corrupt/hand-edited
        state file) must NOT raise TypeError in the graceful check — it is
        treated as a crash and update_health completes normally."""
        from harness import FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - 10, fast_deaths=FAST_DEATH_THRESHOLD - 1)
        hs.get_agent("skill").last_session_end = {"reason": "x", "at": None}
        boot = self._run(hs, now)  # must not raise
        boot.assert_not_called()  # treated as crash → backoff
        self.assertEqual(hs.get_agent("skill").status, "crash-looping")

    def test_crash_no_sessionend_still_backs_off(self):
        """No SessionEnd (a real crash — the hook couldn't run) at
        threshold-minus-one still trips the breaker. The graceful path must not
        weaken crash protection (AC6 — PID path unchanged for crashes)."""
        from harness import FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - 10, fast_deaths=FAST_DEATH_THRESHOLD - 1)
        # last_session_end stays None (crash).
        boot = self._run(hs, now)
        boot.assert_not_called()
        self.assertEqual(hs.get_agent("skill").status, "crash-looping")

    def test_stale_sessionend_treated_as_crash(self):
        """A SessionEnd from a PRIOR spawn (at < last_spawn_at) is NOT graceful
        for the current death — the >= last_spawn_at guard treats it as a crash
        and still backs off."""
        from harness import FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs, _ = self._make_dead_agent(
            last_spawn_at=now - 10, fast_deaths=FAST_DEATH_THRESHOLD - 1)
        self._set_session_end(hs, at=now - 50)  # BEFORE last_spawn_at → stale
        boot = self._run(hs, now)
        boot.assert_not_called()
        self.assertEqual(hs.get_agent("skill").status, "crash-looping")


class TestRestartLifecycle(unittest.TestCase):
    """#11538: update_health must not undo an in-flight RESTARTING intent.

    Regression for the bug where a restart of a still-alive (incl. wedged /
    non-cycling) agent was silently reverted within one health poll
    (HEALTH_POLL_INTERVAL=5s) — the RESTARTING->RUNNING reset fired whenever the
    SAME claude PID was merely alive, with no pid_changed guard. That also
    disarmed the 60s force-kill safety net (scoped to STOPPING/RESTARTING), so a
    wedged agent could never be restarted OR force-killed via the endpoint. The
    reset must now wait for a genuinely NEW claude PID (pid_changed) — proof the
    old process died and the agent rebooted.
    """

    def _make_state(self, intent, intent_set_at, stored_pid=12345):
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill", "/clone")
        agent.intent = intent
        agent.intent_set_at = intent_set_at
        agent.claude_pid = stored_pid
        agent.status = "running"
        hs.set_agent("skill", agent)
        return hs, agent

    def _run_health(self, hs, *, fake_now, stored_pid_alive, read_pid_return):
        """Drive one update_health poll with deterministic PID detection.

        stored_pid_alive: boot_remote._is_process_alive result for the
            currently-stored claude_pid.
        read_pid_return: (pid, alive) tuple from reboot_agent._read_claude_pid,
            consulted only when the stored PID is not alive (mirrors
            update_health's fall-through). A NEW pid here simulates a reboot
            (pid_changed=True).
        """
        kill = MagicMock()
        # #12294: update_health resolves liveness via the image-verified helper
        # for BOTH the stored PID and the .claude-pid file PID. Mirror the old
        # two-source semantics with a per-PID side_effect: the stored PID's
        # liveness is `stored_pid_alive`; the file PID's is `read_pid_return`'s
        # alive flag. Write-back is pinned to a no-op (it would touch /clone).
        stored_pid = hs.get_agent("skill").claude_pid
        file_pid, file_alive = read_pid_return

        def _claude_alive(pid):
            if stored_pid is not None and pid == stored_pid:
                return stored_pid_alive
            if file_pid is not None and pid == file_pid:
                return file_alive
            return False

        patches = [
            patch("harness.boot_remote._get_all_roles", return_value=["skill"]),
            patch("harness.boot_remote._get_clone_path", return_value="/clone"),
            patch("harness.boot_remote._is_process_alive",
                  return_value=stored_pid_alive),
            patch("harness.process_utils.is_claude_process_alive",
                  side_effect=_claude_alive),
            patch("harness.reboot_agent.write_claude_pid", return_value=True),
            patch("harness.reboot_agent._read_claude_pid",
                  return_value=read_pid_return),
            patch("harness.reboot_agent._kill_process", kill),
            patch("harness.time.time", return_value=fake_now),
            patch("harness._log"),
        ]
        for p in patches:
            p.start()
        try:
            hs.update_health()
        finally:
            for p in patches:
                p.stop()
        return kill

    def test_restarting_same_pid_alive_does_not_reset_intent(self):
        """THE BUG: a RESTARTING agent whose same claude PID is still alive
        must KEEP intent=RESTARTING (not silently revert to RUNNING). 10s
        elapsed mirrors a real /status poll well inside the 60s window."""
        from harness import AgentState
        hs, _ = self._make_state(AgentState.INTENT_RESTARTING, 1000.0)
        kill = self._run_health(
            hs, fake_now=1010.0, stored_pid_alive=True,
            read_pid_return=(None, False),
        )
        got = hs.get_agent("skill")
        self.assertEqual(got.intent, AgentState.INTENT_RESTARTING)
        self.assertEqual(got.intent_set_at, 1000.0)
        kill.assert_not_called()

    def test_restarting_new_pid_resets_to_running(self):
        """Restart COMPLETED: old PID dead, a new claude PID booted. The
        RESTARTING intent clears to RUNNING and intent_set_at resets. (This
        happy path was preserved — passes on both old and new code.)"""
        from harness import AgentState
        hs, _ = self._make_state(AgentState.INTENT_RESTARTING, 1000.0,
                                 stored_pid=12345)
        kill = self._run_health(
            hs, fake_now=1010.0, stored_pid_alive=False,
            read_pid_return=(99999, True),
        )
        got = hs.get_agent("skill")
        self.assertEqual(got.intent, AgentState.INTENT_RUNNING)
        self.assertIsNone(got.intent_set_at)
        self.assertEqual(got.claude_pid, 99999)
        kill.assert_not_called()

    def test_wedged_restarting_agent_force_killed_after_timeout(self):
        """The payoff: because intent now PERSISTS as RESTARTING, the 60s
        force-kill net finally engages for a wedged/non-cycling agent whose
        same PID never reaches a cooperative cycle boundary. Old code reset
        intent to RUNNING in the same poll, so this assertion would fail."""
        from harness import AgentState, FORCE_KILL_TIMEOUT_SECONDS
        hs, _ = self._make_state(AgentState.INTENT_RESTARTING, 1000.0)
        kill = self._run_health(
            hs, fake_now=1000.0 + FORCE_KILL_TIMEOUT_SECONDS + 1,
            stored_pid_alive=True, read_pid_return=(None, False),
        )
        kill.assert_called_once_with(12345)
        got = hs.get_agent("skill")
        # Intent stays RESTARTING (no new PID yet); next poll sees the dead PID
        # and runs the reboot path. intent_set_at cleared so the kill is not
        # re-logged every poll.
        self.assertEqual(got.intent, AgentState.INTENT_RESTARTING)
        self.assertIsNone(got.intent_set_at)

    def test_new_pid_not_force_killed_even_past_timeout(self):
        """A restart that took >60s end-to-end must NOT have its freshly-booted
        replacement force-killed: pid_changed proves the old process already
        died, so the stale intent_set_at clock does not apply to the new PID."""
        from harness import AgentState, FORCE_KILL_TIMEOUT_SECONDS
        hs, _ = self._make_state(AgentState.INTENT_RESTARTING, 1000.0,
                                 stored_pid=12345)
        kill = self._run_health(
            hs, fake_now=1000.0 + FORCE_KILL_TIMEOUT_SECONDS + 60,
            stored_pid_alive=False, read_pid_return=(99999, True),
        )
        kill.assert_not_called()
        got = hs.get_agent("skill")
        self.assertEqual(got.intent, AgentState.INTENT_RUNNING)
        self.assertIsNone(got.intent_set_at)
        self.assertEqual(got.claude_pid, 99999)


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

    def test_find_free_port_zero_returns_real_port(self):
        """#12820: find_free_port(0) returns the OS-assigned ephemeral port,
        not the literal 0 — so a --port 0 caller can advertise the real port."""
        from harness import find_free_port
        port = find_free_port(0)
        self.assertNotEqual(port, 0)
        self.assertGreater(port, 0)


class TestSingletonPortGuard(unittest.TestCase):
    """#12820: production harness must acquire the canonical port or refuse —
    never bind an ephemeral port (which would poison clone .harness-port files).
    """

    def _serve(self, body: bytes):
        """Spin a throwaway HTTP server returning ``body`` for GET /status.
        Returns (port, shutdown_callable). Lets HTTPServer bind an OS-assigned
        ephemeral port itself (no probe-then-rebind gap) and reads the actual
        port back from server_address — avoids a TOCTOU race on the port."""
        import http.server
        import threading

        class _Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):  # silence test noise
                pass

        httpd = http.server.HTTPServer(("127.0.0.1", 0), _Handler)
        port = httpd.server_address[1]
        t = threading.Thread(target=httpd.serve_forever, daemon=True)
        t.start()
        return port, httpd.shutdown

    def test_probe_no_server(self):
        """No listener on the port → not a live harness."""
        from harness import _probe_harness_status, find_free_port
        dead_port = find_free_port(0)  # found free, nothing bound to it now
        self.assertFalse(_probe_harness_status(dead_port, timeout=1.0))

    def test_probe_live_harness(self):
        """A server returning harness-shaped /status JSON → live harness."""
        from harness import _probe_harness_status
        port, shutdown = self._serve(b'{"harness": {"status": "running"}, "agents": []}')
        try:
            self.assertTrue(_probe_harness_status(port, timeout=2.0))
        finally:
            shutdown()

    def test_probe_non_harness_200(self):
        """A 200 from an unrelated server lacking the 'harness' key → not ours."""
        from harness import _probe_harness_status
        port, shutdown = self._serve(b'{"hello": "world"}')
        try:
            self.assertFalse(_probe_harness_status(port, timeout=2.0))
        finally:
            shutdown()

    def test_resolve_explicit_port_zero_is_ephemeral(self):
        """--port 0 takes the explicit path and yields a real ephemeral port."""
        from harness import _resolve_listen_port
        port = _resolve_listen_port(0)
        self.assertGreater(port, 0)

    def test_resolve_explicit_specific_free_port(self):
        """An explicit free --port is returned unchanged (no probe, no refuse)."""
        from harness import _resolve_listen_port, find_free_port
        free = find_free_port(0)
        self.assertEqual(_resolve_listen_port(free), free)

    def test_resolve_production_free_claims_canonical(self):
        """Production path (no --port): canonical port free → claim it."""
        import harness
        with patch.object(harness, "_read_config_port", return_value=59321), \
             patch.object(harness, "_probe_harness_status", return_value=False):
            self.assertEqual(harness._resolve_listen_port(None), 59321)

    def test_resolve_production_live_harness_refuses(self):
        """Production path: a live harness on the canonical port → refuse (exit 1),
        never falls back to an ephemeral port that would poison clones."""
        import harness
        with patch.object(harness, "_read_config_port", return_value=59322), \
             patch.object(harness, "_probe_harness_status", return_value=True):
            with self.assertRaises(SystemExit) as ctx:
                harness._resolve_listen_port(None)
            self.assertEqual(ctx.exception.code, 1)


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


class TestCursorLag12801(unittest.TestCase):
    """#12801: per-agent cursor `lag` (events-behind-head) for the TUI
    cursor-lag bar — EventLifecycleManager.lag_for + GET /status injection."""

    def _mgr_with_events(self, ids):
        from harness import EventStream, EventLifecycleManager
        stream = EventStream()
        mgr = EventLifecycleManager(stream)
        for i in ids:
            stream.append({"id": i, "event_type": "x"})
        return mgr

    def test_empty_deque_lag_zero(self):
        from harness import EventStream, EventLifecycleManager
        mgr = EventLifecycleManager(EventStream())
        self.assertEqual(mgr.lag_for("skill"), 0)

    def test_cursor_at_head_lag_zero(self):
        mgr = self._mgr_with_events(["e1", "e2", "e3"])
        mgr._cursors["skill"] = "e3"  # head = caught up
        self.assertEqual(mgr.lag_for("skill"), 0)

    def test_cursor_n_behind(self):
        mgr = self._mgr_with_events(["e1", "e2", "e3", "e4"])
        mgr._cursors["skill"] = "e2"  # 2 events newer (e3, e4)
        self.assertEqual(mgr.lag_for("skill"), 2)

    def test_no_cursor_reads_full_depth(self):
        """A role that has never acked reads as fully behind."""
        mgr = self._mgr_with_events(["e1", "e2", "e3"])
        self.assertEqual(mgr.lag_for("skill"), 3)

    def test_evicted_cursor_reads_full_depth(self):
        """A cursor that predates the retained deque reads as fully behind."""
        mgr = self._mgr_with_events(["e1", "e2", "e3"])
        mgr._cursors["skill"] = "GONE"  # not in deque
        self.assertEqual(mgr.lag_for("skill"), 3)

    def test_status_endpoint_injects_lag_per_agent(self):
        from fastapi.testclient import TestClient
        from harness import app, state, event_lifecycle
        state.start_time = time.time()
        state.port = 7373
        with patch.object(state, "all_agents",
                          return_value=[{"role": "skill"}, {"role": "pm"}]), \
             patch.object(state, "update_health"), \
             patch.object(event_lifecycle, "lag_for",
                          side_effect=lambda r: {"skill": 4, "pm": 0}[r]):
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/status")
        self.assertEqual(resp.status_code, 200)
        agents = {a["role"]: a for a in resp.json()["agents"]}
        self.assertEqual(agents["skill"]["lag"], 4)
        self.assertEqual(agents["pm"]["lag"], 0)


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
            # #12294: the test PID is this python process, not a claude.exe, so
            # image verification would (correctly) reject it. Stub the
            # image-verified check to True so the .claude-pid PID is adopted.
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.process_utils.is_claude_process_alive", return_value=True), \
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

    def setUp(self):
        # #12825 DS-F2: /shutdown and /restart share a single-winner teardown
        # guard whose flag the real process clears by exiting. Tests reuse the
        # process (and the flag can leak in from other test files), so reset it.
        import harness
        harness._teardown_in_progress = False

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

    def test_post_events_assigns_id_when_missing(self):
        """#11404 AC1: POST /events with no `id` auto-assigns a 16-hex id so
        id-tracking consumers (event_poll) can't silently skip the event."""
        from harness import event_lifecycle
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch.object(event_lifecycle, "append") as mock_append:
            resp = self.client.post("/events", json={
                "event_type": "status-transition", "role": "skill"})
        self.assertEqual(resp.status_code, 200)
        mock_append.assert_called_once()
        stored = mock_append.call_args[0][0]
        self.assertRegex(stored.get("id", ""), r"^[0-9a-f]{16}$")

    def test_post_events_preserves_provided_id(self):
        """A caller-provided id is not overwritten by the auto-assign."""
        from harness import event_lifecycle
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch.object(event_lifecycle, "append") as mock_append:
            resp = self.client.post("/events", json={
                "event_type": "status-transition", "role": "skill",
                "id": "caller-supplied-id"})
        self.assertEqual(resp.status_code, 200)
        stored = mock_append.call_args[0][0]
        self.assertEqual(stored["id"], "caller-supplied-id")

    def test_post_events_unknown_role_response_contract(self):
        """#11404 AC2: an unregistered emitter role is dropped with 204 (the
        INTENTIONAL fire-and-forget contract, #9242) and NOT stored."""
        from harness import event_lifecycle
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch.object(event_lifecycle, "append") as mock_append:
            resp = self.client.post("/events", json={
                "event_type": "status-transition", "role": "bogus-role-xyz"})
        self.assertEqual(resp.status_code, 204)
        mock_append.assert_not_called()

    def test_events_lifecycle_omits_in_flight(self):
        """#11165 AC5: GET /events/lifecycle no longer reports `in_flight`
        (dispatch in-flight tracking was deleted under pull-only)."""
        resp = self.client.get("/events/lifecycle")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertNotIn("in_flight", data)
        self.assertIn("stream_size", data)
        self.assertIn("persisted", data)

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
        """POST /shutdown returns 202 Accepted (non-blocking).

        #12720: the handler spawns a `shutdown` DAEMON thread that sleeps
        then calls ``os._exit(0)``. The ``patch("harness.os._exit")`` MUST
        outlive that thread. The pre-#12720 version reverted the patch the
        instant the POST returned 202 — but the daemon thread calls
        os._exit ~1s LATER, so the REAL ``os._exit(0)`` fired from the
        daemon thread, hard-killing the whole pytest process (exit 0, no
        summary, ``pytest.main()`` never returns). In a full ``pytest
        tests/`` run that surfaced as a false-green truncation at ~58%.

        Fix: patch ``os._exit`` + ``time.sleep`` (drop the 1s wait) and
        explicitly JOIN the `shutdown` thread inside the patch window so the
        mock — not the real exit — is what fires, then assert it was called.
        ``HARNESS_PORT_FILE`` is redirected to a non-existent tmp path so the
        thread's port-file unlink can never touch the live discovery file.
        """
        import tempfile
        import threading
        # #4792: removed `_has_stop_sentinel` patch — function deleted.
        fake_port_file = Path(tempfile.gettempdir()) / "sq-12720-nonexistent.harness-port"
        thread_found = False
        thread_alive_after_join = None
        # NOTE: time.sleep is deliberately NOT patched. The daemon thread does
        # time.sleep(1) before os._exit, so leaving the real sleep in place
        # guarantees the thread is still alive (sleeping) when we enumerate it
        # right after the POST — eliminating the race where a no-op sleep lets
        # the thread finish before we can find and join it (DS-c1 F4 follow-up).
        with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
             patch("harness.boot_remote._get_clone_path", return_value="/fake"), \
             patch("harness.HARNESS_PORT_FILE", fake_port_file), \
             patch("harness.os._exit") as mock_exit:  # Prevent actual exit
            resp = self.client.post("/shutdown")
            # The os._exit call happens in the `shutdown` daemon thread, not
            # synchronously. Join it INSIDE the patch context so the mocked
            # os._exit is what fires (else the real one kills the process).
            # CAPTURE state here but assert OUTSIDE the block: a failing assert
            # inside would revert the os._exit patch while the thread may still
            # be alive, letting the REAL os._exit(0) hard-kill pytest — the very
            # bug under test (DS-c1 F4).
            for t in threading.enumerate():
                if t.name == "shutdown":
                    thread_found = True
                    t.join(timeout=10)
                    thread_alive_after_join = t.is_alive()
                    break
            exit_call_count = mock_exit.call_count
            exit_call_args = mock_exit.call_args
        self.assertEqual(resp.status_code, 202)
        data = resp.json()
        self.assertEqual(data["status"], "shutting_down")
        # Assertions OUTSIDE the patch context — by here os._exit is the real
        # builtin again, but the daemon thread has already been joined dead.
        self.assertTrue(thread_found, "shutdown daemon thread was never spawned")
        self.assertFalse(
            thread_alive_after_join,
            "shutdown thread did not finish within join timeout — its os._exit "
            "would fire after the patch context exits (#12720 regression)")
        self.assertEqual(exit_call_count, 1, "os._exit not called exactly once")
        self.assertEqual(exit_call_args, call(0), "os._exit not called with 0")

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
                 patch("harness.process_utils.is_claude_process_alive", return_value=True), \
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

            # #12294: os.getpid() is python, not claude — stub image-verify True.
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.process_utils.is_claude_process_alive", return_value=True), \
                 patch("harness.reboot_agent.write_claude_pid", return_value=True), \
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

            # #12294: os.getpid() is python, not claude — stub image-verify True.
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.process_utils.is_claude_process_alive", return_value=True), \
                 patch("harness.reboot_agent.write_claude_pid", return_value=True), \
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

            # #12294: os.getpid() is python, not claude — stub image-verify True
            # so the same-PID-alive case is exercised (intent stays STOPPING).
            with patch("harness.boot_remote._get_all_roles", return_value=["skill"]), \
                 patch("harness.boot_remote._get_clone_path", return_value=tmpdir), \
                 patch("harness.process_utils.is_claude_process_alive", return_value=True), \
                 patch("harness.reboot_agent.write_claude_pid", return_value=True), \
                 patch("harness.HARNESS_STATE_FILE", Path(tmpdir) / ".harness-state.json"):
                hs.update_health()

            got = hs.get_agent("skill")
            self.assertEqual(got.status, "running")
            self.assertEqual(got.intent, AgentState.INTENT_STOPPING,
                             "Same PID still alive — stopping intent must NOT be cleared (#7637)")


class TestEventLifecycleManager(unittest.TestCase):
    """EventLifecycleManager disk persistence (#7630 P-1). The dispatch /
    in-flight tracking was deleted in #11165 (pull-only)."""

    def test_persist_and_load_round_trip(self):
        """Event state survives a harness restart (append → load)."""
        import tempfile
        from harness import EventStream, EventLifecycleManager

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".event-state.json"
            with patch("harness.EVENT_STATE_FILE", state_file):
                stream = EventStream()
                mgr = EventLifecycleManager(stream)
                mgr.append({"id": "abc12345", "event_type": "test", "role": "skill"})
                self.assertTrue(state_file.exists())

                stream2 = EventStream()
                mgr2 = EventLifecycleManager(stream2)
                mgr2.load()
                events = stream2.get_all()
                self.assertEqual(len(events), 1)
                self.assertEqual(events[0]["id"], "abc12345")

    def test_load_ignores_legacy_dispatch_fields(self):
        """#11165: a legacy state file still carrying in_flight/dispatched/
        dispatch_times/retry_counts loads cleanly — those keys are silently
        ignored, cursors + events still restore, no AttributeError."""
        import tempfile
        import json
        from harness import EventStream, EventLifecycleManager

        with tempfile.TemporaryDirectory() as tmpdir:
            state_file = Path(tmpdir) / ".event-state.json"
            state_file.write_text(json.dumps({
                "events": [{"id": "e1", "event_type": "t", "role": "skill"}],
                "in_flight": {"skill": ["e1"]},
                "dispatched": {"e1": {}},
                "dispatch_times": {"e1": 1.0},
                "retry_counts": {"e1": 0},
                "cursors": {"skill": "e1"},
            }), encoding="utf-8")
            with patch("harness.EVENT_STATE_FILE", state_file):
                stream = EventStream()
                mgr = EventLifecycleManager(stream)
                mgr.load()  # must not raise on the legacy keys
                self.assertEqual(len(stream.get_all()), 1)
                self.assertEqual(mgr.get_cursor("skill"), "e1")
                self.assertFalse(hasattr(mgr, "_in_flight"))

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
        """event_poll.py in target mode queries /events/for/<role>.

        Reconciled to model-B (#11329): event_poll no longer owns the
        cursor — it is harness-owned and passed via ``since=``. The
        legacy ``_read_cursor_from_working_state`` / ``_write_cursor_atomic``
        helpers were removed by the ack-cursor migration; ``poll`` now
        returns a ``(events, hwm)`` tuple.
        """
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
        """event_poll.py in legacy mode queries /events with role param.

        Reconciled to model-B (#11329): ``poll`` returns ``(events, hwm)``
        and the cursor is supplied by the caller, not read from
        working-state.
        """
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

    def test_excludes_self_emitted_reacts_to_events_13255(self):
        """#13255: a reacts-to match emitted BY the requesting role itself is
        excluded — an agent must not self-wake on its own git-commit /
        status-transition events (they always drain to a care-filter no-op).
        Cross-agent reacts-to events (different emitter) are still delivered, and
        explicit target_alias targeting always wins (even self-emitted)."""
        from harness import event_stream

        event_stream.append({  # self-emitted reacts-to -> EXCLUDED
            "id": "own1", "event_type": "git-commit", "role": "skill",
            "payload": {"result": "ok"},
        })
        event_stream.append({  # cross-agent reacts-to -> INCLUDED
            "id": "other1", "event_type": "git-commit", "role": "qa",
            "payload": {"result": "ok"},
        })
        event_stream.append({  # self-emitted BUT explicitly targeted -> INCLUDED
            "id": "selftarget1", "event_type": "assigned-to", "role": "skill",
            "payload": {"target_alias": "skill"},
        })

        with patch("harness._validate_role"), \
             patch("config.get_event_filters_for_role",
                   return_value=["git-commit", "status-transition"]):
            resp = self.client.get("/events/for/skill")

        self.assertEqual(resp.status_code, 200)
        ids = [e["id"] for e in resp.json()["events"]]
        self.assertNotIn("own1", ids, "self-emitted git-commit must be excluded (#13255)")
        self.assertIn("other1", ids, "cross-agent git-commit must still be delivered")
        self.assertIn("selftarget1", ids, "explicit target_alias must win over self-emitted exclusion")

    def test_self_emit_filter_includes_event_with_missing_emitter_13255(self):
        """#13255 (review LOW): an event with no top-level `role` field has
        emitter "" — it cannot be attributed to the requesting role, so the
        self-emit exclusion must NOT drop it (conservative-correct: include)."""
        from harness import event_stream

        event_stream.append({  # reacts-to match, NO emitter -> INCLUDED
            "id": "noemit1", "event_type": "git-commit",
            "payload": {"result": "ok"},
        })

        with patch("harness._validate_role"), \
             patch("config.get_event_filters_for_role",
                   return_value=["git-commit"]):
            resp = self.client.get("/events/for/skill")

        self.assertEqual(resp.status_code, 200)
        ids = [e["id"] for e in resp.json()["events"]]
        self.assertIn("noemit1", ids,
                      "event with missing emitter must not be excluded (#13255)")

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

class TestCompleteEventEndpoint(unittest.TestCase):
    """#11165: POST /events/{event_id}/complete was removed under pull-only —
    it now returns 410 Gone unconditionally. The dispatch/ack lifecycle it
    drove was deleted (#11092 Decision 2)."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from harness import app

        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_complete_returns_410_always(self):
        """AC3: a well-formed completion POST returns 410 Gone."""
        resp = self.client.post("/events/any-id/complete", json={
            "role": "skill", "status": "success", "summary": "Done",
        })
        self.assertEqual(resp.status_code, 410)
        self.assertEqual(resp.json()["status"], "gone")

    def test_complete_returns_410_even_without_role(self):
        """The 410 fires before any body validation — pure deprecation shell."""
        resp = self.client.post("/events/any-id/complete", json={})
        self.assertEqual(resp.status_code, 410)


class TestMergeBodyGuard13170(unittest.TestCase):
    """#13170: POST /merge must fail CLOSED (400) on a malformed or non-object
    JSON body — mirroring POST /events (#13156) and POST /work/assign (#12495).
    Unguarded, a truncated body raised JSONDecodeError and a non-object body
    raised AttributeError on .get(), both propagating to the global handler as
    a 500 where a clean 400 is the contract. Both rejections fire BEFORE any
    merge thread spawns, so no git_ops mocking is needed."""

    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from harness import app

        cls.client = TestClient(app, raise_server_exceptions=False)

    def test_malformed_json_body_400(self):
        resp = self.client.post(
            "/merge", content=b"{not valid json",
            headers={"Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("malformed JSON body", resp.json()["detail"])

    def test_non_dict_body_400(self):
        """A valid-but-non-object body ([1,2], null, 42) -> 400, not a 500 on
        .get(). Sent as raw JSON content (TestClient json=None would send an
        empty body, which is the malformed-parse case, not a JSON null)."""
        for raw in (b"[1, 2]", b"null", b"42"):
            resp = self.client.post(
                "/merge", content=raw,
                headers={"Content-Type": "application/json"})
            self.assertEqual(resp.status_code, 400,
                             f"non-dict body {raw!r} must be 400")
            self.assertIn("must be a JSON object", resp.json()["detail"])

    def test_valid_object_missing_pr_number_still_400(self):
        """Regression: a well-formed object without pr_number keeps its own 400
        (the new guard does not shadow the pre-existing required-field check)."""
        resp = self.client.post("/merge", json={"branch": "x", "role": "skill"})
        self.assertEqual(resp.status_code, 400)
        self.assertIn("pr_number is required", resp.json()["detail"])


class TestSafePullInClone13215(unittest.TestCase):
    """#13215: the deploy sequence's clone pull must survive a DIRTY working
    tree (uncommitted change to a file the incoming commit touches) by
    stashing-around-merge, instead of aborting and silently skipping the
    deploy-sync. _safe_pull_in_clone mirrors git_ops.pull (#13167/#13045) over
    an arbitrary clone via _git_in_clone. Driven entirely by a scripted
    _git_in_clone responder (no real git)."""

    def _resp(self, rc=0, out="", err=""):
        from types import SimpleNamespace
        return SimpleNamespace(returncode=rc, stdout=out, stderr=err)

    def _responder(self, scripted):
        """Return a _git_in_clone side_effect. `scripted` maps a command key to
        a LIST of responses consumed in order; unscripted commands default to
        rc=0. Keys: 'pull','stash','stash pop','stash drop','rev-parse','diff',
        'checkout'."""
        def _key(args):
            if args[:2] == ["stash", "pop"]:
                return "stash pop"
            if args[:2] == ["stash", "drop"]:
                return "stash drop"
            return args[0]

        def _side(clone_path, args, **kw):
            k = _key(list(args))
            q = scripted.get(k)
            if q:
                return q.pop(0)
            return self._resp(0)
        return _side

    def test_clean_pull_succeeds(self):
        import harness
        with patch.object(harness, "_git_in_clone",
                          side_effect=self._responder({"pull": [self._resp(0)]})):
            ok, detail = harness._safe_pull_in_clone("/clone")
        self.assertTrue(ok)
        self.assertEqual(detail, "pulled")

    def test_already_up_to_date_succeeds(self):
        import harness
        with patch.object(harness, "_git_in_clone", side_effect=self._responder(
                {"pull": [self._resp(1, err="Already up to date.")]})):
            ok, detail = harness._safe_pull_in_clone("/clone")
        self.assertTrue(ok)
        self.assertEqual(detail, "already-up-to-date")

    def test_dirty_tree_stashes_pulls_and_pops(self):
        """The exact #13215 bug: first pull aborts (dirty), stash creates an
        entry, retry pull succeeds, clean pop -> success."""
        import harness
        scripted = {
            "pull": [self._resp(1, err="local changes would be overwritten by merge"),
                     self._resp(0)],
            # rev-parse: pre (no stash) then post (stash exists)
            "rev-parse": [self._resp(1, out=""), self._resp(0, out="abc123")],
            "stash": [self._resp(0)],
            "stash pop": [self._resp(0)],
        }
        with patch.object(harness, "_git_in_clone",
                          side_effect=self._responder(scripted)):
            ok, detail = harness._safe_pull_in_clone("/clone")
        self.assertTrue(ok)
        self.assertEqual(detail, "pulled (stashed and popped)")

    def test_genuine_merge_conflict_fails_after_stash(self):
        """A committed-divergence conflict: retry pull also fails -> (False, ...)
        so the caller routes to §11 recovery. The merge is aborted (clears
        MERGE_HEAD + markers) BEFORE the stash is restored, so the clone is not
        left in MERGING state (which would loop the next deploy's checkout)."""
        import harness
        calls = []
        scripted = {
            "pull": [self._resp(1, err="conflict A"),
                     self._resp(1, err="CONFLICT (content): merge conflict in x")],
            "rev-parse": [self._resp(1, out=""), self._resp(0, out="abc123")],
            "stash": [self._resp(0)],
            "stash pop": [self._resp(0)],  # restore after merge --abort
        }
        responder = self._responder(scripted)

        def _tracking(clone_path, args, **kw):
            calls.append(list(args))
            return responder(clone_path, args, **kw)
        with patch.object(harness, "_git_in_clone", side_effect=_tracking):
            ok, detail = harness._safe_pull_in_clone("/clone")
        self.assertFalse(ok)
        self.assertIn("pull-failed", detail)
        # #13215 review MED: the merge is aborted before restoring the stash, and
        # the abort precedes the stash pop (so MERGING state is cleared first).
        self.assertIn(["merge", "--abort"], calls)
        self.assertLess(calls.index(["merge", "--abort"]),
                        calls.index(["stash", "pop"]),
                        "merge --abort must precede the stash restore")

    def test_clean_tree_transient_first_failure_no_pop(self):
        """First pull fails but the tree is CLEAN (stash creates nothing) — the
        retry succeeds and there is nothing to pop (#13167 no-op-stash guard)."""
        import harness
        scripted = {
            "pull": [self._resp(1, err="transient"), self._resp(0)],
            "rev-parse": [self._resp(1, out=""), self._resp(1, out="")],  # unchanged
            "stash": [self._resp(0)],
        }
        with patch.object(harness, "_git_in_clone",
                          side_effect=self._responder(scripted)):
            ok, detail = harness._safe_pull_in_clone("/clone")
        self.assertTrue(ok)
        self.assertEqual(detail, "pulled (no local changes to stash)")

    def test_stash_command_failure_returns_false(self):
        import harness
        scripted = {
            "pull": [self._resp(1, err="dirty")],
            "rev-parse": [self._resp(1, out="")],
            "stash": [self._resp(1, err="stash boom")],
        }
        with patch.object(harness, "_git_in_clone",
                          side_effect=self._responder(scripted)):
            ok, detail = harness._safe_pull_in_clone("/clone")
        self.assertFalse(ok)
        self.assertIn("stash-failed", detail)

    def test_stash_pop_conflict_resolves_to_pulled_state(self):
        """Retry pull succeeds but the stashed local change conflicts on pop ->
        force-resolved to HEAD, still reported as a successful pull (the
        CLAUDE.md sync landed; the stale local change is discarded)."""
        import harness
        scripted = {
            "pull": [self._resp(1, err="dirty"), self._resp(0)],
            "rev-parse": [self._resp(1, out=""), self._resp(0, out="abc123")],
            "stash": [self._resp(0)],
            "stash pop": [self._resp(1, err="conflict")],
            "diff": [self._resp(0, out="config.md\n")],  # unmerged path
            "checkout": [self._resp(0)],
            "stash drop": [self._resp(0)],
        }
        with patch.object(harness, "_git_in_clone",
                          side_effect=self._responder(scripted)):
            ok, detail = harness._safe_pull_in_clone("/clone")
        self.assertTrue(ok)
        self.assertIn("resolved to pulled state", detail)

    def test_safe_stash_pop_in_clone_no_unmerged_does_not_drop(self):
        """A pop that fails for a NON-conflict reason (no unmerged paths) must
        NOT drop the stash (would discard un-applied work)."""
        import harness
        calls = []

        def _side(clone_path, args, **kw):
            calls.append(list(args))
            if list(args)[:2] == ["stash", "pop"]:
                return self._resp(1, err="no stash")
            if list(args)[0] == "diff":
                return self._resp(0, out="")  # no unmerged
            return self._resp(0)
        with patch.object(harness, "_git_in_clone", side_effect=_side):
            result = harness._safe_stash_pop_in_clone("/clone")
        self.assertFalse(result)
        self.assertNotIn(["stash", "drop"], calls)


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

    def test_reboot_affected_agents_emits_deploy_signal(self):
        """#12912 (supersedes #8695 R2): _reboot_affected_agents is now the
        deploy-signal EMITTER. It sets intent=DEPLOYING and emits a deploy-signal
        to the affected alias — and deliberately LEAVES bootup_complete=True so
        the signal is actually delivered off the event bus (the cooperative
        deploy-halt replaces the old slam-bootup_complete-False force restart;
        the agent stops picking up work itself when it halts)."""
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill")
        agent.intent = AgentState.INTENT_RUNNING
        agent.status = "running"  # #12912 iter-3 F1: only ALIVE agents are signaled
        agent.bootup_complete = True
        hs.set_agent("skill", agent)
        import harness
        prev_state = harness.state
        harness.state = hs
        fake_git_diff = MagicMock()
        fake_git_diff.returncode = 0
        fake_git_diff.stdout = ".squidsquad/skill/CLAUDE.md\n"
        emitted = []
        try:
            with patch("harness._log"), \
                 patch("harness.subprocess.run", return_value=fake_git_diff), \
                 patch("harness._emit_event",
                       side_effect=lambda *a, **k: emitted.append((a, k))), \
                 patch.object(hs, "save_state"):
                harness._reboot_affected_agents(123, ["references/sub-skills/common/x.md"])
        finally:
            harness.state = prev_state
        updated = hs.get_agent("skill")
        self.assertEqual(updated.intent, AgentState.INTENT_DEPLOYING)
        # bootup_complete is intentionally NOT cleared (signal must be delivered).
        self.assertTrue(updated.bootup_complete)
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0][0][0], "deploy-signal")
        self.assertEqual(emitted[0][1]["payload"]["target_alias"], "skill")

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
# EAD status-aware work routing — #12342
# ---------------------------------------------------------------------------

class TestEADStatusRouting12342(unittest.TestCase):
    """#12342: the External Activity Detector must route work by status so
    event-mode QA/DM no longer starve:

    - status:approved / status:open → the issue's role:* worker alias
    - status:pending-test           → the install's verifier alias
    - status:pending-ship           → the install's dm alias

    and dedup per (issue, status) so each transition emits once (keying by
    issue number alone meant an issue emitted at most one assigned-to ever).
    """

    _REGISTRY = {
        "skill": ("worker", "skill"),
        "web": ("worker", "web"),
        "pm": ("pm", None),
        "verifier": ("verifier", None),
        "dm": ("dm", None),
        "human": ("human", None),  # #12800: non-agent role-class
    }

    def _issue(self, num, status, role="skill", updated="2099-01-01T00:00:00Z"):
        labels = [{"name": "squidsquad"}, {"name": f"status:{status}"}]
        if role:
            labels.append({"name": f"role:{role}"})
        return {"number": num, "title": f"ISSUE: thing {num}",
                "labels": labels, "updatedAt": updated}

    def _run(self, issues, det=None, registry=None):
        """Run _check_for_changes once against a faked `gh issue list`,
        returning (detector, [emitted assigned-to payloads])."""
        from harness import ExternalActivityDetector
        import config as _cfg
        det = det or ExternalActivityDetector()
        gh_result = MagicMock()
        gh_result.returncode = 0
        gh_result.stdout = json.dumps(issues)
        emitted = []

        def fake_emit(event_type, role, payload=None, **extra):
            if event_type == "assigned-to":
                emitted.append(payload or {})

        with patch("harness.subprocess.run", return_value=gh_result), \
             patch("harness._emit_event", side_effect=fake_emit), \
             patch.object(_cfg, "parse_aliases_registry",
                          return_value=registry or self._REGISTRY):
            det._check_for_changes()
        return det, emitted

    def test_pending_test_routes_to_verifier(self):
        _, emitted = self._run([self._issue(1, "pending-test", role="skill")])
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["target_alias"], "verifier",
                         "pending-test must route to the verifier alias, NOT "
                         "the issue's role:skill worker label (#12342)")

    def test_pending_ship_routes_to_dm(self):
        _, emitted = self._run([self._issue(2, "pending-ship", role="skill")])
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["target_alias"], "dm")

    def test_pending_human_review_routes_to_human(self):
        """#12800 AC3: an agent-needs-human handoff routes to the install's
        `human` alias (was pm), resolved via the role-class registry."""
        _, emitted = self._run(
            [self._issue(20, "pending-human-review", role="skill")])
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["target_alias"], "human",
                         "pending-human-review must route to the human alias "
                         "(#12800), NOT pm and NOT the issue's worker label")

    def test_pending_human_setup_routes_to_human(self):
        """#12800 AC3: worker-pause-for-setup also routes to the human alias."""
        _, emitted = self._run(
            [self._issue(21, "pending-human-setup", role="skill")])
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["target_alias"], "human")

    def test_pending_human_does_not_enter_handoff_reemit_12800(self):
        """#12800: a human is NOT on the event bus, so the assigned-to <human>
        is emitted once for forge/audit but must NOT enter the #12442 handoff
        re-emit cadence (re-nudging would pile up never-consumed events). A
        real agent handoff (pending-test → verifier) DOES seed the re-emit."""
        det, emitted = self._run(
            [self._issue(22, "pending-human-review", role="skill")])
        self.assertEqual(emitted[0]["target_alias"], "human")
        self.assertNotIn(22, det._handoff_emit_at,
                         "human routing must not seed the handoff re-emit timer")
        det2, _ = self._run([self._issue(23, "pending-test", role="skill")])
        self.assertIn(23, det2._handoff_emit_at,
                      "agent handoff (pending-test) must seed the re-emit timer")

    def test_approved_routes_to_worker_label(self):
        _, emitted = self._run([self._issue(3, "approved", role="skill")])
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["target_alias"], "skill")

    def test_open_routes_to_worker_label(self):
        _, emitted = self._run([self._issue(4, "open", role="web")])
        self.assertEqual(len(emitted), 1)
        self.assertEqual(emitted[0]["target_alias"], "web")

    def test_in_progress_emits_nothing(self):
        """in-progress (worker already on it) and other unmapped statuses must
        not emit — only approved/open/pending-test/pending-ship route."""
        _, emitted = self._run([self._issue(5, "in-progress", role="skill")])
        self.assertEqual(emitted, [])
        _, emitted2 = self._run([self._issue(6, "planned", role="skill")])
        self.assertEqual(emitted2, [])

    def test_dedup_per_issue_status_across_transitions(self):
        """The SAME issue must emit once per STATUS — once at approved (worker),
        again at pending-test (verifier) — not be deduped to a single lifetime
        emit (the pre-#12342 per-issue-number dedup bug)."""
        det, emitted1 = self._run(
            [self._issue(7, "approved", role="skill",
                         updated="2099-01-01T00:00:00Z")])
        self.assertEqual([e["target_alias"] for e in emitted1], ["skill"])

        # Same issue, still approved, newer updatedAt → deduped (no re-emit).
        _, emitted_dup = self._run(
            [self._issue(7, "approved", role="skill",
                         updated="2099-02-01T00:00:00Z")], det=det)
        self.assertEqual(emitted_dup, [],
                         "same (issue, status) must not re-emit even when a "
                         "comment bumps updatedAt")

        # Issue transitions to pending-test → emits once, to verifier.
        _, emitted2 = self._run(
            [self._issue(7, "pending-test", role="skill",
                         updated="2099-03-01T00:00:00Z")], det=det)
        self.assertEqual([e["target_alias"] for e in emitted2], ["verifier"])

    def test_back_transition_reemits_to_verifier(self):
        """DS-REVIEW-12342 Finding 1 regression: a reject loop
        pending-test → in-progress → pending-test MUST re-emit to the verifier
        each time it re-enters pending-test. A naive (issue, status) dedup set
        would suppress the second pending-test and starve QA on re-verification.
        """
        det, e1 = self._run([self._issue(10, "pending-test", role="skill",
                                         updated="2099-01-01T00:00:00Z")])
        self.assertEqual([e["target_alias"] for e in e1], ["verifier"])

        # QA rejects → in-progress: no emit, but the status is recorded.
        det, e2 = self._run([self._issue(10, "in-progress", role="skill",
                                         updated="2099-02-01T00:00:00Z")], det=det)
        self.assertEqual(e2, [])

        # Worker resubmits → pending-test: MUST re-emit to verifier.
        det, e3 = self._run([self._issue(10, "pending-test", role="skill",
                                         updated="2099-03-01T00:00:00Z")], det=det)
        self.assertEqual([e["target_alias"] for e in e3], ["verifier"],
                         "re-entry to pending-test after a reject must re-wake "
                         "the verifier (DS Finding 1)")

    def test_comment_bump_same_status_does_not_reemit(self):
        """A comment that bumps updatedAt without changing status must NOT
        re-emit (the dedup's core job)."""
        det, e1 = self._run([self._issue(11, "pending-test", role="skill",
                                         updated="2099-01-01T00:00:00Z")])
        self.assertEqual(len(e1), 1)
        _, e2 = self._run([self._issue(11, "pending-test", role="skill",
                                       updated="2099-02-01T00:00:00Z")], det=det)
        self.assertEqual(e2, [], "same status + comment bump must not re-emit")

    def test_time_filter_skips_unupdated_worker_issues(self):
        """A WORKER-status issue (approved/open) not updated since last check is
        skipped — its owning worker is presumed already looping on its queue, so
        the time filter rightly suppresses re-emit. NOTE (#12442): HANDOFF
        statuses (pending-test/pending-ship) are deliberately EXEMPT from this —
        see test_handoff_reemits_stuck_item_despite_old_updatedat."""
        det, _ = self._run([self._issue(8, "approved", role="skill",
                                        updated="2000-01-01T00:00:00Z")])
        # _last_check_epoch advanced to ~now; an old updatedAt is skipped.
        _, emitted = self._run([self._issue(9, "approved", role="web",
                                            updated="2000-01-01T00:00:00Z")],
                               det=det)
        self.assertEqual(emitted, [])

    def test_alias_for_role_class_resolves_from_registry(self):
        """Verifier/dm targets are resolved from the install's alias registry,
        not hardcoded — a non-default alias name must be honored."""
        from harness import ExternalActivityDetector
        import config as _cfg
        reg = {"skill": ("worker", "skill"), "tester": ("verifier", None),
               "shipper": ("dm", None)}
        with patch.object(_cfg, "parse_aliases_registry", return_value=reg):
            self.assertEqual(
                ExternalActivityDetector._alias_for_role_class("verifier"),
                "tester")
            self.assertEqual(
                ExternalActivityDetector._alias_for_role_class("dm"),
                "shipper")

    def test_alias_for_role_class_falls_back_to_class_name(self):
        """If config is unreadable, fall back to the role-class name (a valid
        bare alias in singleton installs)."""
        from harness import ExternalActivityDetector
        import config as _cfg
        with patch.object(_cfg, "parse_aliases_registry",
                          side_effect=Exception("config boom")):
            self.assertEqual(
                ExternalActivityDetector._alias_for_role_class("verifier"),
                "verifier")

    def test_is_agent_update_removed(self):
        """The broken title-prefix `_is_agent_update` skip is gone (#12342) —
        it matched every SquidSquad issue and made the EAD emit nothing."""
        from harness import ExternalActivityDetector
        self.assertFalse(hasattr(ExternalActivityDetector, "_is_agent_update"))


class TestEADHandoffReemit12442(unittest.TestCase):
    """#12442: terminal HANDOFF statuses (pending-test → verifier, pending-ship
    → dm) re-emit the assigned-to nudge on a bounded cadence so a single
    lost/missed nudge no longer starves delivery indefinitely.

    The original #12342 design emitted exactly once per transition, gated by
    ``updatedAt > _last_check_epoch``. If the one nudge was missed (dm busy
    mid-cycle, a cursor gap, ack-without-action), or the item was ALREADY at
    the handoff status when the detector (re)started — so its updatedAt is in
    the past and the time filter hides it forever — the item starved. Observed:
    #12418 sat pending-ship 48 min until PM hand-injected a wake event.

    Re-emit is scoped to handoff statuses only — worker statuses (approved/open)
    route to a worker presumed already looping on its own queue, so they keep
    the plain single-emit + time-filter behavior.
    """

    _REGISTRY = {
        "skill": ("worker", "skill"),
        "web": ("worker", "web"),
        "verifier": ("verifier", None),
        "dm": ("dm", None),
    }

    # Realistic epochs (year ~2033) so that an issue's old updatedAt
    # (2000-01-01 → epoch 946684800) sorts BEFORE the pinned clock.
    _START = 2_000_000_000

    def _issue(self, num, status, role="skill", updated="2000-01-01T00:00:00Z"):
        labels = [{"name": "squidsquad"}, {"name": f"status:{status}"}]
        if role:
            labels.append({"name": f"role:{role}"})
        return {"number": num, "title": f"ISSUE: thing {num}",
                "labels": labels, "updatedAt": updated}

    def _run(self, issues, det, now):
        """Run _check_for_changes once with harness's clock pinned to ``now``,
        returning the list of emitted assigned-to payloads."""
        import config as _cfg
        gh_result = MagicMock(returncode=0, stdout=json.dumps(issues))
        emitted = []

        def fake_emit(event_type, role, payload=None, **extra):
            if event_type == "assigned-to":
                emitted.append(payload or {})

        with patch("harness.subprocess.run", return_value=gh_result), \
             patch("harness._emit_event", side_effect=fake_emit), \
             patch("harness.time.time", return_value=now), \
             patch.object(_cfg, "parse_aliases_registry",
                          return_value=self._REGISTRY):
            det._check_for_changes()
        return emitted

    def _stuck_detector(self):
        """A detector whose last-check epoch is AFTER an old item's transition —
        i.e. the item was already at its status when the detector started, so
        the time filter alone would hide it forever."""
        from harness import ExternalActivityDetector
        det = ExternalActivityDetector()
        det._last_check_epoch = self._START
        return det

    def test_reemits_stuck_pending_ship_despite_old_updatedat(self):
        """The core fix: a pending-ship item already stuck when the detector
        started (old updatedAt) is still nudged to dm — the single-emit +
        time-filter design would never have surfaced it."""
        det = self._stuck_detector()
        emitted = self._run([self._issue(1, "pending-ship", role="skill")],
                            det, now=self._START + 50)
        self.assertEqual([e["target_alias"] for e in emitted], ["dm"])

    def test_reemits_stuck_pending_test_to_verifier(self):
        """Symmetric: pending-test re-emits to the verifier alias."""
        det = self._stuck_detector()
        emitted = self._run([self._issue(2, "pending-test", role="skill")],
                            det, now=self._START + 50)
        self.assertEqual([e["target_alias"] for e in emitted], ["verifier"])

    def test_no_reemit_within_interval(self):
        """A second poll inside the re-emit interval must NOT re-nudge — the
        cadence is bounded, not every-poll spam."""
        det = self._stuck_detector()
        issue = [self._issue(3, "pending-ship", role="skill")]
        e1 = self._run(issue, det, now=self._START + 50)
        self.assertEqual(len(e1), 1)
        e2 = self._run(issue, det, now=self._START + 150)  # +100s < 600s
        self.assertEqual(e2, [], "must not re-nudge before the interval elapses")

    def test_reemits_after_interval_elapses(self):
        """Once the interval passes and the item is STILL stuck, re-nudge."""
        det = self._stuck_detector()
        issue = [self._issue(4, "pending-ship", role="skill")]
        e1 = self._run(issue, det, now=self._START + 50)
        self.assertEqual(len(e1), 1)
        e2 = self._run(issue, det, now=self._START + 750)  # +700s > 600s
        self.assertEqual([e["target_alias"] for e in e2], ["dm"])

    def test_worker_status_never_reemitted(self):
        """Worker statuses keep the single-emit + time-filter behavior — no
        re-emit cadence (their worker is presumed already looping)."""
        det = self._stuck_detector()
        issue = [self._issue(5, "approved", role="skill")]
        e1 = self._run(issue, det, now=self._START + 50)
        self.assertEqual(e1, [], "old-updatedAt worker item is time-filtered out")
        e2 = self._run(issue, det, now=self._START + 5000)  # well past interval
        self.assertEqual(e2, [], "worker statuses must not get the re-emit path")

    def test_fresh_transition_seeds_timer_no_immediate_double(self):
        """A normal fresh transition emits once via the fast path AND seeds the
        re-emit timer, so the very next poll within the interval does not
        double-fire."""
        det = self._stuck_detector()
        # recent updatedAt → fresh-transition fast path
        e1 = self._run([self._issue(6, "pending-ship", role="skill",
                                    updated="2099-01-01T00:00:00Z")],
                       det, now=self._START + 50)
        self.assertEqual([e["target_alias"] for e in e1], ["dm"])
        e2 = self._run([self._issue(6, "pending-ship", role="skill",
                                    updated="2099-01-01T00:00:00Z")],
                       det, now=self._START + 100)
        self.assertEqual(e2, [], "fresh transition must seed the timer")

    def test_status_change_then_reentry_renudges_immediately(self):
        """When dm bounces a ship back to in-progress and it later re-enters
        pending-ship, the fresh-transition path re-emits at once — it does not
        wait out the stale re-emit interval."""
        det = self._stuck_detector()
        e1 = self._run([self._issue(7, "pending-ship", role="skill")],
                       det, now=self._START + 50)
        self.assertEqual([e["target_alias"] for e in e1], ["dm"])
        # bounced back to in-progress (merge conflict rollback): no emit
        e2 = self._run([self._issue(7, "in-progress", role="skill",
                                    updated="2099-01-01T00:00:00Z")],
                       det, now=self._START + 100)
        self.assertEqual(e2, [])
        # re-enters pending-ship → immediate re-emit via fresh-transition path
        e3 = self._run([self._issue(7, "pending-ship", role="skill",
                                    updated="2099-02-01T00:00:00Z")],
                       det, now=self._START + 150)
        self.assertEqual([e["target_alias"] for e in e3], ["dm"],
                         "re-entry must re-emit at once, not wait the interval")


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


class TestCloneResolutionRefusal(unittest.TestCase):
    """#11640: every spawn path must REFUSE when clone resolution fails,
    never spawning in REPO_ROOT. Covers the /start endpoint, the /restart
    endpoint, and the harness auto-reboot loop."""

    def setUp(self):
        import harness
        self.harness = harness
        # Isolate from any state other tests left behind.
        harness.state.agents.pop("qa", None)
        harness.state.compose_freshness_failed = False

    def test_start_endpoint_refuses_and_marks_error(self):
        """POST /agents/{role}/start refuses (500) and marks the agent error
        when boot_agent reports a clone-resolution failure — no spawn."""
        from fastapi.testclient import TestClient
        err = {"role": "qa", "action": "error", "success": False,
               "message": "clone resolution failed — refusing to spawn"}
        with patch.object(self.harness.boot_remote, "boot_agent", return_value=err) as mock_boot:
            client = TestClient(self.harness.app)
            resp = client.post("/agents/qa/start")
        self.assertEqual(resp.status_code, 500)
        self.assertFalse(resp.json()["success"])
        mock_boot.assert_called_once_with("qa")
        agent = self.harness.state.get_agent("qa")
        self.assertIsNotNone(agent)
        self.assertEqual(agent.status, "error")

    def test_restart_endpoint_refuses_before_mutating_intent(self):
        """POST /agents/{role}/restart resolves the clone BEFORE setting
        intent=restarting, so an UNRESOLVABLE role is refused (500) and is NOT
        left in a restarting state.

        #12380: this test must MOCK `_get_clone_path` to raise rather than
        depend on the live `.local-config` keying. Its prior premise — "qa is
        unregistered in this clone's .local-config" — was the #11600 bug
        itself: compose keyed `.local-config` by the role-class `verifier`, so
        `qa` was absent and resolution happened to raise. #12380 fixes that
        (qa is now correctly registered), so the test can no longer rely on
        qa-absence; it controls resolution directly, like its siblings."""
        from fastapi.testclient import TestClient
        client = TestClient(self.harness.app)
        with patch.object(
            self.harness.boot_remote, "_get_clone_path",
            side_effect=self.harness.boot_remote.CloneResolutionError(
                "role 'qa' is not registered — refusing to fall back to REPO_ROOT"),
        ):
            resp = client.post("/agents/qa/restart")
        self.assertEqual(resp.status_code, 500)
        self.assertIn("clone resolution failed", resp.json()["message"])
        # No restarting state was created for the refused role.
        agent = self.harness.state.get_agent("qa")
        if agent is not None:
            self.assertNotEqual(agent.intent, self.harness.AgentState.INTENT_RESTARTING)

    def test_auto_reboot_loop_refuses_and_marks_error(self):
        """The harness auto-reboot loop marks the agent error (and does not
        retain a spawn) when boot_agent refuses on clone resolution."""
        from harness import HarnessState, AgentState
        st = HarnessState()
        # A dead agent that was running and should reboot.
        agent = AgentState("skill", "/tmp/skill-clone")
        agent.status = "running"  # prev_status seen by the loop
        agent.intent = AgentState.INTENT_RUNNING
        agent.claude_pid = 99999999  # a dead pid
        st.agents["skill"] = agent

        err = {"role": "skill", "action": "error", "success": False,
               "message": "clone resolution failed — refusing to spawn"}
        with patch.object(self.harness.boot_remote, "_get_all_roles", return_value=["skill"]), \
             patch.object(self.harness.boot_remote, "_get_clone_path", return_value="/tmp/skill-clone"), \
             patch.object(self.harness.boot_remote, "_is_process_alive", return_value=False), \
             patch.object(self.harness.reboot_agent, "_read_claude_pid", return_value=(None, False)), \
             patch.object(self.harness.boot_remote, "boot_agent", return_value=err) as mock_boot, \
             patch.object(self.harness, "_NO_AUTO_REBOOT", False), \
             patch.object(st, "save_state"):
            st.update_health()

        mock_boot.assert_called_once_with("skill")
        self.assertEqual(st.agents["skill"].status, "error")
        # Refused boot left no terminal pid behind.
        self.assertIsNone(st.agents["skill"].terminal_pid)


# ---------------------------------------------------------------------------
# SessionEnd hook ingestion — #12418 (HARNESS-ARCH §15.4 / §16)
# ---------------------------------------------------------------------------

class TestSessionEndHook12418(unittest.TestCase):
    """#12418 AC3: POST /hooks/session-end/{role} records the SessionEnd
    reason on AgentState (the graceful-exit signal), persists it, exposes it
    via GET /agents/{role}, and is fail-open (always 200 — a hook must never
    block/fail an agent's teardown)."""

    def setUp(self):
        import harness
        from fastapi.testclient import TestClient
        self.harness = harness
        self.client = TestClient(harness.app, raise_server_exceptions=False)
        harness.state.start_time = time.time()
        self.role = "skill"
        self._roles = patch.object(
            harness.boot_remote, "_get_all_roles", return_value=[self.role])
        self._roles.start()
        self._save = patch.object(harness.state, "save_state")
        self._save.start()
        # GET /agents/{role} runs update_health (PID checks) — neutralize it.
        self._uh = patch.object(harness.state, "update_health")
        self._uh.start()
        harness.state.agents.pop(self.role, None)

    def tearDown(self):
        self._uh.stop()
        self._save.stop()
        self._roles.stop()
        self.harness.state.agents.pop(self.role, None)

    def _hdr(self, role=None):
        return {"X-Agent-Role": self.role if role is None else role}

    def test_records_reason_on_agentstate(self):
        resp = self.client.post(
            "/hooks/session-end", headers=self._hdr(),
            json={"hook_event_name": "SessionEnd", "stop_reason": "other"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))
        agent = self.harness.state.agents.get(self.role)
        self.assertIsNotNone(agent)
        self.assertEqual(agent.last_session_end["reason"], "other")
        self.assertIn("at", agent.last_session_end)

    def test_exposed_via_get_agent(self):
        self.client.post("/hooks/session-end", headers=self._hdr(),
                         json={"stop_reason": "logout"})
        resp = self.client.get(f"/agents/{self.role}")
        self.assertEqual(resp.status_code, 200)
        se = resp.json().get("last_session_end")
        self.assertIsNotNone(se)
        self.assertEqual(se["reason"], "logout")

    def test_missing_stop_reason_defaults_unknown(self):
        resp = self.client.post("/hooks/session-end", headers=self._hdr(), json={})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            self.harness.state.agents[self.role].last_session_end["reason"],
            "unknown")

    def test_malformed_body_is_fail_open(self):
        resp = self.client.post(
            "/hooks/session-end", content=b"not json",
            headers={**self._hdr(), "Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(
            self.harness.state.agents[self.role].last_session_end["reason"],
            "unknown")

    def test_no_role_header_dropped_but_200(self):
        resp = self.client.post("/hooks/session-end", json={"stop_reason": "other"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("ok"))
        self.assertEqual(resp.json().get("dropped"), "no-role")

    def test_uninterpolated_env_var_role_is_no_role(self):
        """#12418 F5: if $SQUIDSQUAD_ROLE was unset, Claude Code sends the
        literal '${SQUIDSQUAD_ROLE}' — treat it as no-role (not unknown-role)."""
        resp = self.client.post("/hooks/session-end",
                                headers=self._hdr("${SQUIDSQUAD_ROLE}"),
                                json={"stop_reason": "other"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("dropped"), "no-role")

    def test_unknown_role_dropped_but_200(self):
        resp = self.client.post("/hooks/session-end",
                                headers=self._hdr("bogus-role"),
                                json={"stop_reason": "other"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("ok"))
        self.assertNotIn("bogus-role", self.harness.state.agents)

    def test_save_failure_is_fail_open(self):
        """Even if persistence raises, the hook still answers 200 — never
        block teardown."""
        self._save.stop()  # replace with a raising stub
        with patch.object(self.harness.state, "save_state",
                               side_effect=OSError("disk full")):
            resp = self.client.post("/hooks/session-end", headers=self._hdr(),
                                    json={"stop_reason": "other"})
        self._save.start()  # restore so tearDown's stop() is balanced
        self.assertEqual(resp.status_code, 200)

    def test_persisted_and_restored(self):
        """last_session_end survives a save_state/load_state round-trip."""
        import json as _json
        import tempfile
        from pathlib import Path as _Path
        st = self.harness.HarnessState()
        agent = self.harness.AgentState(self.role, "/tmp/x")
        agent.last_session_end = {"reason": "other", "at": 123.0}
        st.agents[self.role] = agent
        with tempfile.TemporaryDirectory() as d:
            sf = _Path(d) / ".harness-state.json"
            with patch.object(self.harness, "HARNESS_STATE_FILE", sf):
                st.save_state()
                raw = _json.loads(sf.read_text(encoding="utf-8"))
                self.assertEqual(
                    raw["agents"][self.role]["last_session_end"],
                    {"reason": "other", "at": 123.0})
                st2 = self.harness.HarnessState()
                st2.load_state()
                self.assertEqual(
                    st2.agents[self.role].last_session_end,
                    {"reason": "other", "at": 123.0})


class TestPauseStateHelpers12458(unittest.TestCase):
    """#12458 (#12271 slice c): AgentState.active_pause() returns the reason a
    hook explains the agent's silence (so reboot should hold off), each bounded
    by a staleness ceiling; stopfailure_backoff_due() flags a recent throttle."""

    def setUp(self):
        import harness
        self.h = harness
        self.a = harness.AgentState("skill", "/tmp/x")

    def test_in_flight_within_deadline_is_paused(self):
        now = 1000.0
        self.a.in_flight_until = now + 100  # deadline in the future
        self.assertEqual(self.a.active_pause(now), "in-flight")

    def test_in_flight_past_deadline_not_paused(self):
        now = 1000.0
        self.a.in_flight_until = now - 1  # deadline elapsed (tool_call_max hit)
        self.assertIsNone(self.a.active_pause(now))

    def test_in_flight_deadline_too_far_future_not_paused(self):
        """DS-REVIEW-12458-guard F2: a deadline further out than tool_call_max
        (stale flag / backward clock step) must NOT hold indefinitely — the
        ceiling caps the hold at one legitimate tool call."""
        now = 1000.0
        self.a.in_flight_until = now + self.h.TOOL_CALL_MAX_SECONDS + 100
        self.assertIsNone(self.a.active_pause(now))

    def test_compacting_within_ceiling_is_paused(self):
        now = 1000.0
        self.a.compacting_since = now - 10
        self.assertEqual(self.a.active_pause(now), "compacting")

    def test_compacting_past_ceiling_not_paused(self):
        now = 1000.0
        self.a.compacting_since = now - (self.h.COMPACTING_MAX_SECONDS + 1)
        self.assertIsNone(self.a.active_pause(now))

    def test_waiting_within_ceiling_is_paused(self):
        now = 1000.0
        self.a.waiting_since = now - 10
        self.assertEqual(self.a.active_pause(now), "waiting")

    def test_waiting_past_ceiling_not_paused(self):
        now = 1000.0
        self.a.waiting_since = now - (self.h.WAITING_MAX_SECONDS + 1)
        self.assertIsNone(self.a.active_pause(now))

    def test_no_signals_not_paused(self):
        self.assertIsNone(self.a.active_pause(1000.0))

    def test_in_flight_takes_priority_over_waiting(self):
        now = 1000.0
        self.a.in_flight_until = now + 100
        self.a.waiting_since = now - 10
        self.assertEqual(self.a.active_pause(now), "in-flight")

    def test_clock_skew_negative_age_not_paused(self):
        """A flag stamped in the FUTURE (clock skew / corrupt state) must not
        read as an indefinite pause — the `0 <= age` guard rejects it."""
        now = 1000.0
        self.a.compacting_since = now + 500
        self.assertIsNone(self.a.active_pause(now))

    def test_recent_rate_limit_backoff_due(self):
        now = 1000.0
        self.a.last_stop_failure = {"cause": "rate_limit", "at": now - 5}
        self.assertTrue(self.a.stopfailure_backoff_due(now))

    def test_recent_overloaded_backoff_due(self):
        now = 1000.0
        self.a.last_stop_failure = {"cause": "overloaded", "at": now - 5}
        self.assertTrue(self.a.stopfailure_backoff_due(now))

    def test_stale_rate_limit_not_due(self):
        now = 1000.0
        self.a.last_stop_failure = {"cause": "rate_limit",
                                    "at": now - (self.h.STOP_FAILURE_RECENT_SECONDS + 1)}
        self.assertFalse(self.a.stopfailure_backoff_due(now))

    def test_non_throttle_cause_not_due(self):
        """auth/billing failures need operator action, not an auto-backoff."""
        now = 1000.0
        self.a.last_stop_failure = {"cause": "authentication_failed", "at": now - 5}
        self.assertFalse(self.a.stopfailure_backoff_due(now))

    def test_missing_stop_failure_not_due(self):
        self.assertFalse(self.a.stopfailure_backoff_due(1000.0))
        self.a.last_stop_failure = "not-a-dict"
        self.assertFalse(self.a.stopfailure_backoff_due(1000.0))

    def test_null_at_does_not_crash(self):
        """A {'at': null} from a hand-edited state file must not TypeError."""
        now = 1000.0
        self.a.last_stop_failure = {"cause": "rate_limit", "at": None}
        self.assertFalse(self.a.stopfailure_backoff_due(now))

    def test_pause_state_persisted_and_restored(self):
        import json as _json, tempfile
        from pathlib import Path as _Path
        st = self.h.HarnessState()
        a = self.h.AgentState("skill", "/tmp/x")
        a.in_flight_until = 111.0
        a.waiting_since = 222.0
        a.compacting_since = 333.0
        a.last_stop_failure = {"cause": "rate_limit", "at": 444.0}
        st.agents["skill"] = a
        with tempfile.TemporaryDirectory() as d:
            sf = _Path(d) / ".harness-state.json"
            with patch.object(self.h, "HARNESS_STATE_FILE", sf):
                st.save_state()
                st2 = self.h.HarnessState()
                st2.load_state()
        r = st2.agents["skill"]
        self.assertEqual(r.in_flight_until, 111.0)
        self.assertEqual(r.waiting_since, 222.0)
        self.assertEqual(r.compacting_since, 333.0)
        self.assertEqual(r.last_stop_failure, {"cause": "rate_limit", "at": 444.0})


class TestPauseGuard12458(unittest.TestCase):
    """#12458 (#12271 slice c): update_health's reboot decision is GUARDED — a
    dead-PID agent is NOT rebooted while a hook explains the silence (in-flight /
    waiting / compacting), and a recent throttle (StopFailure) backs off instead
    of immediate respawn. AC5: a genuine death with NO pause signal still reboots
    exactly as before."""

    def _make_agent(self, status="running", **pause):
        from harness import HarnessState, AgentState
        hs = HarnessState()
        agent = AgentState("skill", "/clone")
        agent.status = status
        agent.intent = AgentState.INTENT_RUNNING
        agent.claude_pid = 12345
        agent.last_spawn_at = None  # avoid fast-death-window effects unless set
        for k, v in pause.items():
            setattr(agent, k, v)
        hs.set_agent("skill", agent)
        return hs, agent

    def _run(self, hs, now):
        """One update_health poll, claude PID dead. Returns the boot_agent mock."""
        boot = patch("harness.boot_remote.boot_agent",
                     return_value={"success": True, "terminal_pid": 999})
        patches = [
            patch("harness.boot_remote._get_all_roles", return_value=["skill"]),
            patch("harness.boot_remote._get_clone_path", return_value="/clone"),
            patch("harness.boot_remote._is_process_alive", return_value=False),
            patch("harness.reboot_agent._read_claude_pid", return_value=(None, False)),
            patch("harness.time.time", return_value=now),
            patch("harness._log"),
            patch.object(hs, "save_state"),
        ]
        boot_mock = boot.start()
        for p in patches:
            p.start()
        try:
            hs.update_health()
        finally:
            for p in patches:
                p.stop()
            boot.stop()
        return boot_mock

    # --- AC5: genuine death (no pause) still reboots ---
    def test_genuine_death_no_pause_reboots(self):
        now = 10_000.0
        hs, _ = self._make_agent()
        boot = self._run(hs, now)
        boot.assert_called_once_with("skill")
        self.assertEqual(hs.get_agent("skill").status, "starting")

    # --- AC3a: in-flight within tool_call_max → HOLD ---
    def test_in_flight_within_deadline_holds_reboot(self):
        now = 10_000.0
        hs, _ = self._make_agent(in_flight_until=now + 100)
        boot = self._run(hs, now)
        boot.assert_not_called()
        self.assertEqual(hs.get_agent("skill").status, "paused")

    def test_in_flight_past_deadline_reboots(self):
        """AC4: past tool_call_max (deadline elapsed) the agent IS wedged."""
        now = 10_000.0
        hs, _ = self._make_agent(in_flight_until=now - 1)
        boot = self._run(hs, now)
        boot.assert_called_once_with("skill")

    # --- AC3b: waiting → HOLD ---
    def test_waiting_holds_reboot(self):
        now = 10_000.0
        hs, _ = self._make_agent(waiting_since=now - 10)
        boot = self._run(hs, now)
        boot.assert_not_called()
        self.assertEqual(hs.get_agent("skill").status, "paused")

    # --- AC3c: compacting → HOLD ---
    def test_compacting_holds_reboot(self):
        now = 10_000.0
        hs, _ = self._make_agent(compacting_since=now - 10)
        boot = self._run(hs, now)
        boot.assert_not_called()
        self.assertEqual(hs.get_agent("skill").status, "paused")

    # --- AC3d: StopFailure throttle → backoff, not immediate respawn ---
    def test_stopfailure_rate_limit_backs_off(self):
        from harness import CRASH_BACKOFF_BASE_SECONDS
        now = 10_000.0
        hs, _ = self._make_agent(
            last_stop_failure={"cause": "rate_limit", "at": now - 5})
        boot = self._run(hs, now)
        boot.assert_not_called()
        agent = hs.get_agent("skill")
        self.assertEqual(agent.status, "crash-looping")
        self.assertIsNotNone(agent.reboot_blocked_until)
        self.assertGreater(agent.reboot_blocked_until, now)

    def test_graceful_exit_with_throttle_backs_off_without_streak(self):
        """DS-REVIEW-12458-guard F3: a GRACEFUL exit (SessionEnd after spawn)
        that coincides with a recent throttle still BACKS OFF (don't re-hit the
        limit) but must NOT accumulate the #12244 crash streak (the #12418 AC4
        contract — a cooperative exit is not a crash)."""
        now = 10_000.0
        hs, agent = self._make_agent(
            last_spawn_at=now - 10,
            last_session_end={"reason": "other", "at": now - 5},  # after spawn
            last_stop_failure={"cause": "rate_limit", "at": now - 3},
        )
        boot = self._run(hs, now)
        boot.assert_not_called()  # backed off, not respawned
        a = hs.get_agent("skill")
        self.assertEqual(a.status, "crash-looping")
        self.assertIsNotNone(a.reboot_blocked_until)
        # graceful → streak NOT incremented
        self.assertEqual(a.consecutive_fast_deaths, 0)

    def test_stale_stopfailure_does_not_backoff(self):
        """An OLD StopFailure is not a current throttle → normal death path."""
        from harness import STOP_FAILURE_RECENT_SECONDS
        now = 10_000.0
        hs, _ = self._make_agent(
            last_stop_failure={"cause": "rate_limit",
                               "at": now - (STOP_FAILURE_RECENT_SECONDS + 10)})
        boot = self._run(hs, now)
        boot.assert_called_once_with("skill")  # reboots as a normal death

    # --- resume: a held agent whose ceiling has elapsed reboots ---
    def test_held_agent_reboots_once_pause_clears(self):
        now = 10_000.0
        # already "paused", and its in-flight deadline is now in the past
        hs, _ = self._make_agent(status="paused", in_flight_until=now - 1)
        boot = self._run(hs, now)
        boot.assert_called_once_with("skill")
        self.assertEqual(hs.get_agent("skill").status, "starting")

    def test_held_agent_stays_paused_while_pause_active(self):
        now = 10_000.0
        hs, _ = self._make_agent(status="paused", compacting_since=now - 10)
        boot = self._run(hs, now)
        boot.assert_not_called()
        self.assertEqual(hs.get_agent("skill").status, "paused")

    # --- operator stop wins over a pause hold ---
    def test_operator_stop_wins_over_pause(self):
        from harness import AgentState
        now = 10_000.0
        hs, agent = self._make_agent(status="paused", in_flight_until=now + 100)
        agent.intent = AgentState.INTENT_STOPPING
        boot = self._run(hs, now)
        boot.assert_not_called()
        a = hs.get_agent("skill")
        # settles to stopped (intent fulfilled), NOT held forever
        self.assertEqual(a.intent, AgentState.INTENT_STOPPED)


class TestActivityHook12443(unittest.TestCase):
    """#12443: POST /hooks/activity records the activity heartbeat
    (last_activity_at + enriched {event, tool, phase}) on AgentState, exposes it
    via GET /agents/{role}, throttles the state-FILE write (fires per tool
    call), and is fail-open (always 200 — a telemetry hook must never block or
    fail the agent)."""

    def setUp(self):
        import harness
        from fastapi.testclient import TestClient
        self.harness = harness
        self.client = TestClient(harness.app, raise_server_exceptions=False)
        harness.state.start_time = time.time()
        self.role = "skill"
        self._roles = patch.object(
            harness.boot_remote, "_get_all_roles", return_value=[self.role])
        self._roles.start()
        self._save = patch.object(harness.state, "save_state")
        self._save_mock = self._save.start()
        self._uh = patch.object(harness.state, "update_health")
        self._uh.start()
        harness.state.agents.pop(self.role, None)
        # Reset the persistence throttle so the first POST in each test persists.
        harness._last_activity_save_at = 0.0

    def tearDown(self):
        self._uh.stop()
        self._save.stop()
        self._roles.stop()
        self.harness.state.agents.pop(self.role, None)

    def _hdr(self, role=None):
        return {"X-Agent-Role": self.role if role is None else role}

    def test_records_activity_on_agentstate(self):
        resp = self.client.post(
            "/hooks/activity", headers=self._hdr(),
            json={"event": "PostToolUse", "tool": "Bash", "phase": "implement"})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json().get("ok"))
        agent = self.harness.state.agents.get(self.role)
        self.assertIsNotNone(agent)
        self.assertIsInstance(agent.last_activity_at, float)
        self.assertEqual(agent.last_activity["event"], "PostToolUse")
        self.assertEqual(agent.last_activity["tool"], "Bash")
        self.assertEqual(agent.last_activity["phase"], "implement")

    def test_accepts_raw_hook_payload_fields(self):
        """A raw Claude Code hook payload uses hook_event_name / tool_name —
        the endpoint falls back to those when event/tool aren't set."""
        resp = self.client.post(
            "/hooks/activity", headers=self._hdr(),
            json={"hook_event_name": "PostToolUseFailure", "tool_name": "Edit"})
        self.assertEqual(resp.status_code, 200)
        act = self.harness.state.agents[self.role].last_activity
        self.assertEqual(act["event"], "PostToolUseFailure")
        self.assertEqual(act["tool"], "Edit")

    def test_exposed_via_get_agent(self):
        self.client.post("/hooks/activity", headers=self._hdr(),
                         json={"event": "cycle_post"})
        resp = self.client.get(f"/agents/{self.role}")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIsInstance(data.get("last_activity_at"), float)
        self.assertEqual(data["last_activity"]["event"], "cycle_post")

    def test_no_role_header_dropped_but_200(self):
        resp = self.client.post("/hooks/activity", json={"event": "PostToolUse"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("ok"))
        self.assertEqual(resp.json().get("dropped"), "no-role")

    def test_uninterpolated_env_var_role_is_no_role(self):
        resp = self.client.post("/hooks/activity",
                                headers=self._hdr("${SQUIDSQUAD_ROLE}"),
                                json={"event": "PostToolUse"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json().get("dropped"), "no-role")

    def test_unknown_role_dropped_but_200(self):
        resp = self.client.post("/hooks/activity",
                                headers=self._hdr("bogus-role"),
                                json={"event": "PostToolUse"})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.json().get("ok"))
        self.assertNotIn("bogus-role", self.harness.state.agents)

    def test_malformed_body_is_fail_open(self):
        resp = self.client.post(
            "/hooks/activity", content=b"not json",
            headers={**self._hdr(), "Content-Type": "application/json"})
        self.assertEqual(resp.status_code, 200)
        # Still records the heartbeat (the activity FACT is the signal, not the
        # body) — event is just None when the payload is unreadable.
        self.assertIsInstance(
            self.harness.state.agents[self.role].last_activity_at, float)

    def test_save_failure_is_fail_open(self):
        """Even if persistence raises, the hook still answers 200."""
        self._save.stop()
        with patch.object(self.harness.state, "save_state",
                          side_effect=OSError("disk full")):
            resp = self.client.post("/hooks/activity", headers=self._hdr(),
                                    json={"event": "PostToolUse"})
        self._save_mock = self._save.start()  # restore for tearDown balance
        self.assertEqual(resp.status_code, 200)

    def test_disk_write_is_throttled(self):
        """Heartbeats fire per tool call — the in-memory value updates every
        time, but the state-FILE write is rate-limited. Two rapid POSTs persist
        at most once."""
        self.client.post("/hooks/activity", headers=self._hdr(),
                         json={"event": "PostToolUse"})
        first_at = self.harness.state.agents[self.role].last_activity_at
        self.client.post("/hooks/activity", headers=self._hdr(),
                         json={"event": "PostToolUse"})
        second_at = self.harness.state.agents[self.role].last_activity_at
        # In-memory advanced on BOTH calls...
        self.assertGreaterEqual(second_at, first_at)
        # ...but save_state was called at most once (throttled).
        self.assertLessEqual(self._save_mock.call_count, 1)

    def test_persisted_and_restored(self):
        """last_activity_at + last_activity survive a save/load round-trip."""
        import json as _json
        import tempfile
        from pathlib import Path as _Path
        st = self.harness.HarnessState()
        agent = self.harness.AgentState(self.role, "/tmp/x")
        agent.last_activity_at = 456.0
        agent.last_activity = {"at": 456.0, "event": "PostToolUse", "tool": "Bash"}
        st.agents[self.role] = agent
        with tempfile.TemporaryDirectory() as d:
            sf = _Path(d) / ".harness-state.json"
            with patch.object(self.harness, "HARNESS_STATE_FILE", sf):
                st.save_state()
                raw = _json.loads(sf.read_text(encoding="utf-8"))
                self.assertEqual(
                    raw["agents"][self.role]["last_activity_at"], 456.0)
                st2 = self.harness.HarnessState()
                st2.load_state()
                self.assertEqual(st2.agents[self.role].last_activity_at, 456.0)
                self.assertEqual(
                    st2.agents[self.role].last_activity["tool"], "Bash")


class TestPauseHook12458(unittest.TestCase):
    """#12458: POST /hooks/pause records pause-explaining lifecycle signals
    (Notification→waiting, PreCompact→compacting, PostCompact→clear,
    StopFailure→cause) and is fail-open; and /hooks/activity manages the
    in-flight tool-call window (PreToolUse opens, Post* closes) + clears
    waiting."""

    def setUp(self):
        import harness
        from fastapi.testclient import TestClient
        self.h = harness
        self.client = TestClient(harness.app, raise_server_exceptions=False)
        harness.state.start_time = time.time()
        self.role = "skill"
        self._roles = patch.object(
            harness.boot_remote, "_get_all_roles", return_value=[self.role])
        self._roles.start()
        self._save = patch.object(harness.state, "save_state")
        self._save.start()
        self._uh = patch.object(harness.state, "update_health")
        self._uh.start()
        harness.state.agents.pop(self.role, None)
        harness._last_activity_save_at = 0.0

    def tearDown(self):
        self._uh.stop()
        self._save.stop()
        self._roles.stop()
        self.h.state.agents.pop(self.role, None)

    def _hdr(self, role=None):
        return {"X-Agent-Role": self.role if role is None else role}

    def _agent(self):
        return self.h.state.agents.get(self.role)

    # --- /hooks/pause dispatch ---
    def test_notification_sets_waiting(self):
        r = self.client.post("/hooks/pause", headers=self._hdr(),
                             json={"event": "Notification"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        self.assertIsInstance(self._agent().waiting_since, float)

    def test_precompact_sets_compacting_postcompact_clears(self):
        self.client.post("/hooks/pause", headers=self._hdr(),
                         json={"event": "PreCompact"})
        self.assertIsInstance(self._agent().compacting_since, float)
        self.client.post("/hooks/pause", headers=self._hdr(),
                         json={"event": "PostCompact"})
        self.assertIsNone(self._agent().compacting_since)

    def test_stopfailure_records_cause(self):
        r = self.client.post("/hooks/pause", headers=self._hdr(),
                             json={"hook_event_name": "StopFailure",
                                   "reason": "rate_limit"})
        self.assertEqual(r.status_code, 200)
        sf = self._agent().last_stop_failure
        self.assertEqual(sf["cause"], "rate_limit")
        self.assertIn("at", sf)

    def test_stopfailure_unknown_cause_defaults(self):
        """F5: matcher is NOT a cause source — a payload with only a matcher
        records 'unknown' (→ safe default, no backoff)."""
        self.client.post("/hooks/pause", headers=self._hdr(),
                         json={"event": "StopFailure", "matcher": "rate_limit"})
        self.assertEqual(self._agent().last_stop_failure["cause"], "unknown")

    def test_unknown_event_dropped_but_200(self):
        r = self.client.post("/hooks/pause", headers=self._hdr(),
                             json={"event": "Bogus"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("dropped"), "unknown-event")

    def test_no_role_dropped_but_200(self):
        r = self.client.post("/hooks/pause", json={"event": "Notification"})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json().get("dropped"), "no-role")

    def test_unknown_role_dropped_but_200(self):
        r = self.client.post("/hooks/pause", headers=self._hdr("bogus"),
                             json={"event": "Notification"})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("bogus", self.h.state.agents)

    def test_malformed_body_fail_open(self):
        r = self.client.post("/hooks/pause", content=b"not json",
                             headers={**self._hdr(), "Content-Type": "application/json"})
        self.assertEqual(r.status_code, 200)  # empty body → unknown-event, still 200

    # --- /hooks/activity in-flight management ---
    def test_pretooluse_opens_in_flight_window(self):
        r = self.client.post("/hooks/activity", headers=self._hdr(),
                             json={"event": "PreToolUse", "tool": "Bash"})
        self.assertEqual(r.status_code, 200)
        agent = self._agent()
        self.assertIsInstance(agent.in_flight_until, float)
        # deadline is ~now + tool_call_max
        self.assertGreater(agent.in_flight_until, time.time() + 1)

    def test_posttooluse_closes_in_flight_window(self):
        self.client.post("/hooks/activity", headers=self._hdr(),
                         json={"event": "PreToolUse"})
        self.assertIsNotNone(self._agent().in_flight_until)
        self.client.post("/hooks/activity", headers=self._hdr(),
                         json={"event": "PostToolUse"})
        self.assertIsNone(self._agent().in_flight_until)

    def test_userpromptsubmit_records_heartbeat_no_in_flight_13213(self):
        """#13213 AC2/AC4/AC5: a UserPromptSubmit heartbeat advances
        last_activity_at and records the event (so progress_liveness/the shadow
        verdict sees the agent received input), but is a PLAIN heartbeat — it
        does NOT open an in-flight window. That is deliberate: an in-flight
        window would MASK the freeze-after-prompt-before-first-tool-call gap this
        signal exists to expose."""
        r = self.client.post("/hooks/activity", headers=self._hdr(),
                             json={"event": "UserPromptSubmit"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))
        agent = self._agent()
        # AC2: heartbeat recorded — last_activity_at advanced, event stamped.
        self.assertIsInstance(agent.last_activity_at, float)
        self.assertEqual(agent.last_activity["event"], "UserPromptSubmit")
        # AC4: plain heartbeat — NOT an in-flight opener (only PreToolUse opens).
        self.assertIsNone(agent.in_flight_until)

    def test_userpromptsubmit_does_not_disturb_open_in_flight_13213(self):
        """A UserPromptSubmit arriving while a tool call is in flight must not
        clear the in-flight window (it is neither the PreToolUse opener nor the
        Post* closer) — only a real tool-call boundary moves that window."""
        self.client.post("/hooks/activity", headers=self._hdr(),
                         json={"event": "PreToolUse"})
        opened = self._agent().in_flight_until
        self.assertIsNotNone(opened)
        self.client.post("/hooks/activity", headers=self._hdr(),
                         json={"event": "UserPromptSubmit"})
        # in-flight window untouched; only Post* closes it.
        self.assertEqual(self._agent().in_flight_until, opened)

    def test_activity_clears_waiting(self):
        # set waiting via a Notification, then any activity clears it
        self.client.post("/hooks/pause", headers=self._hdr(),
                         json={"event": "Notification"})
        self.assertIsNotNone(self._agent().waiting_since)
        self.client.post("/hooks/activity", headers=self._hdr(),
                         json={"event": "PostToolUse"})
        self.assertIsNone(self._agent().waiting_since)


if __name__ == "__main__":
    unittest.main()
