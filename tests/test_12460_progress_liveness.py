"""Unit tests for #12460 (#12271 slice d) — progress-based liveness FOUNDATION.

This slice adds the OBSERVATIONAL progress-liveness machinery: the
`AgentState.progress_liveness()` verdict, the `last_dispatch_at` dispatch
reference, and its persistence. None of it drives the reboot decision yet —
the cutover (making progress-liveness authoritative + demoting PID to
teardown-only) is a later, separately-reviewed step gated on the shadow-mode
divergence data this machinery gathers.

These tests pin the §15.1 "dead = dispatched + grace elapsed + no activity
since + no pause" definition, including the zombie repro (#10855 / #10440:
alive PID, zero work) that PID-liveness cannot catch.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import harness  # noqa: E402
from harness import AgentState, ACTIVITY_GRACE_SECONDS  # noqa: E402


NOW = 1_000_000.0  # fixed epoch for deterministic math


def _booted(role="skill"):
    a = AgentState(role)
    a.bootup_complete = True
    return a


# ---------------------------------------------------------------------------
# progress_liveness verdicts
# ---------------------------------------------------------------------------

class TestProgressLiveness:
    def test_not_booted_is_alive(self):
        a = AgentState("skill")  # bootup_complete = False
        a.last_dispatch_at = NOW - 10 * ACTIVITY_GRACE_SECONDS  # stale dispatch
        alive, reason = a.progress_liveness(NOW)
        assert alive is True
        assert reason == "booting"

    def test_idle_no_dispatch_is_alive(self):
        a = _booted()
        # No work ever dispatched → legitimately idle → never a false-positive.
        assert a.last_dispatch_at is None
        alive, reason = a.progress_liveness(NOW)
        assert alive is True
        assert reason == "idle-no-dispatch"

    def test_within_grace_is_alive(self):
        a = _booted()
        a.last_dispatch_at = NOW - (ACTIVITY_GRACE_SECONDS - 1)  # just inside
        alive, reason = a.progress_liveness(NOW)
        assert alive is True
        assert reason == "dispatch-grace"

    def test_acted_since_dispatch_is_alive(self):
        a = _booted()
        a.last_dispatch_at = NOW - (ACTIVITY_GRACE_SECONDS + 100)  # grace elapsed
        a.last_activity_at = NOW - 10  # heartbeat AFTER the dispatch
        alive, reason = a.progress_liveness(NOW)
        assert alive is True
        assert reason == "active"

    def test_wedged_no_activity_since_dispatch_is_dead(self):
        """THE zombie catch: dispatched, grace elapsed, no heartbeat since, no
        pause → dead. PID-liveness would call this alive."""
        a = _booted()
        a.last_dispatch_at = NOW - (ACTIVITY_GRACE_SECONDS + 100)
        a.last_activity_at = None  # never acted
        alive, reason = a.progress_liveness(NOW)
        assert alive is False
        assert reason == "wedged-no-activity-since-dispatch"

    def test_activity_before_dispatch_only_is_dead(self):
        """An old heartbeat from BEFORE the dispatch does not count — the agent
        must have acted on THIS dispatch."""
        a = _booted()
        a.last_dispatch_at = NOW - (ACTIVITY_GRACE_SECONDS + 100)
        a.last_activity_at = a.last_dispatch_at - 50  # stale, pre-dispatch
        alive, reason = a.progress_liveness(NOW)
        assert alive is False
        assert reason == "wedged-no-activity-since-dispatch"

    def test_pause_overrides_wedge(self):
        """An explained pause (in-flight tool call) keeps a silent agent alive
        even past the grace window — silence is accounted for."""
        a = _booted()
        a.last_dispatch_at = NOW - (ACTIVITY_GRACE_SECONDS + 100)
        a.last_activity_at = None
        a.in_flight_until = NOW + 60  # mid tool call
        alive, reason = a.progress_liveness(NOW)
        assert alive is True
        assert reason == "in-flight"

    def test_compacting_pause_alive(self):
        a = _booted()
        a.last_dispatch_at = NOW - (ACTIVITY_GRACE_SECONDS + 100)
        a.compacting_since = NOW - 10
        alive, reason = a.progress_liveness(NOW)
        assert alive is True
        assert reason == "compacting"

    def test_waiting_pause_alive(self):
        a = _booted()
        a.last_dispatch_at = NOW - (ACTIVITY_GRACE_SECONDS + 100)
        a.waiting_since = NOW - 10
        alive, reason = a.progress_liveness(NOW)
        assert alive is True
        assert reason == "waiting"

    def test_stale_pause_past_ceiling_does_not_save_wedge(self):
        """A pause flag past its staleness ceiling is ignored (active_pause
        returns None), so a genuinely wedged agent still reads dead."""
        a = _booted()
        a.last_dispatch_at = NOW - (ACTIVITY_GRACE_SECONDS + 100)
        a.last_activity_at = None
        # waiting_since older than WAITING_MAX_SECONDS → stale → ignored
        a.waiting_since = NOW - (harness.WAITING_MAX_SECONDS + 10)
        alive, reason = a.progress_liveness(NOW)
        assert alive is False
        assert reason == "wedged-no-activity-since-dispatch"


# ---------------------------------------------------------------------------
# zombie repro (#10855 / #10440 pattern)
# ---------------------------------------------------------------------------

class TestZombieRepro:
    def test_inert_boot_zombie_detected(self):
        """#10855: agent boots (bootup_complete), work is dispatched, but the
        process is inert — zero tool calls ever. PID is alive (not modeled
        here), but progress-liveness correctly reads DEAD."""
        a = _booted("verifier")
        # dispatched 22h ago, never any activity, nothing explaining silence
        a.last_dispatch_at = NOW - (22 * 3600)
        a.last_activity_at = None
        a.in_flight_until = None
        a.waiting_since = None
        a.compacting_since = None
        alive, reason = a.progress_liveness(NOW)
        assert alive is False
        assert reason == "wedged-no-activity-since-dispatch"


# ---------------------------------------------------------------------------
# last_dispatch_at field + persistence
# ---------------------------------------------------------------------------

class TestDispatchReferencePersistence:
    def test_defaults_none(self):
        a = AgentState("skill")
        assert a.last_dispatch_at is None

    def test_to_dict_includes_field(self):
        a = AgentState("skill")
        a.last_dispatch_at = NOW
        assert a.to_dict()["last_dispatch_at"] == NOW

    def test_save_load_round_trips(self, tmp_path, monkeypatch):
        from harness import HarnessState
        state_file = tmp_path / ".harness-state.json"
        monkeypatch.setattr(harness, "HARNESS_STATE_FILE", state_file)

        st = HarnessState()
        a = AgentState("skill", "/clone/skill")
        a.last_dispatch_at = NOW
        a.last_activity_at = NOW - 5
        st.set_agent("skill", a)
        st.save_state()

        st2 = HarnessState()
        st2.load_state()
        restored = st2.get_agent("skill")
        assert restored is not None
        assert restored.last_dispatch_at == NOW

    def test_clear_on_spawn_paths(self):
        """All four (re)spawn paths clear last_dispatch_at so a restart starts
        with a clean baseline (DS-c1 F4). Asserted structurally — every spawn
        site that clears last_session_end must also clear last_dispatch_at."""
        import inspect
        src = inspect.getsource(harness)
        se_clears = src.count("last_session_end = None")
        ld_clears = src.count("last_dispatch_at = None")
        # one __init__ + every spawn-path clear must be paired.
        assert ld_clears >= se_clears, (
            f"last_dispatch_at cleared {ld_clears}x but last_session_end "
            f"{se_clears}x — a spawn path clears SessionEnd without the "
            f"dispatch reference (DS-c1 F4 regression)"
        )


# ---------------------------------------------------------------------------
# should_advance_dispatch — DS-c1 F1 (re-nudge of unacted work must not reset
# grace) + F4 (never stamp a stopped agent)
# ---------------------------------------------------------------------------

class TestShouldAdvanceDispatch:
    def test_first_dispatch_advances(self):
        a = _booted()
        assert a.last_dispatch_at is None
        assert a.should_advance_dispatch() is True

    def test_reemit_of_unacted_work_does_not_advance(self):
        """DS-c1 F1: the agent was dispatched but never acted (la < ld / None);
        a handoff re-emit must NOT reset the grace — else a wedged verifier/dm
        resets forever and never reads wedged."""
        a = _booted("verifier")
        a.last_dispatch_at = NOW
        a.last_activity_at = None  # never acted
        assert a.should_advance_dispatch() is False
        # also: acted, but BEFORE the dispatch → still unacted on THIS work
        a.last_activity_at = NOW - 50
        assert a.should_advance_dispatch() is False

    def test_advances_after_agent_caught_up(self):
        """Agent acted since the last dispatch → new work resets the clock."""
        a = _booted()
        a.last_dispatch_at = NOW - 100
        a.last_activity_at = NOW - 10  # acted after dispatch
        assert a.should_advance_dispatch() is True

    def test_stopped_agent_never_stamped(self):
        """DS-c1 F4: a non-RUNNING agent is never stamped."""
        a = _booted()
        a.intent = AgentState.INTENT_STOPPED
        assert a.should_advance_dispatch() is False
        a.intent = AgentState.INTENT_STOPPING
        assert a.should_advance_dispatch() is False

    def test_grace_does_not_reset_forever_simulation(self):
        """End-to-end F1: simulate the handoff re-emit loop. A wedged agent's
        grace must age out to a wedged verdict despite repeated re-nudges."""
        a = _booted("verifier")
        # initial dispatch
        if a.should_advance_dispatch():
            a.last_dispatch_at = NOW
        # never acts; simulate re-emits every ACTIVITY_GRACE_SECONDS
        t = NOW
        for _ in range(5):
            t += ACTIVITY_GRACE_SECONDS
            if a.should_advance_dispatch():  # False — never acted
                a.last_dispatch_at = t
        # last_dispatch_at stayed at the ORIGINAL dispatch; grace long elapsed
        assert a.last_dispatch_at == NOW
        alive, reason = a.progress_liveness(t + 1)
        assert alive is False
        assert reason == "wedged-no-activity-since-dispatch"

    def test_load_defaults_none_for_older_state_file(self, tmp_path, monkeypatch):
        """An older state file lacking last_dispatch_at restores to None, not a
        crash (back-compat)."""
        import json
        from harness import HarnessState
        state_file = tmp_path / ".harness-state.json"
        state_file.write_text(json.dumps({
            "agents": {
                "skill": {"role": "skill", "status": "running",
                          "clone_path": "/c"}
            }
        }), encoding="utf-8")
        monkeypatch.setattr(harness, "HARNESS_STATE_FILE", state_file)
        st = HarnessState()
        st.load_state()
        assert st.get_agent("skill").last_dispatch_at is None


# ---------------------------------------------------------------------------
# update_health SHADOW divergence logging (observational — no behavior change)
# ---------------------------------------------------------------------------

class TestShadowDivergenceLogging:
    def _run_update_health(self, agent, pid_alive, fake_now):
        """Drive one update_health pass with a controlled PID verdict and the
        given agent progress-state. Returns the _log MagicMock."""
        from harness import HarnessState
        hs = HarnessState()
        hs.set_agent("skill", agent)
        log_mock = MagicMock()
        patches = [
            patch("harness.boot_remote._get_all_roles", return_value=["skill"]),
            patch("harness.boot_remote._get_clone_path", return_value="/clone"),
            patch("harness.boot_remote._is_process_alive", return_value=pid_alive),
            # #12294: the PID-based `alive` verdict now comes from the
            # image-verified helper — drive it to keep the shadow-divergence
            # scenarios deterministic; pin write-back to a no-op (would touch
            # /clone otherwise).
            patch("harness.process_utils.is_claude_process_alive", return_value=pid_alive),
            patch("harness.reboot_agent.write_claude_pid", return_value=True),
            patch("harness.reboot_agent._read_claude_pid", return_value=(None, False)),
            patch("harness.boot_remote.boot_agent",
                  return_value={"success": True, "terminal_pid": 9, "action": "spawn"}),
            patch("harness.time.time", return_value=fake_now),
            patch("harness._log", log_mock),
            patch.object(hs, "save_state"),
        ]
        for p in patches:
            p.start()
        try:
            hs.update_health()
        finally:
            for p in patches:
                p.stop()
        return log_mock

    def _divergence_logs(self, log_mock):
        return [c.args[0] for c in log_mock.call_args_list
                if c.args and "LIVENESS DIVERGENCE" in str(c.args[0])]

    def test_pid_alive_progress_dead_logs_candidate_zombie(self):
        """The zombie case: PID alive, progress dead → divergence logged, but
        NO reboot (alive drives the decision; observational only)."""
        now = 1_000_000.0
        a = _booted("skill")
        a.claude_pid = 4321
        a.last_dispatch_at = now - (ACTIVITY_GRACE_SECONDS + 100)
        a.last_activity_at = None  # inert → progress dead
        log_mock = self._run_update_health(a, pid_alive=True, fake_now=now)
        logs = self._divergence_logs(log_mock)
        assert len(logs) == 1
        assert "candidate-zombie" in logs[0]
        assert "PID says alive" in logs[0]
        assert "progress says dead" in logs[0]

    def test_agreement_logs_nothing(self):
        """PID alive AND progress alive (acted since dispatch) → no divergence."""
        now = 1_000_000.0
        a = _booted("skill")
        a.claude_pid = 4321
        a.last_dispatch_at = now - (ACTIVITY_GRACE_SECONDS + 100)
        a.last_activity_at = now - 5  # acted → progress alive
        log_mock = self._run_update_health(a, pid_alive=True, fake_now=now)
        assert self._divergence_logs(log_mock) == []

    def test_idle_agent_no_divergence(self):
        """An idle agent (PID alive, nothing dispatched) agrees → no log."""
        now = 1_000_000.0
        a = _booted("skill")
        a.claude_pid = 4321
        a.last_dispatch_at = None
        log_mock = self._run_update_health(a, pid_alive=True, fake_now=now)
        assert self._divergence_logs(log_mock) == []
