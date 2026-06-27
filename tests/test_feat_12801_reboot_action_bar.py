"""#12801 — TUI bottom action bar with reboot (per-agent / all, busy-aware, force).

Three layers, mirroring the implementation seams:
  A. Harness lifecycle (test_harness-style): the ``force`` param on
     ``/agents/{role}/restart`` kills immediately + stamps ``operator_force_at``;
     the health-poller death classifier excludes an operator-force death from the
     #12244 crash streak (AC6); ``/agents/all/restart`` fans out; the marker is
     transient across a harness restart.
  B. Harness HTTP client (``references/tui/harness_client``): ``post_json`` /
     ``restart_agent`` / ``restart_all`` shape the POST + force suffix and degrade
     gracefully.
  C. App action dispatch (Textual headless Pilot): the action bar routes a
     selected-agent reboot (graceful), a reboot-all, and a CONFIRMED force reboot
     to the right client calls — and busy state is surfaced (AC3/AC5).
"""

import sys
from pathlib import Path
from unittest import mock

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))
sys.path.insert(0, str(REPO / "references" / "tui"))


# ---------------------------------------------------------------------------
# A. Harness lifecycle: force reboot + crash-streak exclusion (AC4/AC6)
# ---------------------------------------------------------------------------

class TestForceRebootEndpoint:
    def _setup(self, current_state_text=None):
        import harness
        from harness import state, AgentState
        state.agents.clear()
        state.set_agent("skill", AgentState("skill", "/clone"))
        return harness

    def test_force_kills_immediately_and_stamps_marker(self):
        """force=True kills the claude PID immediately (overriding busy) and
        stamps operator_force_at so the death is later classified non-crash."""
        import asyncio
        harness = self._setup()
        from harness import state, restart_agent
        with mock.patch("harness._NO_AUTO_REBOOT", False), \
             mock.patch("harness.boot_remote") as boot, \
             mock.patch.object(state, "save_state"), \
             mock.patch("harness.reboot_agent._read_claude_pid",
                        return_value=(4321, True)), \
             mock.patch("harness.reboot_agent._kill_process") as kill, \
             mock.patch("harness.time.time", return_value=5000.0), \
             mock.patch("harness._log"):
            boot._get_all_roles.return_value = ["skill"]
            boot._get_clone_path.return_value = "/clone"
            # current-state file absent → reads as NOT idle (busy); force must
            # still kill immediately.
            res = asyncio.run(restart_agent("skill", force=True))
        kill.assert_called_once_with(4321)
        assert res["forced"] is True
        assert res["immediate"] is True
        assert state.get_agent("skill").operator_force_at == 5000.0

    def test_graceful_busy_does_not_kill_or_stamp(self):
        """force=False on a busy agent queues intent=restarting (no immediate
        kill, no operator_force_at) — graceful path preserved."""
        import asyncio
        harness = self._setup()
        from harness import state, restart_agent, AgentState
        with mock.patch("harness._NO_AUTO_REBOOT", False), \
             mock.patch("harness.boot_remote") as boot, \
             mock.patch.object(state, "save_state"), \
             mock.patch("harness.reboot_agent._read_claude_pid",
                        return_value=(4321, True)), \
             mock.patch("harness.reboot_agent._kill_process") as kill, \
             mock.patch("harness.time.time", return_value=5000.0), \
             mock.patch("harness._log"):
            boot._get_all_roles.return_value = ["skill"]
            boot._get_clone_path.return_value = "/clone"
            # No current-state file → not "idle" → graceful queues, no kill.
            res = asyncio.run(restart_agent("skill", force=False))
        kill.assert_not_called()
        assert res["immediate"] is False
        assert state.get_agent("skill").operator_force_at is None
        assert state.get_agent("skill").intent == AgentState.INTENT_RESTARTING


