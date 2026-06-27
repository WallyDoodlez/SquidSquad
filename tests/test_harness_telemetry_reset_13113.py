"""Regression tests for #13113 — respawned-agent telemetry masquerade.

The (re)spawn paths reset claude_pid / bootup_complete / last_session_end /
last_dispatch_at, but historically left the per-session ACTIVITY + PAUSE
telemetry (last_activity_at, last_activity, in_flight_until, waiting_since,
compacting_since) carrying the dead session's values across the PID boundary.
A respawned record then showed the old session's last_activity_at — frozen at
the pre-kill timestamp — until the new session landed its first heartbeat,
making a healthy fresh agent indistinguishable from a wedged one (and, via a
stale in_flight_until, holding off death-detection in active_pause()).

`AgentState.reset_session_telemetry()` clears that set on every spawn path so a
respawned record is indistinguishable from a first boot. These tests lock the
behavior, the deliberate scope boundary (backoff bookkeeping persists), and the
structural pairing (no spawn path may clear last_dispatch_at without it).
"""

import inspect
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import harness  # noqa: E402
from harness import AgentState  # noqa: E402


# The per-session activity + pause fields the helper must reset.
_SESSION_FIELDS = (
    "last_activity_at",
    "last_activity",
    "in_flight_until",
    "waiting_since",
    "compacting_since",
)

# Backoff / crash-loop bookkeeping that MUST survive a respawn by design.
_PERSIST_FIELDS = {
    "last_spawn_at": 1_234_567.0,
    "consecutive_fast_deaths": 3,
    "reboot_history": [111.0, 222.0],
    "reboot_blocked_until": 999_999.0,
    "last_stop_failure": {"cause": "rate_limit", "at": 42.0},
}


def _staled():
    """An agent record carrying a dead session's stale per-session telemetry."""
    a = AgentState("skill", "/clone/skill")
    a.last_activity_at = 22_060.0
    a.last_activity = {"at": 22_060.0, "event": "PostToolUse", "tool": "Read"}
    a.in_flight_until = 22_100.0
    a.waiting_since = 22_050.0
    a.compacting_since = 22_040.0
    return a


class TestResetSessionTelemetry:
    def test_clears_all_session_fields(self):
        a = _staled()
        a.reset_session_telemetry()
        for f in _SESSION_FIELDS:
            assert getattr(a, f) is None, f"{f} not cleared by reset"

    def test_respawned_record_matches_fresh_boot(self):
        """After reset, the per-session telemetry is indistinguishable from a
        first-boot AgentState — the whole point (no masquerade)."""
        fresh = AgentState("skill", "/clone/skill")
        a = _staled()
        a.reset_session_telemetry()
        for f in _SESSION_FIELDS:
            assert getattr(a, f) == getattr(fresh, f)

    def test_preserves_backoff_bookkeeping(self):
        """Scope boundary: crash-loop / backoff fields persist across respawns
        by design and must NOT be touched."""
        a = _staled()
        for f, v in _PERSIST_FIELDS.items():
            setattr(a, f, v)
        a.reset_session_telemetry()
        for f, v in _PERSIST_FIELDS.items():
            assert getattr(a, f) == v, f"{f} wrongly reset (must persist)"

    def test_idempotent_on_fresh_agent(self):
        """Calling it on an already-fresh record is a harmless no-op."""
        a = AgentState("skill")
        a.reset_session_telemetry()
        for f in _SESSION_FIELDS:
            assert getattr(a, f) is None


class TestSpawnPathPairing:
    def test_every_spawn_path_resets_session_telemetry(self):
        """Structural guard (mirrors the DS-c1 F4 last_dispatch_at pairing):
        every spawn site that clears last_dispatch_at must also call
        reset_session_telemetry(), so a future spawn path cannot reintroduce
        the masquerade. last_dispatch_at = None appears once in __init__ plus
        once per spawn path; the reset is called once per spawn path."""
        src = inspect.getsource(harness)
        ld_total = src.count("last_dispatch_at = None")
        spawn_dispatch_clears = ld_total - 1  # exclude the __init__ default
        reset_calls = src.count(".reset_session_telemetry()")
        assert spawn_dispatch_clears >= 1, "no spawn-path dispatch clears found"
        assert reset_calls >= spawn_dispatch_clears, (
            f"reset_session_telemetry() called {reset_calls}x but "
            f"{spawn_dispatch_clears} spawn paths clear last_dispatch_at — a "
            f"spawn path clears the dispatch reference without resetting the "
            f"per-session telemetry (#13113 masquerade regression)"
        )
