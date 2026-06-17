"""Unit tests for the INSTALLER-ARCH §10.3 post-commit harness restart (#12420).

Covers the wizard.py code half — port discovery, alias enumeration, and the
`restart_agents` routing (reachable → per-alias stop+start; unreachable →
user-driven cold-start). The single network touchpoint is `wizard._http_request`,
monkeypatched here so the tests exercise both branches without a live harness.
The LLM-driven runbook step (WIZARD.md Step 7.5c) is not unit-tested — these
tests pin the deterministic *what happens*, not the prose.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import wizard  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _write_aliases_config(base, aliases):
    """Write base/.squidsquad/config.md with a legacy bullet-form `## Aliases`
    block (the shape real installs ship — see this repo's config.md)."""
    squid = base / ".squidsquad"
    squid.mkdir(parents=True, exist_ok=True)
    lines = ["# SquidSquad Config", "", "## Aliases", ""]
    lines += [f"- **{alias}**: {role_class}" for alias, role_class in aliases]
    lines += ["", "## Project", "", "- **Name**: demo", ""]
    (squid / "config.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return squid / "config.md"


def _write_port(base, value):
    squid = base / ".squidsquad"
    squid.mkdir(parents=True, exist_ok=True)
    (squid / ".harness-port").write_text(str(value), encoding="utf-8")


class _FakeHTTP:
    """Records (method, url) calls; returns programmed (status, body) responses.

    `status_map`: url-substring → (status, body). `raise_on`: url-substring →
    exception instance to raise (transport failure). First match wins; otherwise
    `default`.
    """

    def __init__(self, default=(200, "{}"), status_map=None, raise_on=None):
        self.calls = []
        self.default = default
        self.status_map = status_map or {}
        self.raise_on = raise_on or {}

    def __call__(self, method, url, timeout, data=None):
        self.calls.append((method, url))
        for sub, exc in self.raise_on.items():
            if sub in url:
                raise exc
        for sub, resp in self.status_map.items():
            if sub in url:
                return resp
        return self.default

    def posts(self):
        return [url for (m, url) in self.calls if m == "POST"]


_ALIASES = [("skill", "skill"), ("pm", "pm"), ("dm", "dm"), ("qa", "qa")]
_SORTED = ["dm", "pm", "qa", "skill"]


# ---------------------------------------------------------------------------
# _read_harness_port
# ---------------------------------------------------------------------------


class TestReadHarnessPort:
    def test_missing_file_defaults(self, tmp_path):
        assert wizard._read_harness_port(tmp_path) == wizard.HARNESS_DEFAULT_PORT

    def test_reads_file(self, tmp_path):
        _write_port(tmp_path, 8989)
        assert wizard._read_harness_port(tmp_path) == 8989

    def test_whitespace_tolerated(self, tmp_path):
        _write_port(tmp_path, "  7400\n")
        assert wizard._read_harness_port(tmp_path) == 7400

    @pytest.mark.parametrize("junk", ["", "abc", "12.5", "port"])
    def test_invalid_defaults(self, tmp_path, junk):
        _write_port(tmp_path, junk)
        assert wizard._read_harness_port(tmp_path) == wizard.HARNESS_DEFAULT_PORT


# ---------------------------------------------------------------------------
# _install_aliases
# ---------------------------------------------------------------------------


class TestInstallAliases:
    def test_reads_sorted_aliases(self, tmp_path):
        _write_aliases_config(tmp_path, _ALIASES)
        assert wizard._install_aliases(tmp_path) == _SORTED

    def test_missing_config_empty(self, tmp_path):
        assert wizard._install_aliases(tmp_path) == []

    def test_malformed_aliases_empty(self, tmp_path):
        squid = tmp_path / ".squidsquad"
        squid.mkdir(parents=True)
        # No `## Aliases` section at all → registry raises → []
        (squid / "config.md").write_text("# SquidSquad Config\n", encoding="utf-8")
        assert wizard._install_aliases(tmp_path) == []


# ---------------------------------------------------------------------------
# restart_agents — UNREACHABLE branch (AC1 "falls through to start.sh", AC5)
# ---------------------------------------------------------------------------


class TestUnreachable:
    def test_probe_transport_error_is_cold_start(self, tmp_path, monkeypatch):
        _write_aliases_config(tmp_path, _ALIASES)
        fake = _FakeHTTP(raise_on={"/status": ConnectionRefusedError("refused")})
        monkeypatch.setattr(wizard, "_http_request", fake)
        result = wizard.restart_agents(tmp_path)
        assert result["reachable"] is False
        assert result["ok"] is True  # unreachable is a normal branch, not an error
        assert result["cold_start_cmd"] == "./start.sh"
        # No lifecycle calls were made — the wizard never spawns the harness.
        assert fake.posts() == []

    def test_probe_non_2xx_is_unreachable(self, tmp_path, monkeypatch):
        _write_aliases_config(tmp_path, _ALIASES)
        fake = _FakeHTTP(status_map={"/status": (503, "down")})
        monkeypatch.setattr(wizard, "_http_request", fake)
        result = wizard.restart_agents(tmp_path)
        assert result["reachable"] is False
        assert fake.posts() == []

    def test_unreachable_reports_resolved_port(self, tmp_path, monkeypatch):
        _write_port(tmp_path, 8123)
        fake = _FakeHTTP(raise_on={"/status": OSError("nope")})
        monkeypatch.setattr(wizard, "_http_request", fake)
        result = wizard.restart_agents(tmp_path)
        assert result["port"] == 8123


# ---------------------------------------------------------------------------
# restart_agents — REACHABLE branch (AC1 stop+start per alias, AC2, AC5)
# ---------------------------------------------------------------------------


class TestReachable:
    def test_restarts_each_alias_stop_then_start(self, tmp_path, monkeypatch):
        _write_aliases_config(tmp_path, _ALIASES)
        fake = _FakeHTTP(default=(200, "{}"))
        monkeypatch.setattr(wizard, "_http_request", fake)
        result = wizard.restart_agents(tmp_path)

        assert result["reachable"] is True
        assert result["ok"] is True
        assert result["restarted"] == _SORTED
        assert result["failures"] == []

        # Exactly: GET /status, then stop+start per alias in sorted order.
        expected = []
        for alias in _SORTED:
            expected.append(f"/agents/{alias}/stop")
            expected.append(f"/agents/{alias}/start")
        assert [url.split(":7373")[-1] for url in fake.posts()] == expected
        # First call was the /status probe (GET).
        assert fake.calls[0][0] == "GET" and fake.calls[0][1].endswith("/status")

    def test_uses_resolved_port_in_urls(self, tmp_path, monkeypatch):
        _write_aliases_config(tmp_path, [("skill", "skill")])
        _write_port(tmp_path, 9001)
        fake = _FakeHTTP(default=(200, "{}"))
        monkeypatch.setattr(wizard, "_http_request", fake)
        wizard.restart_agents(tmp_path)
        assert all(":9001/" in url for (_m, url) in fake.calls)

    def test_reachable_but_no_aliases_is_error(self, tmp_path, monkeypatch):
        # config.md without an `## Aliases` section → reachable, but nothing to restart.
        squid = tmp_path / ".squidsquad"
        squid.mkdir(parents=True)
        (squid / "config.md").write_text("# SquidSquad Config\n", encoding="utf-8")
        fake = _FakeHTTP(default=(200, "{}"))
        monkeypatch.setattr(wizard, "_http_request", fake)
        result = wizard.restart_agents(tmp_path)
        assert result["reachable"] is True
        assert result["ok"] is False
        assert result["aliases"] == []
        assert fake.posts() == []  # never attempted a restart


# ---------------------------------------------------------------------------
# Per-alias failure handling — best-effort, recorded not fatal
# ---------------------------------------------------------------------------


class TestPartialFailure:
    def test_one_alias_stop_http_error_recorded(self, tmp_path, monkeypatch):
        _write_aliases_config(tmp_path, [("skill", "skill"), ("pm", "pm")])
        # pm's stop returns 500; everything else 200.
        fake = _FakeHTTP(
            default=(200, "{}"),
            status_map={"/agents/pm/stop": (500, "boom")},
        )
        monkeypatch.setattr(wizard, "_http_request", fake)
        result = wizard.restart_agents(tmp_path)

        assert result["ok"] is False
        assert result["restarted"] == ["skill"]
        assert len(result["failures"]) == 1
        assert result["failures"][0]["alias"] == "pm"
        assert "stop: HTTP 500" in result["failures"][0]["error"]
        # pm's start was NOT attempted after its stop failed.
        assert "/agents/pm/start" not in fake.posts()

    def test_start_transport_error_recorded(self, tmp_path, monkeypatch):
        _write_aliases_config(tmp_path, [("skill", "skill")])
        fake = _FakeHTTP(
            default=(200, "{}"),
            raise_on={"/agents/skill/start": TimeoutError("slow")},
        )
        monkeypatch.setattr(wizard, "_http_request", fake)
        result = wizard.restart_agents(tmp_path)
        assert result["ok"] is False
        assert result["restarted"] == []
        assert result["failures"][0]["alias"] == "skill"
        assert "start: TimeoutError" in result["failures"][0]["error"]


# ---------------------------------------------------------------------------
# CLI exit codes
# ---------------------------------------------------------------------------


class TestCmdExitCodes:
    def test_unreachable_exits_0(self, tmp_path, monkeypatch):
        _write_aliases_config(tmp_path, _ALIASES)
        monkeypatch.setattr(
            wizard, "_http_request",
            _FakeHTTP(raise_on={"/status": ConnectionRefusedError()}),
        )
        assert wizard.cmd_restart_agents([str(tmp_path)]) == 0

    def test_clean_restart_exits_0(self, tmp_path, monkeypatch):
        _write_aliases_config(tmp_path, _ALIASES)
        monkeypatch.setattr(wizard, "_http_request", _FakeHTTP(default=(200, "{}")))
        assert wizard.cmd_restart_agents([str(tmp_path)]) == 0

    def test_reachable_with_failure_exits_1(self, tmp_path, monkeypatch):
        _write_aliases_config(tmp_path, [("skill", "skill")])
        monkeypatch.setattr(
            wizard, "_http_request",
            _FakeHTTP(default=(200, "{}"), status_map={"/agents/skill/stop": (500, "x")}),
        )
        assert wizard.cmd_restart_agents([str(tmp_path)]) == 1
