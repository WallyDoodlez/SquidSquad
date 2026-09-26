"""#14131 + #14132 — two ways a harness-managed agent stayed dead or frozen.

#14131: a LIVE agent stuck at intent=deploying (it never emits ack-stop, e.g. a
deaf session per #14114) was never recovered. The dead-PID deploy-window
fallback only covers an agent whose PID died. The health poller now classifies a
live deploy stall (AgentState.deploy_stall_action) and either recovers it through
the normal pull-first deploy sequence (idle past the window, or past the hard
ceiling) or surfaces ONE deploy-error to pm (still active past the window).

#14132: an idle `/restart` kills the agent, but an idle agent is exactly the one
with waiting_since set, so the #12458 pause guard read the restart's own kill as
an explained "waiting" pause and held the respawn for up to 30 min. The idle
immediate kill now stamps operator_force_at, and the pause guard skips a
harness-requested kill.

Both are driven through the real HarnessState.update_health() and the real
restart_agent() endpoint, with only process/boot/IO seams mocked.
"""

import asyncio
import sys
import tempfile
import threading
import time as _real_time
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import harness  # noqa: E402
from harness import AgentState, HarnessState  # noqa: E402

WINDOW = harness._DEPLOY_WINDOW_SECONDS
CEILING = harness._DEPLOY_ALIVE_CEILING_SECONDS


def _deploying_agent(now, age, activity_age=None, pid=4242):
    a = AgentState("skill", "/clone")
    a.status = "running"
    a.intent = AgentState.INTENT_DEPLOYING
    a.intent_set_at = now - age
    a.claude_pid = pid
    a.last_spawn_at = now - 10_000
    a.bootup_complete = True
    a.last_activity_at = None if activity_age is None else now - activity_age
    return a


def _poll(hs, now, alive, boot_result=None):
    """Run one real update_health() poll with the process/boot seams mocked.
    Returns the boot_agent mock."""
    boot_result = boot_result or {"success": True, "terminal_pid": 999,
                                  "action": "spawn"}
    patches = [
        mock.patch("harness.boot_remote._get_all_roles", return_value=["skill"]),
        mock.patch("harness.boot_remote._get_clone_path", return_value="/clone"),
        mock.patch("harness.boot_remote._is_process_alive", return_value=alive),
        mock.patch("harness.process_utils.is_claude_process_alive",
                   return_value=alive),
        mock.patch("harness.reboot_agent.write_claude_pid", return_value=True),
        mock.patch("harness.reboot_agent._read_claude_pid",
                   return_value=(None, False)),
        mock.patch("harness.time.time", return_value=now),
        mock.patch("harness._log"),
        mock.patch.object(hs, "save_state"),
    ]
    boot = mock.patch("harness.boot_remote.boot_agent", return_value=boot_result)
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


def _wait_inflight_clear(role, timeout=5.0):
    deadline = _real_time.monotonic() + timeout
    while _real_time.monotonic() < deadline:
        with harness._deploy_inflight_lock:
            if role not in harness._deploy_inflight:
                return True
        _real_time.sleep(0.01)
    return False


# ---------------------------------------------------------------------------
# #14131 — deploy_stall_action classification
# ---------------------------------------------------------------------------

class TestDeployStallAction:
    NOW = 100_000.0

    def test_not_deploying_is_none(self):
        a = _deploying_agent(self.NOW, WINDOW + 60)
        a.intent = AgentState.INTENT_RUNNING
        assert a.deploy_stall_action(self.NOW) is None

    def test_no_clock_is_none(self):
        a = _deploying_agent(self.NOW, WINDOW + 60)
        a.intent_set_at = None
        assert a.deploy_stall_action(self.NOW) is None

    def test_inside_window_is_none(self):
        """AC3: the normal deploy-halt window is untouched."""
        a = _deploying_agent(self.NOW, WINDOW - 1)
        assert a.deploy_stall_action(self.NOW) is None

    def test_idle_past_window_recovers(self):
        a = _deploying_agent(self.NOW, WINDOW + 60, activity_age=WINDOW + 30)
        assert a.deploy_stall_action(self.NOW) == "recover"

    def test_never_active_past_window_recovers(self):
        a = _deploying_agent(self.NOW, WINDOW + 60, activity_age=None)
        assert a.deploy_stall_action(self.NOW) == "recover"

    def test_active_past_window_surfaces(self):
        a = _deploying_agent(self.NOW, WINDOW + 60, activity_age=30)
        assert a.deploy_stall_action(self.NOW) == "surface"

    def test_active_past_ceiling_recovers(self):
        a = _deploying_agent(self.NOW, CEILING + 1, activity_age=5)
        assert a.deploy_stall_action(self.NOW) == "recover"


