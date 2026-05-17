"""Tests for references/scripts/health_check.py — health classification with .health file support."""

import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import health_check


class TestParseLocalConfig:
    def test_parses_valid_entries(self, tmp_path):
        pm_path = tmp_path / "pm-clone"
        skill_path = tmp_path / "skill-clone"
        config = tmp_path / ".local-config"
        config.write_text(
            f"# comment\n\n- **pm**: {pm_path}\n- **skill**: {skill_path}\n"
        )
        with patch.object(health_check, "LOCAL_CONFIG", config):
            result = health_check._parse_local_config()
        assert "pm" in result
        assert "skill" in result
        assert result["pm"] == pm_path

    def test_missing_file_exits(self, tmp_path):
        """#3100: Missing .local-config exits with code 2, not empty dict."""
        with patch.object(health_check, "LOCAL_CONFIG", tmp_path / "missing"):
            with pytest.raises(SystemExit) as exc_info:
                health_check._parse_local_config()
        assert exc_info.value.code == 2

    def test_malformed_lines_skipped(self, tmp_path):
        config = tmp_path / ".local-config"
        config.write_text("not a valid line\n- **pm**: /good/path\ngarbage\n")
        with patch.object(health_check, "LOCAL_CONFIG", config):
            result = health_check._parse_local_config()
        assert len(result) == 1
        assert "pm" in result


class TestParseLocalConfigMandatory:
    """Tests for #3100 — .local-config is mandatory, no global fallback."""

    def test_valid_local_config_parses(self, tmp_path):
        """When .local-config exists with valid entries, parse them."""
        skill_path = tmp_path / "project" / "skill"
        config = tmp_path / ".local-config"
        config.write_text(f"- **skill**: {skill_path}\n")

        with patch.object(health_check, "LOCAL_CONFIG", config):
            result = health_check._parse_local_config()

        assert result["skill"] == skill_path

    def test_missing_local_config_exits(self, tmp_path):
        """When .local-config is missing, exit with code 2 and clear error."""
        with patch.object(health_check, "LOCAL_CONFIG", tmp_path / "missing"):
            with pytest.raises(SystemExit) as exc_info:
                health_check._parse_local_config()
        assert exc_info.value.code == 2

    def test_empty_local_config_exits(self, tmp_path):
        """When .local-config exists but has no valid entries, exit with code 2."""
        config = tmp_path / ".local-config"
        config.write_text("# comment only\n")

        with patch.object(health_check, "LOCAL_CONFIG", config):
            with pytest.raises(SystemExit) as exc_info:
                health_check._parse_local_config()
        assert exc_info.value.code == 2

    def test_no_global_clones_fallback(self, tmp_path):
        """Global ~/.squidsquad/clones/ is never used, even if it exists (#3100)."""
        global_clones = tmp_path / "fakehome" / ".squidsquad" / "clones"
        global_clones.mkdir(parents=True)
        (global_clones / "skill").write_text(f"{tmp_path / 'fallback'}\n")

        with patch.object(health_check, "LOCAL_CONFIG", tmp_path / "missing"):
            with pytest.raises(SystemExit) as exc_info:
                health_check._parse_local_config()
        assert exc_info.value.code == 2


class TestReadInterval:
    def test_reads_from_config(self):
        with patch("config.get_field", return_value="45"):
            assert health_check._read_interval() == 45

    def test_missing_config_returns_default(self):
        with patch("config.get_field", return_value=None):
            assert health_check._read_interval() == 30

    def test_import_error_returns_default(self):
        with patch("config.get_field", side_effect=ImportError):
            assert health_check._read_interval() == 30

    def test_non_numeric_returns_default(self):
        """#8116 regression: malformed config value must not crash."""
        with patch("config.get_field", return_value="10 items"):
            assert health_check._read_interval() == 30

    def test_empty_string_returns_default(self):
        with patch("config.get_field", return_value=""):
            assert health_check._read_interval() == 30


class TestParseCurrentState:
    def test_valid_state(self):
        phase, desc = health_check._parse_current_state("implementing|Working on #5...")
        assert phase == "implementing"
        assert desc == "Working on #5..."

    def test_empty_input(self):
        phase, desc = health_check._parse_current_state("")
        assert phase == ""
        assert desc == ""

    def test_none_input(self):
        phase, desc = health_check._parse_current_state(None)
        assert phase == ""
        assert desc == ""

    def test_no_pipe(self):
        phase, desc = health_check._parse_current_state("idle")
        assert phase == "idle"
        assert desc == ""

    def test_multiline_uses_first(self):
        phase, desc = health_check._parse_current_state("pulling|sync\nextra line")
        assert phase == "pulling"
        assert desc == "sync"


