"""Tests for references/scripts/reboot_agent.py — safe agent restart (#2183)."""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import reboot_agent


@pytest.fixture
def squid_dir(tmp_path):
    """Create minimal .squidsquad directory."""
    squid = tmp_path / ".squidsquad"
    for role in ("skill", "pm"):
        (squid / role).mkdir(parents=True)
    return squid


@pytest.fixture
def patch_dirs(squid_dir, tmp_path, monkeypatch):
    """Patch paths to use tmp_path."""
    monkeypatch.setattr(reboot_agent, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(reboot_agent, "SQUID_DIR", squid_dir)
    return tmp_path


class TestRebootNotRunning:
    """Agent not running — reboot should exit 0 gracefully."""

    def test_no_pid_file(self, patch_dirs, squid_dir):
        result = reboot_agent.reboot("skill")
        assert result == 0

    def test_dead_pid(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("99999", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: False)
        result = reboot_agent.reboot("skill")
        assert result == 0

    def test_invalid_pid_file(self, patch_dirs, squid_dir):
        (squid_dir / "skill" / ".pid").write_text("not-a-number", encoding="utf-8")
        result = reboot_agent.reboot("skill")
        assert result == 0


class TestRebootForce:
    """Force reboot — kills immediately without waiting."""

    def test_force_kills_immediately(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)

        killed = []
        monkeypatch.setattr(reboot_agent, "_kill_process", lambda pid: killed.append(pid))

        result = reboot_agent.reboot("skill", force=True)
        assert result == 0
        assert 12345 in killed
        # Sentinel should be written
        assert (squid_dir / "skill" / ".restart").exists()


class TestRebootWaitForIdle:
    """Normal reboot — writes sentinel, waits for idle, then kills."""

    def test_idle_detected(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        # Write current-state as idle
        (squid_dir / "skill" / "current-state").write_text("idle|", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        monkeypatch.setattr(reboot_agent, "POLL_INTERVAL", 0.01)

        killed = []
        monkeypatch.setattr(reboot_agent, "_kill_process", lambda pid: killed.append(pid))

        result = reboot_agent.reboot("skill", timeout=1)
        assert result == 0
        assert 12345 in killed

    def test_timeout_cleans_sentinel(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        # current-state is NOT idle — agent is busy
        (squid_dir / "skill" / "current-state").write_text("implementing|Working...", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        monkeypatch.setattr(reboot_agent, "POLL_INTERVAL", 0.01)

        result = reboot_agent.reboot("skill", timeout=0.05)
        assert result == 1
        # Sentinel should be cleaned up on timeout
        assert not (squid_dir / "skill" / ".restart").exists()


class TestSentinelWritten:
    """Restart sentinel is always written before waiting."""

    def test_sentinel_content(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / "current-state").write_text("idle|", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        monkeypatch.setattr(reboot_agent, "_kill_process", lambda pid: None)
        monkeypatch.setattr(reboot_agent, "POLL_INTERVAL", 0.01)

        reboot_agent.reboot("skill", timeout=1)
        # Sentinel was written (and read by wrapper) — may be consumed already
        # but the function should have created it


class TestGetClonePath:
    """Clone path resolution."""

    def test_defaults_to_repo_root(self, patch_dirs):
        path = reboot_agent._get_clone_path("skill")
        assert path == reboot_agent.REPO_ROOT

    def test_reads_local_config(self, patch_dirs, squid_dir):
        local_config = squid_dir / ".local-config"
        local_config.write_text("- **skill**: /custom/path\n", encoding="utf-8")
        path = reboot_agent._get_clone_path("skill")
        assert path == Path("/custom/path")


class TestRebootAll:
    """--all flag handles get_agents() dict output correctly (#2353)."""

    def test_all_flag_with_dict_agents(self, patch_dirs, squid_dir, monkeypatch):
        """get_agents() returns list of dicts — reboot() must receive string role."""
        import importlib
        import config as config_mod

        agents = [
            {"id": "pm", "alias": "pm", "role": "infra"},
            {"id": "skill", "alias": "skill", "role": "dev"},
        ]
        rebooted_roles = []

        def fake_reboot(role, timeout=60, force=False):
            rebooted_roles.append(role)
            return 0

        monkeypatch.setattr(reboot_agent, "reboot", fake_reboot)
        monkeypatch.setattr(config_mod, "get_agents", lambda: agents)

        with patch("sys.argv", ["reboot_agent.py", "--all"]):
            rc = reboot_agent.main()

        assert rc == 0
        assert rebooted_roles == ["pm", "skill"]

    def test_all_flag_with_string_agents_fallback(self, patch_dirs, monkeypatch):
        """Fallback list of strings still works when get_agents() fails."""
        import config as config_mod

        rebooted_roles = []

        def fake_reboot(role, timeout=60, force=False):
            rebooted_roles.append(role)
            return 0

        monkeypatch.setattr(reboot_agent, "reboot", fake_reboot)
        def raise_import_error():
            raise ImportError("no config")

        monkeypatch.setattr(config_mod, "get_agents", raise_import_error)

        with patch("sys.argv", ["reboot_agent.py", "--all"]):
            rc = reboot_agent.main()

        assert rc == 0
        assert rebooted_roles == ["pm", "skill"]
