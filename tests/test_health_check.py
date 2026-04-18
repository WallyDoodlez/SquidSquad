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
        config = tmp_path / ".local-config"
        config.write_text(
            "# comment\n\n- **pm**: /path/to/pm\n- **skill**: /path/to/skill\n"
        )
        with patch.object(health_check, "LOCAL_CONFIG", config):
            result = health_check._parse_local_config()
        assert "pm" in result
        assert "skill" in result
        assert result["pm"] == Path("/path/to/pm")

    def test_missing_file_returns_empty(self, tmp_path):
        with patch.object(health_check, "LOCAL_CONFIG", tmp_path / "missing"):
            result = health_check._parse_local_config()
        assert result == {}

    def test_malformed_lines_skipped(self, tmp_path):
        config = tmp_path / ".local-config"
        config.write_text("not a valid line\n- **pm**: /good/path\ngarbage\n")
        with patch.object(health_check, "LOCAL_CONFIG", config):
            result = health_check._parse_local_config()
        assert len(result) == 1
        assert "pm" in result


class TestReadInterval:
    def test_reads_from_config(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("## Iteration Interval\n\n- **Minutes**: 45\n")
        with patch.object(health_check, "CONFIG_MD", config):
            assert health_check._read_interval() == 45

    def test_missing_config_returns_default(self, tmp_path):
        with patch.object(health_check, "CONFIG_MD", tmp_path / "missing"):
            assert health_check._read_interval() == 30

    def test_no_minutes_field_returns_default(self, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("## Some Section\n\n- **Foo**: bar\n")
        with patch.object(health_check, "CONFIG_MD", config):
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
                     stop=False, working_state=None, health_text=None, pid=None):
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
        health_file = tmp_path / ".squidsquad" / "skill" / ".health"
        assert "dead" in health_file.read_text(encoding="utf-8")

    def test_health_alive_but_no_pid_file(self, tmp_path):
        """When .health=alive but no .pid file exists, cannot verify liveness."""
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|Waiting...",
                                  health_text="alive")
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"
        assert "no .pid file" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=False)
    def test_pid_dead_autocorrects_health_file(self, mock_alive, tmp_path):
        """When PID is dead, .health file is auto-corrected to 'dead'."""
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|",
                                  health_text="alive", pid=11111)
        health_check.check_agent_health("skill", clone, 30)
        health_file = tmp_path / ".squidsquad" / "skill" / ".health"
        content = health_file.read_text(encoding="utf-8")
        assert content.startswith("dead")

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