# ---------------------------------------------------------------------------
# #14131 — health poller wiring (AC1/AC2/AC3)
# ---------------------------------------------------------------------------

class TestLiveDeployStallPoller:
    NOW = 200_000.0

    def setup_method(self):
        with harness._deploy_inflight_lock:
            harness._deploy_inflight.clear()

    def test_alive_idle_past_window_runs_deploy_sequence_once(self):
        """AC1/AC2: a live, idle agent at deploying past the window is recovered
        via the deploy sequence (which force-kills + respawns), started once
        even across repeated polls while it is in flight. The newest
        deploy-signal id is passed so the cursor is advanced past it."""
        hs = HarnessState()
        hs.set_agent("skill", _deploying_agent(self.NOW, WINDOW + 120,
                                               activity_age=WINDOW + 60))
        sig = {"id": "sig14131abc", "event_type": "deploy-signal",
               "role": "harness", "payload": {"target_alias": "skill"}}
        release = threading.Event()
        seq = mock.Mock(side_effect=lambda *a, **k: release.wait(5))
        with mock.patch("harness._run_deploy_sequence", seq), \
             mock.patch.object(harness.event_stream, "get_all",
                               return_value=[sig]):
            _poll(hs, self.NOW, alive=True)
            _poll(hs, self.NOW + 5, alive=True)   # still in flight
            release.set()
            assert _wait_inflight_clear("skill")
        seq.assert_called_once_with("skill", "sig14131abc")

    def test_alive_active_past_window_surfaces_once_no_deploy(self):
        """AC1 (surface branch): an agent still heartbeating past the window is
        not killed; exactly ONE deploy-error goes to pm per deploy intent."""
        hs = HarnessState()
        hs.set_agent("skill", _deploying_agent(self.NOW, WINDOW + 60,
                                               activity_age=20))
        seq = mock.Mock()
        with mock.patch("harness._run_deploy_sequence", seq), \
             mock.patch("harness._emit_event") as emit:
            _poll(hs, self.NOW, alive=True)
            hs.get_agent("skill").last_activity_at = self.NOW + 3
            _poll(hs, self.NOW + 5, alive=True)
        seq.assert_not_called()
        errs = [c for c in emit.call_args_list if c.args[0] == "deploy-error"]
        assert len(errs) == 1
        payload = errs[0].kwargs["payload"]
        assert errs[0].args[1] == "pm"
        assert payload["failed_role"] == "skill"
        assert payload["stage"] == "halt-timeout"

    def test_alive_inside_window_untouched(self):
        """AC3: inside the deploy window the live agent is left alone (the
        normal ack-stop → deploy path owns it)."""
        hs = HarnessState()
        hs.set_agent("skill", _deploying_agent(self.NOW, WINDOW - 30))
        seq = mock.Mock()
        with mock.patch("harness._run_deploy_sequence", seq), \
             mock.patch("harness._emit_event") as emit:
            _poll(hs, self.NOW, alive=True)
        seq.assert_not_called()
        assert not [c for c in emit.call_args_list
                    if c.args[0] == "deploy-error"]
        a = hs.get_agent("skill")
        assert a.intent == AgentState.INTENT_DEPLOYING

    def test_dead_past_window_existing_fallback_unchanged(self):
        """AC2 companion: the existing DEAD-PID fallback still settles the agent
        back to running for auto-respawn, without starting a deploy thread."""
        hs = HarnessState()
        hs.set_agent("skill", _deploying_agent(self.NOW, WINDOW + 60))
        seq = mock.Mock()
        with mock.patch("harness._run_deploy_sequence", seq):
            _poll(hs, self.NOW, alive=False)
        seq.assert_not_called()
        a = hs.get_agent("skill")
        assert a.intent == AgentState.INTENT_RUNNING
        assert a.status == "running"

    def test_dead_inside_window_settles_deploying(self):
        """AC3: the normal deploy-halt death inside the window settles to
        status=deploying (no crash respawn, no stall recovery)."""
        hs = HarnessState()
        hs.set_agent("skill", _deploying_agent(self.NOW, WINDOW - 60))
        seq = mock.Mock()
        with mock.patch("harness._run_deploy_sequence", seq):
            boot = _poll(hs, self.NOW, alive=False)
        seq.assert_not_called()
        boot.assert_not_called()
        assert hs.get_agent("skill").status == "deploying"


