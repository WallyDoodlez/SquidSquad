"""Tests for references/scripts/subloop_driver.py — event-mode periodic
driver state machine (#12506, conforms to AGENT-RUNTIME §8.6.1).

These cover the deterministic core that backs the #12506 acceptance criteria:
AC1 lazy enable, AC3 bounded burst, AC4 re-arm + reset, AC5 Monitor
coexistence (driver-tick-mid-work absorbs), AC6 config consumption.
"""

import json
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import subloop_driver as sd


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def isolated(tmp_path, monkeypatch):
    """Redirect driver state writes into a temp repo root; pin config values
    so lifecycle tests don't depend on the live config.md."""
    monkeypatch.setattr(sd, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(sd, "idle_scan_burst", lambda: 3)
    monkeypatch.setattr(sd, "cooldown_minutes", lambda: 30)
    return tmp_path


T0 = "2026-06-18T00:00:00+00:00"


def _plus(minutes):
    h, m = divmod(minutes, 60)
    return f"2026-06-18T{h:02d}:{m:02d}:00+00:00"


# ---------------------------------------------------------------------------
# AC6 — config consumption (graceful defaults)
# ---------------------------------------------------------------------------

class TestConfigReaders:
    def test_idle_scan_burst_reads_value(self, monkeypatch):
        monkeypatch.setattr(sd._config, "get_field", lambda f: "5")
        assert sd.idle_scan_burst() == 5

    def test_idle_scan_burst_defaults_to_3_when_absent(self, monkeypatch):
        monkeypatch.setattr(sd._config, "get_field", lambda f: None)
        assert sd.idle_scan_burst() == 3

    def test_idle_scan_burst_defaults_on_garbage(self, monkeypatch):
        monkeypatch.setattr(sd._config, "get_field", lambda f: "abc")
        assert sd.idle_scan_burst() == 3

    def test_cooldown_parses_bare_int_legacy(self, monkeypatch):
        # Existing installs carry `30` (no unit) — must still parse.
        monkeypatch.setattr(sd._config, "get_field", lambda f: "30")
        assert sd.cooldown_minutes() == 30

    def test_cooldown_parses_m_suffix(self, monkeypatch):
        # #12506 moves config to `30m`.
        monkeypatch.setattr(sd._config, "get_field", lambda f: "30m")
        assert sd.cooldown_minutes() == 30

    def test_cooldown_parses_other_minute_values(self, monkeypatch):
        monkeypatch.setattr(sd._config, "get_field", lambda f: "45m")
        assert sd.cooldown_minutes() == 45

    def test_cooldown_defaults_when_absent(self, monkeypatch):
        monkeypatch.setattr(sd._config, "get_field", lambda f: None)
        assert sd.cooldown_minutes() == 30


# ---------------------------------------------------------------------------
# AC1 — lazy enable
# ---------------------------------------------------------------------------

class TestLazyEnable:
    def test_fresh_agent_is_disarmed(self, isolated):
        # A busy agent that never reaches idle never calls arm() — no state,
        # disarmed by default (never schedules a driver).
        state = sd.read_state("skill")
        assert state["armed"] is False
        assert state["scan_count"] == 0
        assert not sd._state_path("skill").exists()

    def test_first_idle_arms_and_schedules(self, isolated):
        res = sd.arm("skill")
        assert res["action"] == "schedule"
        assert res["interval_minutes"] == 30
        assert sd.read_state("skill")["armed"] is True

    def test_second_arm_is_noop_no_double_schedule(self, isolated):
        sd.arm("skill")
        res = sd.arm("skill")
        assert res["action"] == "already-armed"
        # DS #12506-unit3 F3: already-armed must carry interval_minutes so the
        # agent can rebuild a restart-lost (session-scoped) cron without a
        # second call.
        assert res["interval_minutes"] == 30

    def test_arm_is_per_alias_isolated(self, isolated):
        sd.arm("skill")
        assert sd.read_state("pm")["armed"] is False


# ---------------------------------------------------------------------------
# AC3 — bounded burst
# ---------------------------------------------------------------------------

class TestBoundedBurst:
    def test_tick_scans_while_under_cap_and_cooldown_elapsed(self, isolated):
        sd.arm("skill")
        res = sd.tick("skill", drained=True, now=T0)
        assert res["action"] == "scan"

    def test_record_scan_increments(self, isolated):
        sd.arm("skill")
        r1 = sd.record_scan("skill", now=T0)
        assert r1["scan_count"] == 1
        assert r1["at_cap"] is False

    def test_cap_reached_after_burst_then_tick_cancels(self, isolated):
        sd.arm("skill")
        sd.record_scan("skill", now=_plus(0))
        sd.record_scan("skill", now=_plus(40))
        last = sd.record_scan("skill", now=_plus(80))
        assert last["scan_count"] == 3
        assert last["at_cap"] is True
        # Next tick (cooldown long elapsed) must cancel, not scan.
        res = sd.tick("skill", drained=True, now=_plus(200))
        assert res["action"] == "cancel"
        assert res["reason"] == "at-cap"

    def test_no_scan_beyond_cap_even_if_cooldown_elapsed(self, isolated):
        sd.arm("skill")
        for m in (0, 40, 80):
            sd.record_scan("skill", now=_plus(m))
        res = sd.tick("skill", drained=True, now=_plus(999))
        assert res["action"] != "scan"


# ---------------------------------------------------------------------------
# Cooldown throttle gating
# ---------------------------------------------------------------------------

class TestCooldownGating:
    def test_tick_waits_when_cooldown_not_elapsed(self, isolated):
        sd.arm("skill")
        sd.record_scan("skill", now=T0)
        # 10 min later — inside the 30m cool-down.
        res = sd.tick("skill", drained=True, now=_plus(10))
        assert res["action"] == "wait"
        assert res["reason"] == "cooldown-not-elapsed"

    def test_tick_scans_after_cooldown_elapses(self, isolated):
        sd.arm("skill")
        sd.record_scan("skill", now=T0)
        res = sd.tick("skill", drained=True, now=_plus(31))
        assert res["action"] == "scan"

    def test_first_scan_not_blocked_by_null_last_run(self, isolated):
        sd.arm("skill")
        # never scanned → last_run None → cooldown counts as elapsed
        res = sd.tick("skill", drained=True, now=T0)
        assert res["action"] == "scan"


# ---------------------------------------------------------------------------
# AC4 — re-arm + reset
# ---------------------------------------------------------------------------

class TestReArm:
    def test_reidle_after_cancel_rearms_and_resets_count(self, isolated):
        sd.arm("skill")
        for m in (0, 40, 80):
            sd.record_scan("skill", now=_plus(m))
        sd.cancel("skill")
        assert sd.read_state("skill")["armed"] is False
        res = sd.reidle("skill")
        assert res["action"] == "schedule"
        assert res["rearmed"] is True
        state = sd.read_state("skill")
        assert state["armed"] is True
        assert state["scan_count"] == 0

    def test_reidle_resets_count_even_if_still_armed(self, isolated):
        sd.arm("skill")
        sd.record_scan("skill", now=T0)
        res = sd.reidle("skill")
        assert res["action"] == "already-armed"
        assert sd.read_state("skill")["scan_count"] == 0

    def test_reidle_preserves_last_run_so_throttle_holds(self, isolated):
        # Re-arming must NOT bypass the global cool-down throttle.
        sd.arm("skill")
        sd.record_scan("skill", now=T0)
        sd.reidle("skill")
        res = sd.tick("skill", drained=True, now=_plus(5))
        assert res["action"] == "wait"


# ---------------------------------------------------------------------------
# AC5 — Monitor coexistence (driver tick mid-work is absorbed)
# ---------------------------------------------------------------------------

class TestMonitorCoexistence:
    def test_tick_with_work_present_absorbs_not_scans(self, isolated):
        sd.arm("skill")
        res = sd.tick("skill", drained=False, now=T0)
        assert res["action"] == "absorb-work"


class TestDisarmedGuard:
    """DS finding #3: a disarmed driver must never authorize a scan, even if a
    stale self-wake fires after cancel()."""

    def test_disarmed_tick_returns_cancel(self, isolated):
        # never armed
        res = sd.tick("skill", drained=True, now=T0)
        assert res["action"] == "cancel"
        assert res["reason"] == "disarmed"

    def test_stale_tick_after_cancel_does_not_scan(self, isolated):
        sd.arm("skill")
        sd.cancel("skill")
        res = sd.tick("skill", drained=True, now=_plus(999))
        assert res["action"] == "cancel"
        assert res["reason"] == "disarmed"


# ---------------------------------------------------------------------------
# State persistence
# ---------------------------------------------------------------------------

class TestStatePersistence:
    def test_round_trip(self, isolated):
        sd.arm("skill")
        sd.record_scan("skill", now=T0)
        on_disk = json.loads(sd._state_path("skill").read_text(encoding="utf-8"))
        assert on_disk["armed"] is True
        assert on_disk["scan_count"] == 1
        assert on_disk["last_run"] == T0

    def test_corrupt_state_falls_back_to_default(self, isolated):
        path = sd._state_path("skill")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{not valid json", encoding="utf-8")
        state = sd.read_state("skill")
        assert state == sd._DEFAULT_STATE

    def test_non_dict_json_falls_back_to_default(self, isolated):
        path = sd._state_path("skill")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("[1, 2, 3]", encoding="utf-8")
        assert sd.read_state("skill") == sd._DEFAULT_STATE

    def test_type_corrupt_scan_count_falls_back(self, isolated):
        # DS finding #2: a valid-JSON but wrong-typed field must not crash
        # downstream callers (scan_count would do str + int).
        path = sd._state_path("skill")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"armed": true, "scan_count": "not-an-int", "last_run": null}',
                        encoding="utf-8")
        assert sd.read_state("skill") == sd._DEFAULT_STATE

    def test_numeric_last_run_coerced_to_str_then_tolerated(self, isolated):
        # A numeric last_run (manual corruption) coerces to str; cooldown_elapsed
        # then treats the unparseable value as elapsed rather than crashing.
        path = sd._state_path("skill")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"armed": true, "scan_count": 0, "last_run": 1700000000}',
                        encoding="utf-8")
        state = sd.read_state("skill")
        assert state["last_run"] == "1700000000"
        res = sd.tick("skill", drained=True, now=T0)
        assert res["action"] == "scan"