class TestOperatorForceClassification:
    def test_operator_force_death_predicate(self):
        from harness import AgentState
        a = AgentState("skill", "/c")
        a.last_spawn_at = 100.0
        assert a.operator_force_death() is False          # marker None
        a.operator_force_at = 50.0
        assert a.operator_force_death() is False           # stale (< spawn)
        a.operator_force_at = 150.0
        assert a.operator_force_death() is True             # after spawn

    def test_operator_force_death_not_counted_toward_streak(self):
        """AC6: an operator FORCE death at threshold-1 must NOT increment the
        #12244 crash streak (it has no SessionEnd but is operator-initiated) and
        the one-shot marker is consumed."""
        from harness import HarnessState, AgentState, FAST_DEATH_THRESHOLD
        now = 10_000.0
        hs = HarnessState()
        agent = AgentState("skill", "/clone")
        agent.status = "running"
        agent.intent = AgentState.INTENT_RUNNING
        agent.claude_pid = 12345
        agent.last_spawn_at = now - 10
        agent.consecutive_fast_deaths = FAST_DEATH_THRESHOLD - 1
        agent.operator_force_at = now - 5   # after spawn → operator-initiated
        hs.set_agent("skill", agent)
        boot = self._run(hs, now)
        boot.assert_called_once_with("skill")   # respawned, NOT backed off
        a = hs.get_agent("skill")
        assert a.consecutive_fast_deaths == FAST_DEATH_THRESHOLD - 1  # not ++'d
        assert a.status != "crash-looping"
        assert a.operator_force_at is None       # marker consumed

    def _run(self, hs, fake_now):
        boot = mock.patch("harness.boot_remote.boot_agent",
                          return_value={"success": True, "terminal_pid": 999,
                                        "action": "spawn"})
        patches = [
            mock.patch("harness.boot_remote._get_all_roles", return_value=["skill"]),
            mock.patch("harness.boot_remote._get_clone_path", return_value="/clone"),
            mock.patch("harness.boot_remote._is_process_alive", return_value=False),
            mock.patch("harness.process_utils.is_claude_process_alive",
                       return_value=False),
            mock.patch("harness.reboot_agent.write_claude_pid", return_value=True),
            mock.patch("harness.reboot_agent._read_claude_pid",
                       return_value=(None, False)),
            mock.patch("harness.time.time", return_value=fake_now),
            mock.patch("harness._log"),
            mock.patch.object(hs, "save_state"),
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


class TestForceMarkerTransient:
    def test_marker_not_restored_across_restart(self):
        """operator_force_at is harness-session-owned (like RESTARTING intent):
        a value persisted to the state file must NOT be resurrected on load —
        else the next natural crash would be mis-classified as operator-forced."""
        import tempfile
        from harness import HarnessState, AgentState
        with tempfile.TemporaryDirectory() as tmp:
            sf = Path(tmp) / ".harness-state.json"
            with mock.patch("harness.HARNESS_STATE_FILE", sf):
                hs = HarnessState()
                a = AgentState("skill", "/c")
                a.operator_force_at = 777.0
                hs.set_agent("skill", a)
                hs.save_state()
                hs2 = HarnessState()
                with mock.patch("harness._log"):
                    hs2.load_state()
                assert hs2.get_agent("skill").operator_force_at is None


class TestRestartAllEndpoint:
    def test_restart_all_fans_out_with_force(self):
        import asyncio
        import harness
        from harness import state, restart_all
        state.agents.clear()
        with mock.patch("harness.boot_remote") as boot, \
             mock.patch("harness.restart_agent",
                        new=mock.AsyncMock(return_value={"role": "x",
                                                         "success": True,
                                                         "forced": True})) as ra, \
             mock.patch("harness._log"):
            boot._get_all_roles.return_value = ["pm", "skill", "qa"]
            res = asyncio.run(restart_all(force=True))
        assert {r["role"] for r in res["results"]} == {"pm", "skill", "qa"}
        # every per-role call carried force=True
        assert all(c.kwargs.get("force") is True for c in ra.await_args_list)
        assert len(ra.await_args_list) == 3


# ---------------------------------------------------------------------------
# B. Harness HTTP client — POST helpers
# ---------------------------------------------------------------------------

class TestHarnessClientPost:
    def test_restart_agent_url_and_force_suffix(self):
        import harness_client as hc
        captured = {}

        def fake_post(base_url, path, *, timeout=5):
            captured["base"] = base_url
            captured["path"] = path
            return True, {"ok": True}

        with mock.patch.object(hc, "post_json", side_effect=fake_post):
            ok, _ = hc.restart_agent("http://h", "skill", force=False)
            assert ok and captured["path"] == "/agents/skill/restart"
            hc.restart_agent("http://h", "skill", force=True)
            assert captured["path"] == "/agents/skill/restart?force=true"

    def test_restart_all_force_suffix(self):
        import harness_client as hc
        captured = {}
        with mock.patch.object(hc, "post_json",
                               side_effect=lambda b, p, **k: captured.update(p=p) or (True, {})):
            hc.restart_all("http://h", force=True)
            assert captured["p"] == "/agents/all/restart?force=true"
            hc.restart_all("http://h", force=False)
            assert captured["p"] == "/agents/all/restart"

    def test_post_json_ok(self):
        import io
        import harness_client as hc

        class _Resp:
            def __enter__(self): return self
            def __exit__(self, *a): return False
            def read(self): return b'{"action":"restart","success":true}'

        with mock.patch("harness_client.urllib.request.urlopen",
                        return_value=_Resp()):
            ok, payload = hc.post_json("http://h", "/agents/skill/restart")
        assert ok is True
        assert payload["success"] is True

    def test_post_json_transport_error_returns_reason(self):
        import harness_client as hc
        import urllib.error
        with mock.patch("harness_client.urllib.request.urlopen",
                        side_effect=urllib.error.URLError("refused")):
            ok, payload = hc.post_json("http://h", "/agents/skill/restart")
        assert ok is False
        assert "error" in payload


# ---------------------------------------------------------------------------
# C. App action dispatch — Textual headless Pilot
# ---------------------------------------------------------------------------

pytest.importorskip("textual", reason="TUI dep (requirements-tui.txt)")
import app as tui_app  # noqa: E402


def _status(now):
    return {
        "harness": {"status": "running", "port": 7373},
        "agents": [
            {"role": "skill", "status": "running", "intent": "running",
             "current_cycle": "12801", "last_activity_at": now - 5, "lag": 0},
            {"role": "pm", "status": "running", "intent": "running",
             "current_cycle": None, "last_activity_at": now - 9, "lag": 0},
        ],
    }


@pytest.mark.asyncio
async def test_action_bar_lists_reboot(monkeypatch):
    """AC1: the bottom action bar (Footer) advertises the reboot actions."""
    import time
    monkeypatch.setattr(tui_app.hc, "fetch_status",
                        lambda *a, **k: _status(time.time()))
    app = tui_app.HarnessTUI(base_url="http://test")
    actions = {b.action for b in app.BINDINGS}
    assert {"reboot_selected", "reboot_all", "force_selected"} <= actions


@pytest.mark.asyncio
async def test_reboot_selected_dispatches_graceful(monkeypatch):
    """AC2/AC4: rebooting the selected (cursor) agent calls restart_agent with
    force=False for that role."""
    import time
    now = time.time()
    monkeypatch.setattr(tui_app.hc, "fetch_status", lambda *a, **k: _status(now))
    calls = []
    monkeypatch.setattr(tui_app.hc, "restart_agent",
                        lambda base, role, **k: calls.append((role, k.get("force"))) or (True, {}))
    app = tui_app.HarnessTUI(base_url="http://test")
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        from textual.widgets import DataTable
        app.query_one("#agents", DataTable).move_cursor(row=0)
        app.action_reboot_selected()
        await app.workers.wait_for_complete()
        await pilot.pause()
    assert calls == [("skill", False)]


@pytest.mark.asyncio
async def test_reboot_all_dispatches(monkeypatch):
    """AC2: reboot-all calls restart_all (graceful)."""
    import time
    now = time.time()
    monkeypatch.setattr(tui_app.hc, "fetch_status", lambda *a, **k: _status(now))
    calls = []
    monkeypatch.setattr(tui_app.hc, "restart_all",
                        lambda base, **k: calls.append(k.get("force")) or (True, {}))
    app = tui_app.HarnessTUI(base_url="http://test")
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        app.action_reboot_all()
        await app.workers.wait_for_complete()
        await pilot.pause()
    assert calls == [False]


@pytest.mark.asyncio
async def test_force_requires_confirm_then_dispatches_force(monkeypatch):
    """AC5: force reboot is gated behind ConfirmReboot; confirming dispatches
    restart_agent with force=True for the selected agent."""
    import time
    now = time.time()
    monkeypatch.setattr(tui_app.hc, "fetch_status", lambda *a, **k: _status(now))
    calls = []
    monkeypatch.setattr(tui_app.hc, "restart_agent",
                        lambda base, role, **k: calls.append((role, k.get("force"))) or (True, {}))
    app = tui_app.HarnessTUI(base_url="http://test")
    pushed = {}

    def fake_push(screen, callback=None):
        pushed["screen"] = screen
        pushed["callback"] = callback

    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        from textual.widgets import DataTable
        app.query_one("#agents", DataTable).move_cursor(row=0)
        monkeypatch.setattr(app, "push_screen", fake_push)
        app.action_force_selected()
        # A confirm dialog was pushed (distinct, confirmed action — AC5).
        assert isinstance(pushed["screen"], tui_app.ConfirmReboot)
        # No dispatch yet — confirmation pending.
        assert calls == []
        # Operator confirms → force dispatch fires.
        pushed["callback"](True)
        await app.workers.wait_for_complete()
        await pilot.pause()
    assert calls == [("skill", True)]


@pytest.mark.asyncio
async def test_force_cancel_does_not_dispatch(monkeypatch):
    """AC5: cancelling the confirm dialog must NOT reboot."""
    import time
    now = time.time()
    monkeypatch.setattr(tui_app.hc, "fetch_status", lambda *a, **k: _status(now))
    calls = []
    monkeypatch.setattr(tui_app.hc, "restart_agent",
                        lambda *a, **k: calls.append(1) or (True, {}))
    app = tui_app.HarnessTUI(base_url="http://test")
    pushed = {}
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        from textual.widgets import DataTable
        app.query_one("#agents", DataTable).move_cursor(row=0)
        monkeypatch.setattr(app, "push_screen",
                            lambda s, callback=None: pushed.update(cb=callback))
        app.action_force_selected()
        pushed["cb"](False)   # cancel
        await app.workers.wait_for_complete()
        await pilot.pause()
    assert calls == []


@pytest.mark.asyncio
async def test_selected_agent_reports_busy(monkeypatch):
    """AC3: the selected-agent lookup carries work_state so the action layer can
    surface busy ('working') before a reboot."""
    import time
    now = time.time()
    monkeypatch.setattr(tui_app.hc, "fetch_status", lambda *a, **k: _status(now))
    app = tui_app.HarnessTUI(base_url="http://test")
    async with app.run_test() as pilot:
        await app.workers.wait_for_complete()
        await pilot.pause()
        from textual.widgets import DataTable
        app.query_one("#agents", DataTable).move_cursor(row=0)
        agent = app._selected_agent()
    # skill has a current_cycle → working/busy; pm is idle.
    assert agent["role"] == "skill"
    assert agent["work_state"] == tui_app.hc.WORK_STATE_WORKING
