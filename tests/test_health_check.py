"""Tests for references/scripts/health_check.py — offline-fallback health probe.

Post-#4792 §5.4 trim: `.stop` / `.health` / legacy `.pid` reads removed.
Liveness is now PID-only via `.claude-pid`, with current-state mtime as
fallback when the PID file is missing.
"""

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


class TestReadClaudePidFile:
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

    def test_read_claude_pid_empty(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".claude-pid").write_text("")
        assert health_check._read_claude_pid_file(squid) is None


class TestCheckAgentHealth:
    def _setup_agent(self, tmp_path, role, state_text=None, state_age_seconds=0,
                     working_state=None, claude_pid=None):
        """Create a mock agent directory structure."""
        import os as _os
        squid = tmp_path / ".squidsquad" / role
        squid.mkdir(parents=True, exist_ok=True)

        if state_text is not None:
            state_file = squid / "current-state"
            state_file.write_text(state_text)
            if state_age_seconds > 0:
                mtime = time.time() - state_age_seconds
                _os.utime(state_file, (mtime, mtime))

        if working_state:
            (squid / "working-state.md").write_text(working_state)

        if claude_pid is not None:
            (squid / ".claude-pid").write_text(str(claude_pid))

        return tmp_path

    # --- PID-liveness branch (.claude-pid present) ---

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_pid_alive_recent_state(self, mock_alive, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|Waiting...",
                                  claude_pid=12345)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "healthy"
        assert result["health_source"] == "pid-check"
        assert result["pid"] == 12345
        assert "PID 12345 alive" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_pid_alive_but_stale_state(self, mock_alive, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|",
                                  state_age_seconds=3700,
                                  claude_pid=12345)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"
        assert result["health_source"] == "pid-check"
        assert "current-state stale" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_pid_alive_no_state_yet(self, mock_alive, tmp_path):
        """Freshly-booted agent: .claude-pid exists, current-state not yet written."""
        clone = self._setup_agent(tmp_path, "skill", claude_pid=12345)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "healthy"
        assert "freshly booted" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=False)
    def test_pid_dead(self, mock_alive, tmp_path):
        """`.claude-pid` exists but the PID is dead → stalled."""
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="idle|Waiting...",
                                  claude_pid=99999)
        result = health_check.check_agent_health("skill", clone, 30)
        assert result["health"] == "stalled"
        assert result["health_source"] == "pid-check"
        assert result["pid"] == 99999
        assert "PID 99999 is dead" in result["reason"]

    # --- mtime fallback (.claude-pid missing) ---

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
        assert ".claude-pid" in result["reason"]
        assert "current-state" in result["reason"]

    # --- Edge cases ---

    def test_missing_clone_path(self, tmp_path):
        result = health_check.check_agent_health("skill", tmp_path / "nonexistent", 30)
        assert result["health"] == "unknown"
        assert "does not exist" in result["reason"]

    @patch.object(health_check, "_is_process_alive", return_value=True)
    def test_task_extracted_from_working_state(self, mock_alive, tmp_path):
        clone = self._setup_agent(tmp_path, "skill",
                                  state_text="implementing|#42",
                                  claude_pid=12345,
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


class TestNoLegacyReads:
    """#4792 §5.4 source-grep guards: legacy sentinel reads must be gone."""

    def test_no_dot_health_read(self):
        source = (SCRIPTS / "health_check.py").read_text(encoding="utf-8")
        assert '".health"' not in source
        assert "'.health'" not in source

    def test_no_dot_stop_read(self):
        source = (SCRIPTS / "health_check.py").read_text(encoding="utf-8")
        assert '".stop"' not in source
        assert "'.stop'" not in source

    def test_no_legacy_dot_pid_parser(self):
        """Legacy `.pid` parser removed (Q16) — only `.claude-pid` remains."""
        source = (SCRIPTS / "health_check.py").read_text(encoding="utf-8")
        # bare `.pid` references should be gone; only `.claude-pid` remains
        assert '"/.pid"' not in source
        assert "_read_pid_file" not in source
        assert "_read_any_pid" not in source
        assert "_parse_health_file" not in source

    def test_docstring_mentions_offline_fallback(self):
        """Per CONTEXT-4792.md §5.4: docstring must note offline-fallback role."""
        source = (SCRIPTS / "health_check.py").read_text(encoding="utf-8")
        assert "offline fallback" in source.lower()
        assert "squidsquad_cli.py status" in source or "GET /status" in source