class TestParseWorkingStateTask:
    def test_active_task(self):
        text = "# Working State\n\n- **Task**: #42\n- **Status**: in-progress"
        assert health_check._parse_working_state_task(text) == "#42"

    def test_no_task(self):
        text = "# Working State\n\n- **Task**: none\n"
        assert health_check._parse_working_state_task(text) == "idle"

    def test_empty_input(self):
        assert health_check._parse_working_state_task("") == "unknown"

    def test_none_input(self):
        assert health_check._parse_working_state_task(None) == "unknown"


class TestParseHealthFile:
    def test_alive_status(self):
        status, detail = health_check._parse_health_file("alive")
        assert status == "alive"
        assert detail == ""

    def test_error_with_detail(self):
        status, detail = health_check._parse_health_file("error|gh auth failed")
        assert status == "error"
        assert detail == "gh auth failed"

    def test_none_input(self):
        status, detail = health_check._parse_health_file(None)
        assert status is None
        assert detail is None

    def test_empty_input(self):
        status, detail = health_check._parse_health_file("")
        assert status is None
        assert detail is None

    def test_booting_status(self):
        status, detail = health_check._parse_health_file("booting")
        assert status == "booting"

    def test_backoff_status(self):
        status, detail = health_check._parse_health_file("backoff")
        assert status == "backoff"

    def test_multiline_uses_first(self):
        status, detail = health_check._parse_health_file("alive\nextra")
        assert status == "alive"


