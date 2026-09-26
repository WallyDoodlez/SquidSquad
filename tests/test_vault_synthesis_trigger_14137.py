"""#14137 -- vault-synthesis gets an event-mode trigger that exists.

Synthesis fired "after 5 consecutive quiet cycles" counted in working state.
Event-mode PM has no quiet cycles, so it never ran (`.last-synthesis` was 4
months old). It now rides the #13861 harness maintenance window: the window
decides `synthesis_due` (at most weekly, config `Vault Optimize > Synthesis
Interval Days`, floor 7) and the single `vault-maintenance` event to pm carries
it. The harness schedules; the PM's sub-skill still judges, and it makes no
vault writes during the #13862 freeze.
"""

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "references" / "scripts"))

import harness  # noqa: E402

DAY = 86400.0


@pytest.fixture
def window(tmp_path, monkeypatch):
    ctx = {"queue": {"queue": [], "total_due": 0}, "rc": 0, "emitted": []}
    monkeypatch.setattr(harness, "VAULT_MAINTENANCE_STATE_FILE",
                        tmp_path / ".vault-maintenance.json")

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, ctx["rc"], json.dumps(ctx["queue"]), "boom")

    def fake_emit(event_type, role, payload=None, **extra):
        ctx["emitted"].append(payload)
        return {"id": f"ev{len(ctx['emitted'])}"}

    monkeypatch.setattr(harness.subprocess, "run", fake_run)
    monkeypatch.setattr(harness, "_emit_event", fake_emit)
    monkeypatch.setattr(harness.ExternalActivityDetector, "_alias_for_role_class",
                        staticmethod(lambda rc: "pm-alias"))
    monkeypatch.setattr(harness, "_vault_optimize_interval_hours", lambda: 24.0)
    monkeypatch.setattr(harness, "_vault_synthesis_interval_days", lambda: 7.0)
    monkeypatch.setattr(harness, "_log", lambda *a: None)
    return ctx


class TestSynthesisSchedule:
    def test_first_window_signals_synthesis_even_with_empty_queue(self, window):
        out = harness.run_vault_maintenance_window(now=1000.0)
        assert out["synthesis_due"] is True
        (payload,) = window["emitted"]
        assert payload["synthesis_due"] is True and payload["queued"] == 0
        assert payload["target_alias"] == "pm-alias"
        state = harness._read_vault_maintenance_state()
        assert state["last_synthesis_signal_at"] == 1000.0

    def test_not_resignalled_within_the_week(self, window):
        harness.run_vault_maintenance_window(now=1000.0)
        for day in range(1, 7):
            harness.run_vault_maintenance_window(now=1000.0 + day * DAY)
        assert len(window["emitted"]) == 1, "synthesis must not fire more than weekly"

    def test_resignalled_after_the_interval(self, window):
        harness.run_vault_maintenance_window(now=1000.0)
        harness.run_vault_maintenance_window(now=1000.0 + 7 * DAY)
        assert [p["synthesis_due"] for p in window["emitted"]] == [True, True]

    def test_optimize_only_window_carries_synthesis_false(self, window):
        harness._write_vault_maintenance_state({"last_synthesis_signal_at": 999.0})
        window["queue"] = {"queue": [{"slug": "a"}], "total_due": 2}
        harness.run_vault_maintenance_window(now=1000.0)
        (payload,) = window["emitted"]
        assert payload["queued"] == 1 and payload["synthesis_due"] is False
        assert harness._read_vault_maintenance_state()["last_synthesis_signal_at"] == 999.0

    def test_analyze_failure_does_not_block_synthesis(self, window):
        window["rc"] = 1
        out = harness.run_vault_maintenance_window(now=1000.0)
        assert "error" in out
        (payload,) = window["emitted"]
        assert payload["synthesis_due"] is True and payload["queued"] == 0

    def test_force_synthesis_overrides_the_interval(self, window):
        harness._write_vault_maintenance_state({"last_synthesis_signal_at": 999.0})
        harness.run_vault_maintenance_window(force=True, now=1000.0,
                                             force_synthesis=True)
        assert window["emitted"][0]["synthesis_due"] is True

    def test_force_synthesis_alone_runs_a_not_due_window(self, window):
        """Review F2: force_synthesis without force still runs the window."""
        harness._write_vault_maintenance_state(
            {"last_window_at": 1000.0, "last_synthesis_signal_at": 1000.0})
        out = harness.run_vault_maintenance_window(now=1001.0, force_synthesis=True)
        assert out["ran"] and out["synthesis_due"] is True
        assert window["emitted"][0]["synthesis_due"] is True

    def test_force_endpoint_synthesis_param(self, window, monkeypatch):
        harness._write_vault_maintenance_state({"last_synthesis_signal_at": 1e18})
        out = asyncio.run(harness.post_vault_maintenance(synthesis=True))
        assert out["forced"] and out["synthesis_due"] is True
        out2 = asyncio.run(harness.post_vault_maintenance())
        assert out2["synthesis_due"] is False
        body = asyncio.run(harness.get_vault_maintenance())
        assert body["synthesis_interval_days"] == 7.0
        assert isinstance(body["last_synthesis_signal_at"], float)


