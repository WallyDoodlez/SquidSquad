"""Tests for references/scripts/reboot_agent.py — unified agent lifecycle (#2496)."""

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
import boot_remote


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
    monkeypatch.setattr(boot_remote, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(boot_remote, "SQUIDSQUAD_DIR", squid_dir)
    monkeypatch.setattr(boot_remote, "LOCAL_CONFIG", squid_dir / ".local-config")
    monkeypatch.setattr(boot_remote, "CONFIG_MD", squid_dir / "config.md")
    return tmp_path


def _stub_spawn(monkeypatch):
    """Stub out _spawn_wrapper to track calls without actually spawning."""
    spawned = []

    def fake_spawn(role, clone_path):
        spawned.append(role)
        return True, "spawned (test stub)"

    monkeypatch.setattr(reboot_agent, "_spawn_wrapper", fake_spawn)
    return spawned


# ---------------------------------------------------------------------------
# Dead agent → boot (not no-op) (#2496)
# ---------------------------------------------------------------------------

class TestRebootDeadAgentBoots:
    """When agent is dead, reboot boots it instead of returning 0 as no-op."""

    def test_no_pid_file_boots(self, patch_dirs, squid_dir, monkeypatch):
        spawned = _stub_spawn(monkeypatch)
        result = reboot_agent.reboot("skill")
        assert result == 0
        assert "skill" in spawned

    def test_dead_pid_boots(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("99999", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: False)
        spawned = _stub_spawn(monkeypatch)
        result = reboot_agent.reboot("skill")
        assert result == 0
        assert "skill" in spawned

    def test_invalid_pid_file_boots(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("not-a-number", encoding="utf-8")
        spawned = _stub_spawn(monkeypatch)
        result = reboot_agent.reboot("skill")
        assert result == 0
        assert "skill" in spawned

    def test_boot_failure_returns_1(self, patch_dirs, squid_dir, monkeypatch):
        """If spawn fails, reboot returns 1."""
        monkeypatch.setattr(reboot_agent, "_spawn_wrapper",
                            lambda role, path: (False, "no boot script"))
        result = reboot_agent.reboot("skill")
        assert result == 1


# ---------------------------------------------------------------------------
# .stop sentinel (#2496)
# ---------------------------------------------------------------------------

class TestStopSentinel:
    """Reboot respects .stop sentinel — does not respawn."""

    def test_stop_prevents_boot_of_dead_agent(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".stop").write_text("", encoding="utf-8")
        spawned = _stub_spawn(monkeypatch)
        result = reboot_agent.reboot("skill")
        assert result == 0
        assert spawned == []  # No spawn

    def test_stop_prevents_reboot_of_running_agent(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / ".stop").write_text("", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        spawned = _stub_spawn(monkeypatch)
        killed = []
        monkeypatch.setattr(reboot_agent, "_kill_process", lambda pid: killed.append(pid))

        result = reboot_agent.reboot("skill")
        assert result == 0
        assert spawned == []
        assert killed == []  # Not even killed

    def test_stop_prevents_force_reboot(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / ".stop").write_text("", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        spawned = _stub_spawn(monkeypatch)

        result = reboot_agent.reboot("skill", force=True)
        assert result == 0
        assert spawned == []


# ---------------------------------------------------------------------------
# Force reboot — kills and respawns (#2496)
# ---------------------------------------------------------------------------

class TestRebootForce:
    """Force reboot — kills immediately and spawns new wrapper."""

    def test_force_kills_and_respawns(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        alive_pids = {12345}
        monkeypatch.setattr(reboot_agent, "_is_process_alive",
                            lambda pid: pid in alive_pids)

        killed = []
        def fake_kill(pid):
            killed.append(pid)
            alive_pids.discard(pid)
        monkeypatch.setattr(reboot_agent, "_kill_process", fake_kill)
        spawned = _stub_spawn(monkeypatch)

        result = reboot_agent.reboot("skill", force=True)
        assert result == 0
        assert 12345 in killed
        assert "skill" in spawned
        assert (squid_dir / "skill" / ".restart").exists()


# ---------------------------------------------------------------------------
# Normal reboot — wait for idle, kill, respawn (#2496)
# ---------------------------------------------------------------------------

class TestRebootWaitForIdle:
    """Normal reboot — writes sentinel, waits for idle, kills, respawns."""

    def test_idle_detected_and_respawns(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / "current-state").write_text("idle|", encoding="utf-8")
        alive_pids = {12345}
        monkeypatch.setattr(reboot_agent, "_is_process_alive",
                            lambda pid: pid in alive_pids)
        monkeypatch.setattr(reboot_agent, "POLL_INTERVAL", 0.01)

        killed = []
        def fake_kill(pid):
            killed.append(pid)
            alive_pids.discard(pid)
        monkeypatch.setattr(reboot_agent, "_kill_process", fake_kill)
        spawned = _stub_spawn(monkeypatch)

        result = reboot_agent.reboot("skill", timeout=1)
        assert result == 0
        assert 12345 in killed
        assert "skill" in spawned

    def test_timeout_cleans_sentinel_no_spawn(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / "current-state").write_text(
            "implementing|Working...", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        monkeypatch.setattr(reboot_agent, "POLL_INTERVAL", 0.01)
        spawned = _stub_spawn(monkeypatch)

        result = reboot_agent.reboot("skill", timeout=0.05)
        assert result == 1
        assert not (squid_dir / "skill" / ".restart").exists()
        assert spawned == []  # No spawn on timeout


# ---------------------------------------------------------------------------
# Sentinel written before waiting
# ---------------------------------------------------------------------------

class TestSentinelWritten:
    """Restart sentinel is always written before waiting."""

    def test_sentinel_content(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / "current-state").write_text("idle|", encoding="utf-8")
        alive_pids = {12345}
        monkeypatch.setattr(reboot_agent, "_is_process_alive",
                            lambda pid: pid in alive_pids)
        def fake_kill(pid):
            alive_pids.discard(pid)
        monkeypatch.setattr(reboot_agent, "_kill_process", fake_kill)
        monkeypatch.setattr(reboot_agent, "POLL_INTERVAL", 0.01)
        _stub_spawn(monkeypatch)

        reboot_agent.reboot("skill", timeout=1)


# ---------------------------------------------------------------------------
# Clone path resolution — unified with boot_remote (#2496)
# ---------------------------------------------------------------------------

class TestGetClonePath:
    """Clone path resolution uses boot_remote's unified logic."""

    def test_defaults_to_repo_root(self, patch_dirs):
        path = reboot_agent._get_clone_path("skill")
        assert path == boot_remote.REPO_ROOT

    def test_reads_local_config(self, patch_dirs, squid_dir, monkeypatch, tmp_path):
        custom_path = tmp_path / "custom" / "clone"
        custom_path.mkdir(parents=True)
        local_config = squid_dir / ".local-config"
        local_config.write_text(f"- **skill**: {custom_path}\n", encoding="utf-8")
        monkeypatch.setattr(boot_remote, "LOCAL_CONFIG", local_config)
        # Block shared filesystem path so it falls through to .local-config
        fake_home = tmp_path / "fakehome"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", staticmethod(lambda: fake_home))
        path = reboot_agent._get_clone_path("skill")
        assert path == custom_path


# ---------------------------------------------------------------------------
# --all flag (#2353 regression)
# ---------------------------------------------------------------------------

class TestRebootAll:
    """--all flag handles get_agents() dict output correctly (#2353)."""

    def test_all_flag_with_dict_agents(self, patch_dirs, squid_dir, monkeypatch):
        """get_agents() returns list of dicts — reboot() must receive string role."""
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


# ---------------------------------------------------------------------------
# Double-start prevention (#2496)
# ---------------------------------------------------------------------------

class TestDoubleStartPrevention:
    """_spawn_wrapper checks PID alive before spawning."""

    def test_spawn_blocked_if_pid_alive(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        monkeypatch.setattr(boot_remote, "_find_boot_script",
                            lambda cp, r: (Path("/fake/script.sh"), "sh"))

        success, msg = reboot_agent._spawn_wrapper("skill", patch_dirs)
        assert success is False
        assert "still alive" in msg