class TestCheckAgentHealth:
    def _setup_agent(self, tmp_path, role, state_text=None, state_age_seconds=0,
                     stop=False, working_state=None, health_text=None, pid=None,
                     claude_pid=None):
        """Create a mock agent directory structure."""
        import os as _os
        squid = tmp_path / ".squidsquad" / role
        squid.mkdir(parents=True, exist_ok=True)

        if stop:
            (squid / ".stop").write_text("stopped")

        if state_text is not None:
            state_file = squid / "current-state"
            state_file.write_text(state_text)
            if state_age_seconds > 0:
                mtime = time.time() - state_age_seconds
                _os.utime(state_file, (mtime, mtime))

        if working_state:
            (squid / "working-state.md").write_text(working_state)

        if health_text is not None:
            (squid / ".health").write_text(health_text)

        if pid is not None:
            (squid / ".pid").write_text(str(pid))

        if claude_pid is not None:
            (squid / ".claude-pid").write_text(str(claude_pid))

        return tmp_path

    # --- .health file primary detection ---

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_health_alive_with_recent_state(self, mock_alive, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|Waiting...",
                                  health_text="alive", pid=12345)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "healthy"
        assert result["health_source"] == "health-file"
        assert result["health_file_status"] == "alive"

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_health_alive_but_stale_state(self, mock_alive, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|",
                                  state_age_seconds=3700,
                                  health_text="alive", pid=12345)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"
        assert result["health_source"] == "health-file"
        assert "stale" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_health_alive_no_state_yet(self, mock_alive, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text="alive", pid=12345)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "healthy"
        assert "freshly booted" in result["reason"]

    # --- PID cross-check tests ---

    @patch.object(health_check, "_is_process_alive", return_value=False)
    def test_health_alive_but_pid_dead(self, mock_alive, tmp_path):
        """When .health=alive but PID is dead, agent should be stalled."""
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|Waiting...",
                                  health_text="alive", pid=99999)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"
        assert "PID 99999 is dead" in result["reason"]

    def test_health_alive_but_no_pid_file(self, tmp_path):
        """When .health=alive but no .pid file exists, cannot verify liveness."""
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|Waiting...",
                                  health_text="alive")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"
        assert "no .pid file" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=False)
    def test_pid_dead_detected_as_stalled(self, mock_alive, tmp_path):
        """When PID is dead, agent is detected as stalled (#2183)."""
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|",
                                  health_text="alive", pid=11111)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"

    # --- Heartbeat epoch tests (#2183) ---

    def test_heartbeat_fresh(self, tmp_path):
        """New-format heartbeat (epoch) within 10s → healthy."""
        now = int(time.time())
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text=str(now))
        result = health_check.check_agent_health("skill", clone, 30, now=now)
        assert result["health"] == "healthy"
        assert "heartbeat" in result["reason"]

    def test_heartbeat_stale_no_pid(self, tmp_path):
        """New-format heartbeat older than 10s, no PID file → stalled (#5429)."""
        now = int(time.time())
        old_epoch = now - 30  # 30s old
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text=str(old_epoch))
        result = health_check.check_agent_health("skill", clone, 30, now=now)
        assert result["health"] == "stalled"
        assert "heartbeat stale" in result["reason"]
        assert "no PID file" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_heartbeat_stale_but_pid_alive(self, mock_alive, tmp_path):
        """Heartbeat stale but .claude-pid alive → healthy with warning (#5429)."""
        now = int(time.time())
        old_epoch = now - 30  # 30s old
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text=str(old_epoch),
                                  claude_pid=12345)
        result = health_check.check_agent_health("skill", clone, 30, now=now)
        assert result["health"] == "healthy"
        assert "PID 12345 alive" in result["reason"]
        assert "harness/wrapper may be down" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_heartbeat_stale_pid_file_fallback(self, mock_alive, tmp_path):
        """Heartbeat stale, no .claude-pid but .pid alive → healthy (#5429)."""
        now = int(time.time())
        old_epoch = now - 30
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text=str(old_epoch),
                                  pid=54321)
        result = health_check.check_agent_health("skill", clone, 30, now=now)
        assert result["health"] == "healthy"
        assert "PID 54321 alive" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=False)
    def test_heartbeat_stale_and_pid_dead(self, mock_alive, tmp_path):
        """Heartbeat stale and PID dead → stalled (#5429)."""
        now = int(time.time())
        old_epoch = now - 30
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text=str(old_epoch),
                                  claude_pid=99999)
        result = health_check.check_agent_health("skill", clone, 30, now=now)
        assert result["health"] == "stalled"
        assert "PID 99999 is dead" in result["reason"]

    # --- Legacy status tests ---

    def test_health_booting(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text="booting")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "healthy"
        assert "booting" in result["reason"]

    def test_health_restarting(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text="restarting")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "healthy"
        assert "restarting" in result["reason"]

    def test_health_backoff(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text="backoff")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"
        assert "backoff" in result["reason"]

    def test_health_dead(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text="dead")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"
        assert "dead" in result["reason"]

    def test_health_error(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text="error|gh auth failed")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "error"
        assert "gh auth failed" in result["reason"]

    def test_health_error_no_detail(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  health_text="error")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "error"

    # --- mtime fallback (no .health file) ---

    def test_mtime_fallback_healthy(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|Waiting...",
                                  state_age_seconds=5)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "healthy"
        assert result["health_source"] == "mtime-fallback"

    def test_mtime_fallback_stalled(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|",
                                  state_age_seconds=3700)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"
        assert result["health_source"] == "mtime-fallback"

    def test_mtime_fallback_no_files(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "unknown"
        assert "no .health file, no current-state" in result["reason"]

    # --- Edge cases ---

    def test_stopped_agent(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill", stop=True,
                                  health_text="alive")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stopped"
        assert ".stop" in result["reason"]

    def test_missing_clone_path(self, tmp_path):
        result = health_check.check_agent_health("skill", tmp_path / "nonexistent", 30)
        assert result["health"] == "unknown"
        assert "does not exist" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_task_extracted_from_working_state(self, mock_alive, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="implementing|#42",
                                  health_text="alive", pid=12345,
                                  working_state="# Working State\n\n- **Task**: #42\n")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["task"] == "#42"

    def test_injectable_now(self, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|")
        fixed_now = time.time() + 7200
        result = health_check.check_agent_health("skill", clone, 30, now=fixed_now)
        assert result["health"] == "stalled"
        assert result["last_active_minutes_ago"] >= 119


class TestReadClaudePidFile:
    """Tests for _read_claude_pid_file and _read_any_pid (#5429)."""

    def test_read_claude_pid_exists(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".claude-pid").write_text("12345")
        assert health_check._read_claude_pid_file(squid) == 12345

    def test_read_claude_pid_missing(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        assert health_check._read_claude_pid_file(squid) is None

    def test_read_claude_pid_invalid(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".claude-pid").write_text("not-a-number")
        assert health_check._read_claude_pid_file(squid) is None

    def test_read_any_pid_prefers_claude_pid(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".claude-pid").write_text("111")
        (squid / ".pid").write_text("222")
        assert health_check._read_any_pid(squid) == 111

    def test_read_any_pid_falls_back_to_pid(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".pid").write_text("222")
        assert health_check._read_any_pid(squid) == 222

    def test_read_any_pid_none_when_neither(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        assert health_check._read_any_pid(squid) is None


class TestAliveBranchUsesAnyPid:
    """#7611: alive health branch must use _read_any_pid, not _read_pid_file."""

    def test_alive_branch_reads_claude_pid(self):
        """The alive branch source must call _read_any_pid, not _read_pid_file."""
        import inspect
        source = inspect.getsource(health_check.check_agent_health)
        # Find the "alive" branch and verify it uses _read_any_pid
        lines = source.splitlines()
        in_alive = False
        uses_any_pid = False
        for line in lines:
            if '"alive"' in line or "'alive'" in line:
                in_alive = True
            elif in_alive and "_read_any_pid" in line:
                uses_any_pid = True
                break
            elif in_alive and ("elif" in line or "else:" in line):
                break  # Left the alive branch
        assert uses_any_pid, \
            "alive branch must use _read_any_pid for thin-launcher compat (#7611)"
