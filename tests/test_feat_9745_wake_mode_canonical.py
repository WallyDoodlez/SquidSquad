"""Tests for config.get_wake_mode — harness-probe contract (#9745, #11401).

#9745 consolidated wake-mode resolution into config.get_wake_mode. #11401
changed *how* it resolves: per AGENT-RUNTIME §2 the wake mechanism is
selected solely by the boot-time harness probe (GET /status → 200 =
event-driven; any failure = polling). There is no `event-driven:` config
field anymore, so the Python runtime probes the harness instead of reading
config.md — removing the divergence where config said one thing and the
agent (driven by harness reachability) did another.

These tests cover the resolution table from #11401:

| harness reachable | result        |
|-------------------|---------------|
| yes (200)         | event-driven  |
| no (refused/timeout/non-200/no port) | polling |

…and the two divergence cases that motivated the fix: config.md content is
now irrelevant — a down harness yields polling even if config said
`event-driven: yes`, and an up harness yields event-driven even if config
never set the field.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import config


def _mock_resp(status=200):
    """A urlopen context-manager mock returning a response with ``status``."""
    resp = MagicMock()
    resp.status = status
    cm = MagicMock()
    cm.__enter__.return_value = resp
    cm.__exit__.return_value = False
    return cm


# ---------------------------------------------------------------------------
# Probe-based resolution
# ---------------------------------------------------------------------------

class TestGetWakeMode:
    def test_event_driven_when_harness_returns_200(self):
        with patch.object(config.urllib.request, "urlopen", return_value=_mock_resp(200)):
            assert config.get_wake_mode("skill") == "event-driven"

    def test_polling_when_connection_refused(self):
        import urllib.error
        with patch.object(config.urllib.request, "urlopen",
                          side_effect=urllib.error.URLError("refused")):
            assert config.get_wake_mode("skill") == "polling"

    def test_polling_on_timeout(self):
        with patch.object(config.urllib.request, "urlopen", side_effect=TimeoutError()):
            assert config.get_wake_mode("skill") == "polling"

    def test_polling_on_non_200(self):
        with patch.object(config.urllib.request, "urlopen", return_value=_mock_resp(503)):
            assert config.get_wake_mode("skill") == "polling"

    def test_polling_on_oserror(self):
        with patch.object(config.urllib.request, "urlopen", side_effect=OSError("socket")):
            assert config.get_wake_mode("skill") == "polling"

    def test_role_arg_is_ignored(self):
        """Reachability is global, not per-role: same result for any role,
        and role is optional."""
        with patch.object(config.urllib.request, "urlopen", return_value=_mock_resp(200)):
            assert config.get_wake_mode("pm") == "event-driven"
            assert config.get_wake_mode("dm") == "event-driven"
            assert config.get_wake_mode() == "event-driven"

    def test_returns_literal_strings_only(self):
        with patch.object(config.urllib.request, "urlopen", return_value=_mock_resp(200)):
            assert config.get_wake_mode("skill") in ("event-driven", "polling")


# ---------------------------------------------------------------------------
# Divergence cases from #11401 — config.md is now irrelevant
# ---------------------------------------------------------------------------

class TestConfigIsIgnored:
    def test_down_harness_polls_even_if_config_says_event(self, monkeypatch):
        """The original bug: config `event-driven: yes` while harness down
        made scripts report event while the agent polled. Now: polling."""
        monkeypatch.setattr(config, "get_field", lambda f: "yes")
        import urllib.error
        with patch.object(config.urllib.request, "urlopen",
                          side_effect=urllib.error.URLError("down")):
            assert config.get_wake_mode("skill") == "polling"

    def test_up_harness_events_even_if_config_unset(self, monkeypatch):
        """The mirror bug: no config field but harness up → agent events,
        scripts must agree."""
        def gf(f):
            raise SystemExit(1)  # field absent (get_field's behavior)
        monkeypatch.setattr(config, "get_field", gf)
        with patch.object(config.urllib.request, "urlopen", return_value=_mock_resp(200)):
            assert config.get_wake_mode("skill") == "event-driven"


# ---------------------------------------------------------------------------
# Probe helper internals
# ---------------------------------------------------------------------------

class TestHarnessReachable:
    def test_reachable_true_on_200(self):
        with patch.object(config.urllib.request, "urlopen", return_value=_mock_resp(200)):
            assert config._harness_reachable() is True

    def test_reachable_false_and_never_raises(self):
        import http.client
        # Includes http.client.HTTPException (BadStatusLine) — NOT an OSError,
        # realistic mid-restart failure — and AttributeError (atypical resp
        # object). The contract is "any failure → polling, never raise".
        exceptions = (
            OSError("x"),
            TimeoutError(),
            ValueError("x"),
            http.client.BadStatusLine("garbage"),
            http.client.HTTPException("incomplete read"),
            AttributeError("no status"),
        )
        for exc in exceptions:
            with patch.object(config.urllib.request, "urlopen", side_effect=exc):
                assert config._harness_reachable() is False, f"{type(exc).__name__} must degrade to False"

    def test_port_from_file(self, tmp_path, monkeypatch):
        pf = tmp_path / ".harness-port"
        pf.write_text("9999", encoding="utf-8")
        monkeypatch.setattr(config, "_HARNESS_PORT_FILE", pf)
        assert config._harness_wake_port() == 9999

    def test_port_default_when_file_missing(self, tmp_path, monkeypatch):
        monkeypatch.setattr(config, "_HARNESS_PORT_FILE", tmp_path / "nope")
        assert config._harness_wake_port() == config._DEFAULT_HARNESS_PORT

    def test_port_default_when_file_garbage(self, tmp_path, monkeypatch):
        pf = tmp_path / ".harness-port"
        pf.write_text("not-an-int", encoding="utf-8")
        monkeypatch.setattr(config, "_HARNESS_PORT_FILE", pf)
        assert config._harness_wake_port() == config._DEFAULT_HARNESS_PORT


# ---------------------------------------------------------------------------
# statusline_data still delegates to the canonical helper
# ---------------------------------------------------------------------------

class TestStatuslineDelegates:
    def test_statusline_data_delegates(self, monkeypatch):
        sys.modules.pop("statusline_data", None)
        statusline_data = __import__("statusline_data")
        monkeypatch.setattr(config, "get_wake_mode", lambda r: "event-driven")
        assert statusline_data._get_wake_mode("dm") == "event-driven"