class TestDeployInflightGuard:
    def setup_method(self):
        with harness._deploy_inflight_lock:
            harness._deploy_inflight.clear()

    def test_second_start_refused_while_in_flight(self):
        release = threading.Event()
        seq = mock.Mock(side_effect=lambda *a, **k: release.wait(5))
        with mock.patch("harness._run_deploy_sequence", seq):
            assert harness._start_deploy_thread("dm", "e1") is True
            assert harness._start_deploy_thread("dm", "e2") is False
            release.set()
            assert _wait_inflight_clear("dm")
            # Cleared on completion → a later deploy can start again.
            assert harness._start_deploy_thread("dm", "e3") is True
            assert _wait_inflight_clear("dm")
        assert [c.args for c in seq.call_args_list] == [("dm", "e1"),
                                                        ("dm", "e3")]

    def test_inflight_cleared_when_sequence_raises(self):
        seq = mock.Mock(side_effect=RuntimeError("boom"))
        with mock.patch("harness._run_deploy_sequence", seq), \
             mock.patch("threading.excepthook"):
            assert harness._start_deploy_thread("dm") is True
            assert _wait_inflight_clear("dm")

    def test_ack_stop_deploy_halted_routes_through_guard(self):
        """AC3: the normal ack-stop(deploy-halted) path still starts the deploy
        sequence with the signal's event id — now via the in-flight guard."""
        import inspect
        src = inspect.getsource(harness.receive_event)
        idx = src.find('"deploy-halted"')
        block = src[idx:idx + 4000]
        assert "_start_deploy_thread(role, ack_event_id)" in block
        assert "target=_run_deploy_sequence" not in block

    def test_latest_deploy_signal_id_picks_newest_for_role(self):
        evs = [
            {"id": "a", "event_type": "deploy-signal",
             "payload": {"target_alias": "dm"}},
            {"id": "b", "event_type": "deploy-signal",
             "payload": {"target_alias": "qa"}},
            {"id": "c", "event_type": "deploy-signal",
             "payload": {"target_alias": "dm"}},
            {"id": "d", "event_type": "status-transition", "payload": {}},
        ]
        with mock.patch.object(harness.event_stream, "get_all",
                               return_value=evs):
            assert harness._latest_deploy_signal_id("dm") == "c"
            assert harness._latest_deploy_signal_id("pm") is None


# ---------------------------------------------------------------------------
# #14132 — idle /restart vs the #12458 pause guard
# ---------------------------------------------------------------------------

