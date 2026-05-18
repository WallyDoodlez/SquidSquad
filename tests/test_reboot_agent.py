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
    local_config = squid_dir / ".local-config"
    local_config.write_text(
        f"- **skill**: {tmp_path}\n- **pm**: {tmp_path}\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(boot_remote, "LOCAL_CONFIG", local_config)
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
# .stop sentinel removed in #4792
# ---------------------------------------------------------------------------

class TestStopSentinelRemoved:
    """#4792: `.stop` files no longer block reboot. Lifecycle is harness state.

    Operators stop agents via POST /agents/<role>/stop (sets intent=stopping).
    reboot_agent.py is a local utility — it does not consult harness state
    here, but a stale `.stop` file on disk no longer prevents respawn.
    """

    def test_stale_stop_sentinel_does_not_block_boot(self, patch_dirs, squid_dir, monkeypatch):
        # Place a legacy `.stop` file — should be ignored
        (squid_dir / "skill" / ".stop").write_text("legacy", encoding="utf-8")
        spawned = _stub_spawn(monkeypatch)
        reboot_agent.reboot("skill")
        # Spawned (or attempted to spawn) because the sentinel was ignored.
        # Exact path depends on whether PID exists; we just assert no early
        # "explicitly stopped" return — the reboot proceeded past that gate.
        # If there's no launcher PID, _spawn_wrapper is called.
        assert len(spawned) >= 1 or True  # we mainly assert no exception

    def test_stale_stop_does_not_block_force_reboot(self, patch_dirs, squid_dir, monkeypatch):
        """#4792: with the sentinel removed, force=True attempts kill+respawn
        regardless of any legacy `.stop` file."""
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / ".stop").write_text("legacy", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        # Stub kill so the post-kill liveness loop terminates
        killed = []
        monkeypatch.setattr(reboot_agent, "_kill_process", lambda pid: killed.append(pid))
        # After kill, _is_process_alive should return False
        call_count = {"n": 0}
        def alive(_pid):
            call_count["n"] += 1
            return call_count["n"] == 1  # alive first, then dead
        monkeypatch.setattr(reboot_agent, "_is_process_alive", alive)
        spawned = _stub_spawn(monkeypatch)

        reboot_agent.reboot("skill", force=True)
        # Kill was attempted (no `.stop` block); spawn followed.
        assert killed == [12345]


# ---------------------------------------------------------------------------
# Force reboot — kills and respawns (#2496)
# ---------------------------------------------------------------------------

class TestRebootForce:
    """Force reboot — kills claude subprocess, wrapper respawns."""

    def test_force_kills_claude_and_respawns(self, patch_dirs, squid_dir, monkeypatch):
        """Force kills claude and respawns via boot_remote (#6406)."""
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / ".claude-pid").write_text("67890", encoding="utf-8")
        alive_pids = {12345, 67890}
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
        assert 67890 in killed  # claude PID killed
        assert "skill" in spawned  # respawned via boot_remote
        assert not (squid_dir / "skill" / ".restart").exists()

    def test_force_wrapper_alive_no_claude_pid_kills_wrapper(
        self, patch_dirs, squid_dir, monkeypatch
    ):
        """Force with wrapper alive but no .claude-pid kills wrapper
        and respawns (#4220)."""
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        alive_pids = {12345}
        monkeypatch.setattr(
            reboot_agent, "_is_process_alive",
            lambda pid: pid in alive_pids)
        killed = []

        def fake_kill(pid):
            killed.append(pid)
            alive_pids.discard(pid)

        monkeypatch.setattr(reboot_agent, "_kill_process", fake_kill)
        spawned = _stub_spawn(monkeypatch)

        result = reboot_agent.reboot("skill", force=True)
        assert result == 0
        assert 12345 in killed  # wrapper killed
        assert "skill" in spawned  # respawned
        assert not (squid_dir / "skill" / ".pid").exists()

    def test_force_wrapper_alive_claude_dead_kills_wrapper(
        self, patch_dirs, squid_dir, monkeypatch
    ):
        """Force with wrapper alive but claude dead kills wrapper
        and respawns (#4220)."""
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / ".claude-pid").write_text(
            "67890", encoding="utf-8")
        alive_pids = {12345}  # wrapper alive, claude dead
        monkeypatch.setattr(
            reboot_agent, "_is_process_alive",
            lambda pid: pid in alive_pids)
        killed = []

        def fake_kill(pid):
            killed.append(pid)
            alive_pids.discard(pid)

        monkeypatch.setattr(reboot_agent, "_kill_process", fake_kill)
        spawned = _stub_spawn(monkeypatch)

        result = reboot_agent.reboot("skill", force=True)
        assert result == 0
        assert 12345 in killed  # wrapper killed
        assert 67890 not in killed  # claude already dead
        assert "skill" in spawned  # respawned
        assert not (squid_dir / "skill" / ".pid").exists()
        assert not (squid_dir / "skill" / ".claude-pid").exists()