class TestSynthesisIntervalConfig:
    def test_default_and_weekly_floor(self):
        with patch("config.get_field", return_value="14"):
            assert harness._vault_synthesis_interval_days() == 14.0
        for low in ("3", "0.5"):
            with patch("config.get_field", return_value=low):
                assert harness._vault_synthesis_interval_days() == 7.0
        for bad in ("0", "never"):
            with patch("config.get_field", return_value=bad):
                assert harness._vault_synthesis_interval_days() == 7.0

    def test_config_field_and_default(self):
        import config
        assert config.FIELD_MAP["vault-synthesis-interval-days"] == (
            "Vault Optimize", "Synthesis Interval Days")
        assert config._FIELD_DEFAULTS["vault-synthesis-interval-days"] == "7"

    def test_catalog_payload_lists_synthesis_due(self):
        import event_catalog
        row = event_catalog.EMITTED["vault-maintenance"]
        assert "synthesis_due" in row["payload_fields"]
        assert "vault-synthesis" in row["description"]


class TestInstructions:
    SYN = REPO / "references" / "sub-skills" / "roles" / "pm" / "vault-synthesis.md"
    PM = REPO / "references" / "roles" / "pm" / "instructions.md"
    CONTRACT = REPO / "references" / "sub-skills" / "common-events" / "event-mode-contract.md"

    def test_quiet_cycle_counter_gone(self):
        for f in (self.SYN, self.PM):
            text = f.read_text(encoding="utf-8")
            assert "synthesis cycle counter" not in text
            assert "5 consecutive quiet cycles" not in text
            assert "every 5 quiet cycles" not in text

    def test_synthesis_triggered_by_synthesis_due(self):
        assert "synthesis_due: true" in self.SYN.read_text(encoding="utf-8")
        pm = self.PM.read_text(encoding="utf-8")
        step = pm[pm.index("#### step:cycle/vault-synthesis"):]
        assert "synthesis_due: true" in step

    def test_freeze_behaviour_stated(self):
        text = self.SYN.read_text(encoding="utf-8")
        freeze = text[text.index("**Vault write freeze**"):]
        freeze = freeze[:freeze.index("\n\n")]
        assert "config.py get vault-writes-per-cycle" in freeze
        assert "no vault writes" in freeze and "review task" in freeze
        # Review F1: the review-task template carries the frozen draft.
        assert "**Drafted note** field" in freeze
        step4 = text[text.index("**Step 4"):text.index("**Step 5")]
        assert "**Drafted note** (vault frozen" in step4
        assert "Target:" in step4

    def test_optimize_runs_before_synthesis(self):
        text = self.SYN.read_text(encoding="utf-8")
        activation = text[:text.index("**Activation")]
        assert "run optimize first, then synthesis" in activation

    def test_contract_routes_synthesis_due(self):
        text = self.CONTRACT.read_text(encoding="utf-8")
        bullet = text[text.index("- **`vault-maintenance`**"):]
        bullet = bullet[:bullet.index("\n- ")]
        assert "run sub-skill: `vault-synthesis`" in bullet
        assert "synthesis_due" in bullet
        # Review F4: each condition maps to its sub-skill, optimize first.
        i_q = bullet.index("If `queued` > 0")
        i_opt = bullet.index("run sub-skill: `vault-optimize`")
        i_s = bullet.index("If `synthesis_due` is true")
        i_syn = bullet.index("run sub-skill: `vault-synthesis`")
        assert i_q < i_opt < i_s < i_syn