class TestIdleRestartBypassesPauseGuard:
    NOW = 300_000.0

    def _restart(self, clone, kill_side_effect=None, force=False):
        from harness import state, restart_agent
        with mock.patch("harness._NO_AUTO_REBOOT", False), \
             mock.patch("harness.boot_remote") as boot, \
             mock.patch.object(state, "save_state"), \
             mock.patch("harness.reboot_agent._read_claude_pid",
                        return_value=(4321, True)), \
             mock.patch("harness.reboot_agent._kill_process",
                        side_effect=kill_side_effect) as kill, \
             mock.patch("harness.time.time", return_value=self.NOW), \
             mock.patch("harness._log"):
            boot._get_all_roles.return_value = ["skill"]
            boot._get_clone_path.return_value = str(clone)
            res = asyncio.run(restart_agent("skill", force=force))
        return res, kill

    def _idle_waiting_agent(self, clone):
        from harness import state
        state.agents.clear()
        a = AgentState("skill", str(clone))
        a.status = "running"
        a.intent = AgentState.INTENT_RUNNING
        a.claude_pid = 4321
        a.last_spawn_at = self.NOW - 5000
        a.bootup_complete = True
        a.waiting_since = self.NOW - 800      # idle at its prompt (13 min)
        state.set_agent("skill", a)
        d = Path(clone) / ".squidsquad" / "skill"
        d.mkdir(parents=True, exist_ok=True)
        (d / "current-state").write_text("idle", encoding="utf-8")
        return state

    def test_idle_restart_with_waiting_since_respawns_next_poll(self):
        """AC1/AC2: an idle /restart stamps the kill marker, and the next poll
        respawns the agent instead of holding it as a 'waiting' pause."""
        with tempfile.TemporaryDirectory() as clone:
            state = self._idle_waiting_agent(clone)
            res, kill = self._restart(clone)
            kill.assert_called_once_with(4321)
            assert res["immediate"] is True
            a = state.get_agent("skill")
            assert a.operator_force_at == self.NOW
            assert a.intent == AgentState.INTENT_RESTARTING
            # The pause signal would otherwise explain the death.
            assert a.active_pause(self.NOW + 5) == "waiting"

            hs = HarnessState()
            hs.set_agent("skill", a)
            boot = _poll(hs, self.NOW + 5, alive=False)
            boot.assert_called_once_with("skill")
            after = hs.get_agent("skill")
            assert after.status != "paused"
            assert after.operator_force_at is None     # one-shot, consumed

    def test_force_restart_with_waiting_since_respawns_next_poll(self):
        with tempfile.TemporaryDirectory() as clone:
            state = self._idle_waiting_agent(clone)
            (Path(clone) / ".squidsquad" / "skill" / "current-state").write_text(
                "working", encoding="utf-8")
            self._restart(clone, force=True)
            hs = HarnessState()
            hs.set_agent("skill", state.get_agent("skill"))
            boot = _poll(hs, self.NOW + 5, alive=False)
            boot.assert_called_once_with("skill")

    def test_failed_kill_clears_marker(self):
        """A kill that fails leaves the agent alive — the marker is dropped so a
        later natural death of this spawn is classified normally."""
        with tempfile.TemporaryDirectory() as clone:
            state = self._idle_waiting_agent(clone)
            res, _ = self._restart(clone, kill_side_effect=OSError("denied"))
            assert res["immediate"] is False
            assert state.get_agent("skill").operator_force_at is None

    def test_busy_graceful_restart_does_not_stamp(self):
        with tempfile.TemporaryDirectory() as clone:
            state = self._idle_waiting_agent(clone)
            (Path(clone) / ".squidsquad" / "skill" / "current-state").write_text(
                "working", encoding="utf-8")
            res, kill = self._restart(clone)
            kill.assert_not_called()
            assert res["immediate"] is False
            assert state.get_agent("skill").operator_force_at is None

    def test_unexplained_death_while_waiting_keeps_hold(self):
        """AC3 regression: a genuine death while waiting (no restart, no marker)
        is still held as an explained pause by #12458."""
        hs = HarnessState()
        a = AgentState("skill", "/clone")
        a.status = "running"
        a.intent = AgentState.INTENT_RUNNING
        a.claude_pid = 4321
        a.last_spawn_at = self.NOW - 5000
        a.bootup_complete = True
        a.waiting_since = self.NOW - 800
        hs.set_agent("skill", a)
        boot = _poll(hs, self.NOW, alive=False)
        boot.assert_not_called()
        assert hs.get_agent("skill").status == "paused"

    def test_stale_marker_from_prior_spawn_keeps_hold(self):
        """A marker older than the current spawn does not excuse the pause."""
        hs = HarnessState()
        a = AgentState("skill", "/clone")
        a.status = "running"
        a.intent = AgentState.INTENT_RUNNING
        a.claude_pid = 4321
        a.last_spawn_at = self.NOW - 5000
        a.operator_force_at = self.NOW - 6000
        a.bootup_complete = True
        a.waiting_since = self.NOW - 800
        hs.set_agent("skill", a)
        boot = _poll(hs, self.NOW, alive=False)
        boot.assert_not_called()
        assert hs.get_agent("skill").status == "paused"