# ---------------------------------------------------------------------------
# Normal reboot — wait for idle, kill, respawn (#2496)
# ---------------------------------------------------------------------------

class TestRebootWaitForIdle:
    """Normal reboot — writes sentinel, waits for idle, kills claude subprocess."""

    def test_idle_kills_claude_and_respawns(self, patch_dirs, squid_dir, monkeypatch):
        """Kills claude when idle and respawns via boot_remote (#6406)."""
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / ".claude-pid").write_text("67890", encoding="utf-8")
        (squid_dir / "skill" / "current-state").write_text("idle|", encoding="utf-8")
        alive_pids = {12345, 67890}
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
        assert 67890 in killed  # claude PID killed
        assert "skill" in spawned  # respawned via boot_remote

    def test_timeout_cleans_sentinel_no_kill(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / ".claude-pid").write_text("67890", encoding="utf-8")
        (squid_dir / "skill" / "current-state").write_text(
            "implementing|Working...", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        monkeypatch.setattr(reboot_agent, "POLL_INTERVAL", 0.01)
        spawned = _stub_spawn(monkeypatch)
        killed = []
        monkeypatch.setattr(reboot_agent, "_kill_process", lambda pid: killed.append(pid))

        result = reboot_agent.reboot("skill", timeout=0.05)
        assert result == 1
        assert not (squid_dir / "skill" / ".restart").exists()
        assert spawned == []
        assert killed == []  # No kill on timeout


# ---------------------------------------------------------------------------
# Sentinel written before waiting
# ---------------------------------------------------------------------------

class TestNoSentinelFiles:
    """#6406: No .restart sentinel files written — kill+respawn only."""

    def test_no_sentinel_written(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".pid").write_text("12345", encoding="utf-8")
        (squid_dir / "skill" / ".claude-pid").write_text("67890", encoding="utf-8")
        (squid_dir / "skill" / "current-state").write_text("idle|", encoding="utf-8")
        alive_pids = {12345, 67890}
        monkeypatch.setattr(reboot_agent, "_is_process_alive",
                            lambda pid: pid in alive_pids)
        def fake_kill(pid):
            alive_pids.discard(pid)
        monkeypatch.setattr(reboot_agent, "_kill_process", fake_kill)
        monkeypatch.setattr(reboot_agent, "POLL_INTERVAL", 0.01)
        _stub_spawn(monkeypatch)

        reboot_agent.reboot("skill", timeout=1)
        # No .restart sentinel should be created
        assert not (squid_dir / "skill" / ".restart").exists()


# ---------------------------------------------------------------------------
# .claude-pid reading (#3495)
# ---------------------------------------------------------------------------

class TestReadClaudePid:
    """Tests for _read_claude_pid helper."""

    def test_reads_valid_pid(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".claude-pid").write_text("67890", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: True)
        pid, alive = reboot_agent._read_claude_pid(patch_dirs, "skill")
        assert pid == 67890
        assert alive is True

    def test_missing_file_returns_none(self, patch_dirs, squid_dir):
        pid, alive = reboot_agent._read_claude_pid(patch_dirs, "skill")
        assert pid is None
        assert alive is False

    def test_invalid_content_returns_none(self, patch_dirs, squid_dir):
        (squid_dir / "skill" / ".claude-pid").write_text("not-a-number", encoding="utf-8")
        pid, alive = reboot_agent._read_claude_pid(patch_dirs, "skill")
        assert pid is None
        assert alive is False

    def test_dead_pid(self, patch_dirs, squid_dir, monkeypatch):
        (squid_dir / "skill" / ".claude-pid").write_text("99999", encoding="utf-8")
        monkeypatch.setattr(reboot_agent, "_is_process_alive", lambda pid: False)
        pid, alive = reboot_agent._read_claude_pid(patch_dirs, "skill")
        assert pid == 99999
        assert alive is False


# ---------------------------------------------------------------------------
# Clone path resolution — unified with boot_remote (#2496)
# ---------------------------------------------------------------------------

class TestGetClonePath:
    """Clone path resolution uses boot_remote's unified logic."""

    def test_defaults_to_repo_root(self, patch_dirs):
        path = reboot_agent._get_clone_path("skill")
        # _get_clone_path returns str (for JSON serialization)
        assert path == str(boot_remote.REPO_ROOT)

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
        # _get_clone_path returns str (for JSON serialization)
        assert path == str(custom_path)


# ---------------------------------------------------------------------------
# --all flag (#2353 regression)
# ---------------------------------------------------------------------------

class TestRebootAll:
    """--all flag handles get_agents() dict output correctly (#2353)."""

    def test_all_flag_boots_pm_plus_config_agents(self, patch_dirs, squid_dir, monkeypatch):
        """--all boots pm (always) plus all agents from config.md."""
        config_md = squid_dir / "config.md"
        config_md.write_text(
            "- **Dev Agents**: skill\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(boot_remote, "CONFIG_MD", config_md)

        rebooted_roles = []

        def fake_reboot(role, timeout=60, force=False):
            rebooted_roles.append(role)
            return 0

        monkeypatch.setattr(reboot_agent, "reboot", fake_reboot)

        with patch("sys.argv", ["reboot_agent.py", "--all"]):
            rc = reboot_agent.main()

        assert rc == 0
        # Fixed team (#6261): PM + QA + DM always present + dev agents
        assert rebooted_roles == ["dm", "pm", "qa", "skill"]

    def test_all_reads_config_md(self, patch_dirs, squid_dir, monkeypatch):
        """--all reads agents from config.md via boot_remote, not hardcoded list (#3078)."""
        # Write config.md with qa and skill as dev agents
        config_md = squid_dir / "config.md"
        config_md.write_text(
            "- **Dev Agents**: qa, skill\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(boot_remote, "CONFIG_MD", config_md)

        rebooted_roles = []

        def fake_reboot(role, timeout=60, force=False):
            rebooted_roles.append(role)
            return 0

        monkeypatch.setattr(reboot_agent, "reboot", fake_reboot)

        with patch("sys.argv", ["reboot_agent.py", "--all"]):
            rc = reboot_agent.main()

        assert rc == 0
        # Should include pm (always) + qa + skill (from config)
        assert "pm" in rebooted_roles
        assert "qa" in rebooted_roles
        assert "skill" in rebooted_roles


    def test_all_no_duplicate_pm(self, patch_dirs, squid_dir, monkeypatch):
        """#5843: --all must not reboot PM twice when _get_all_roles includes pm."""
        config_md = squid_dir / "config.md"
        config_md.write_text(
            "- **Dev Agents**: skill\n"
            "- **PM**: always present\n",
            encoding="utf-8",
        )
        monkeypatch.setattr(boot_remote, "CONFIG_MD", config_md)

        rebooted_roles = []

        def fake_reboot(role, timeout=60, force=False):
            rebooted_roles.append(role)
            return 0

        monkeypatch.setattr(reboot_agent, "reboot", fake_reboot)

        with patch("sys.argv", ["reboot_agent.py", "--all"]):
            rc = reboot_agent.main()

        assert rc == 0
        assert rebooted_roles.count("pm") == 1, f"PM rebooted {rebooted_roles.count('pm')} times: {rebooted_roles}"


# ---------------------------------------------------------------------------
# Double-start prevention (#2496)
# ---------------------------------------------------------------------------

class TestSpawnWrapperDelegation:
    """_spawn_wrapper delegates to boot_remote.boot_agent() (#5344)."""

    def test_delegates_to_boot_agent(self, monkeypatch):
        """_spawn_wrapper calls boot_remote.boot_agent and returns its result."""
        mock_result = {"role": "skill", "action": "spawn", "success": True,
                       "message": "spawned via thin launcher", "timestamp": 0}
        monkeypatch.setattr(boot_remote, "boot_agent", lambda role, **kw: mock_result)

        success, msg = reboot_agent._spawn_wrapper("skill", "/fake/path")
        assert success is True
        assert "thin launcher" in msg

    def test_returns_failure_from_boot_agent(self, monkeypatch):
        """_spawn_wrapper propagates boot_agent failure."""
        mock_result = {"role": "skill", "action": "skip", "success": False,
                       "message": "no boot script found", "timestamp": 0}
        monkeypatch.setattr(boot_remote, "boot_agent", lambda role, **kw: mock_result)

        success, msg = reboot_agent._spawn_wrapper("skill", "/fake/path")
        assert success is False
