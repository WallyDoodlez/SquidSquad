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
