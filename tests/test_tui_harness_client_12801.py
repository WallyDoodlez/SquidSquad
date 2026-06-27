"""Tests for the TUI harness data layer (#12801 Story 1.2).

Pure derivation functions (work-state, cursor-lag bar, row shaping) +
graceful fetch failure. No Textual, no running harness.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "tui"))

import harness_client as hc  # noqa: E402


NOW = 1_000_000.0


# --- derive_work_state -----------------------------------------------------

class TestDeriveWorkState:
    def test_working_when_current_cycle_set(self):
        a = {"status": "running", "intent": "running", "current_cycle": 42}
        assert hc.derive_work_state(a, NOW) == hc.WORK_STATE_WORKING

    def test_working_when_in_flight_future(self):
        a = {"status": "running", "intent": "running",
             "current_cycle": None, "in_flight_until": NOW + 100}
        assert hc.derive_work_state(a, NOW) == hc.WORK_STATE_WORKING

    def test_idle_when_alive_and_nothing_in_progress(self):
        a = {"status": "running", "intent": "running",
             "current_cycle": None, "in_flight_until": None}
        assert hc.derive_work_state(a, NOW) == hc.WORK_STATE_IDLE

    def test_idle_when_in_flight_in_past(self):
        a = {"status": "running", "intent": "running",
             "current_cycle": None, "in_flight_until": NOW - 100}
        assert hc.derive_work_state(a, NOW) == hc.WORK_STATE_IDLE

    def test_down_when_not_running(self):
        a = {"status": "stopped", "intent": "running", "current_cycle": 7}
        assert hc.derive_work_state(a, NOW) == hc.WORK_STATE_DOWN

    def test_down_when_intent_restarting(self):
        # qa's real /status shape during a restart: running + restarting.
        a = {"status": "running", "intent": "restarting", "current_cycle": None}
        assert hc.derive_work_state(a, NOW) == hc.WORK_STATE_DOWN

    def test_color_mapping(self):
        assert hc.WORK_STATE_COLOR[hc.WORK_STATE_WORKING] == "green"
        assert hc.WORK_STATE_COLOR[hc.WORK_STATE_IDLE] == "yellow"
        assert hc.WORK_STATE_COLOR[hc.WORK_STATE_DOWN] == "red"


# --- lag_to_bar ------------------------------------------------------------

class TestLagToBar:
    def test_caught_up_arrow_at_right_no_alert(self):
        bar, alert = hc.lag_to_bar(0, scale=10, width=6)
        assert bar == "[-----→]"  # arrow at far right
        assert alert is False

    def test_far_behind_arrow_at_left_alert(self):
        bar, alert = hc.lag_to_bar(10, scale=10, width=6)
        assert bar == "[→-----]"  # arrow at far left
        assert alert is True

    def test_lag_beyond_scale_clamps_to_left(self):
        bar, alert = hc.lag_to_bar(999, scale=10, width=6)
        assert bar == "[→-----]"
        assert alert is True

    def test_negative_lag_treated_as_caught_up(self):
        bar, alert = hc.lag_to_bar(-5, scale=10, width=6)
        assert bar == "[-----→]"
        assert alert is False

    def test_exactly_one_arrow_in_bar(self):
        for lag in range(0, 12):
            bar, _ = hc.lag_to_bar(lag, scale=10, width=6)
            assert bar.count("→") == 1
            assert len(bar) == 8  # "[" + 6 + "]"


# --- agent_rows ------------------------------------------------------------

class TestAgentRows:
    def test_shapes_rows_with_derived_fields(self):
        status = {"agents": [
            {"role": "skill", "status": "running", "intent": "running",
             "current_cycle": 5, "last_activity_at": NOW, "lag": 0},
            {"role": "qa", "status": "running", "intent": "restarting",
             "current_cycle": None, "lag": 10},
        ]}
        rows = hc.agent_rows(status, NOW)
        by_role = {r["role"]: r for r in rows}
        assert by_role["skill"]["work_state"] == "working"
        assert by_role["skill"]["color"] == "green"
        assert by_role["skill"]["lag_alert"] is False
        assert by_role["qa"]["work_state"] == "down"
        assert by_role["qa"]["color"] == "red"
        assert by_role["qa"]["lag_alert"] is True

    def test_missing_lag_defaults_to_zero(self):
        status = {"agents": [{"role": "dm", "status": "running",
                              "intent": "running", "current_cycle": None}]}
        rows = hc.agent_rows(status, NOW)
        assert rows[0]["lag"] == 0
        assert rows[0]["lag_alert"] is False

    def test_empty_agents(self):
        assert hc.agent_rows({"agents": []}, NOW) == []
        assert hc.agent_rows({}, NOW) == []


# --- format_age ------------------------------------------------------------

class TestFormatAge:
    def test_none_is_dash(self):
        assert hc.format_age(None, NOW) == "—"

    def test_unparseable_is_dash(self):
        assert hc.format_age("not-a-number", NOW) == "—"

    def test_seconds(self):
        assert hc.format_age(NOW - 3, NOW) == "3s"

    def test_minutes_floor(self):
        assert hc.format_age(NOW - 125, NOW) == "2m"  # 125s → 2m (floor)

    def test_hours_floor(self):
        assert hc.format_age(NOW - 3 * 3600 - 5, NOW) == "3h"

    def test_days_floor(self):
        assert hc.format_age(NOW - 4 * 86400 - 100, NOW) == "4d"

    def test_boundary_60s_is_one_minute(self):
        assert hc.format_age(NOW - 60, NOW) == "1m"

    def test_future_clamps_to_zero(self):
        assert hc.format_age(NOW + 500, NOW) == "0s"


# --- _iso_to_epoch ---------------------------------------------------------

class TestIsoToEpoch:
    def test_z_suffix_utc(self):
        # 2026-06-21T00:00:00Z → known epoch.
        import datetime
        expected = datetime.datetime(
            2026, 6, 21, tzinfo=datetime.timezone.utc).timestamp()
        assert hc._iso_to_epoch("2026-06-21T00:00:00Z") == expected

    def test_offset_form(self):
        assert hc._iso_to_epoch("2026-06-21T00:00:00+00:00") is not None

    def test_empty_and_none(self):
        assert hc._iso_to_epoch("") is None
        assert hc._iso_to_epoch(None) is None

    def test_garbage(self):
        assert hc._iso_to_epoch("nonsense") is None

    def test_roundtrips_into_format_age(self):
        import datetime
        iso = "2026-06-21T00:00:00Z"
        epoch = hc._iso_to_epoch(iso)
        # 90 seconds later → "1m".
        assert hc.format_age(epoch, epoch + 90) == "1m"


# --- agent_rows last_activity_age -----------------------------------------

class TestAgentRowsActivityAge:
    def test_age_field_present(self):
        status = {"agents": [
            {"role": "skill", "status": "running", "intent": "running",
             "current_cycle": 5, "last_activity_at": NOW - 30, "lag": 0},
        ]}
        rows = hc.agent_rows(status, NOW)
        assert rows[0]["last_activity_age"] == "30s"

    def test_age_dash_when_missing(self):
        status = {"agents": [
            {"role": "dm", "status": "running", "intent": "running",
             "current_cycle": None, "lag": 0},
        ]}
        rows = hc.agent_rows(status, NOW)
        assert rows[0]["last_activity_age"] == "—"


# --- human_queue_rows ------------------------------------------------------

class TestHumanQueueRows:
    def _q(self):
        return {"count": 2, "items": [
            {"number": 12527, "title": "Greenfield smoke",
             "status": "pending-human-setup", "role": "skill",
             "priority": "high", "updated_at": "2026-06-21T00:00:00Z",
             "url": "https://x/12527"},
            {"number": 13119, "title": "Couple sentinel",
             "status": "pending-human-review", "role": "skill",
             "priority": "medium", "updated_at": "2026-06-20T23:00:00Z",
             "url": "https://x/13119"},
        ]}

    def test_shapes_rows_and_strips_prefix(self):
        # now = 1h after the first item's updated_at.
        now = hc._iso_to_epoch("2026-06-21T01:00:00Z")
        rows = hc.human_queue_rows(self._q(), now)
        assert rows[0]["number"] == 12527
        assert rows[0]["status_short"] == "setup"
        assert rows[0]["age"] == "1h"
        assert rows[1]["status_short"] == "review"

    def test_preserves_harness_order(self):
        rows = hc.human_queue_rows(self._q(), NOW)
        assert [r["number"] for r in rows] == [12527, 13119]

    def test_unknown_status_passes_through(self):
        q = {"items": [{"number": 1, "status": "weird", "updated_at": ""}]}
        rows = hc.human_queue_rows(q, NOW)
        assert rows[0]["status_short"] == "weird"
        assert rows[0]["age"] == "—"  # empty updated_at → unparseable

    def test_none_payload_graceful(self):
        assert hc.human_queue_rows(None, NOW) == []

    def test_empty_items(self):
        assert hc.human_queue_rows({"count": 0, "items": []}, NOW) == []


# --- agent_table_rows (display cells) --------------------------------------

class TestAgentTableRows:
    def test_cells_match_contract_shape(self):
        status = {"agents": [
            {"role": "skill", "status": "running", "intent": "running",
             "current_cycle": "#12801", "last_activity_at": NOW - 120, "lag": 4},
        ]}
        rows = hc.agent_table_rows(status, NOW)
        assert len(rows) == 1
        role, state, task, age, lag = rows[0]
        assert role == "skill"
        assert state == "[green]● working[/]"
        assert task == "#12801"
        assert age == "2m"
        assert lag.startswith("[") and "→" in lag

    def test_idle_no_task_renders_dash(self):
        status = {"agents": [
            {"role": "dm", "status": "running", "intent": "running",
             "current_cycle": None, "lag": 0},
        ]}
        role, state, task, age, lag = hc.agent_table_rows(status, NOW)[0]
        assert state == "[yellow]● idle[/]"
        assert task == "—"

    def test_down_agent_red(self):
        status = {"agents": [
            {"role": "qa", "status": "running", "intent": "restarting",
             "current_cycle": None, "lag": 0},
        ]}
        assert hc.agent_table_rows(status, NOW)[0][1] == "[red]● down[/]"

    def test_far_behind_lag_cell_reddened(self):
        status = {"agents": [
            {"role": "pm", "status": "running", "intent": "running",
             "current_cycle": None, "lag": 10},
        ]}
        assert hc.agent_table_rows(status, NOW)[0][4].startswith("[red]")

    def test_none_status_empty(self):
        assert hc.agent_table_rows(None, NOW) == []
        assert hc.agent_table_rows({}, NOW) == []


# --- fetch_json graceful failure ------------------------------------------

class TestFetchJson:
    def test_returns_none_on_unreachable(self):
        # Nothing listening on this port → URLError → None (graceful).
        assert hc.fetch_json("http://127.0.0.1:9", "/status", timeout=1) is None

    def test_parses_ok(self, monkeypatch):
        import io

        class _Resp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b'{"agents": []}'

        monkeypatch.setattr(hc.urllib.request, "urlopen", lambda *a, **k: _Resp())
        assert hc.fetch_json("http://x", "/status") == {"agents": []}
