"""Tests for references/scripts/thin_launcher.py (#4966)."""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import thin_launcher


class TestPIDManagement:
    """Thin launcher PID file operations."""

    def test_write_pid(self, tmp_path):
        """Writes PID file atomically."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        thin_launcher._write_pid(str(tmp_path), "skill", 12345)
        pid_file = role_dir / ".claude-pid"
        assert pid_file.exists()
        assert pid_file.read_text(encoding="utf-8") == "12345"
        # .tmp should not remain
        assert not pid_file.with_suffix(".tmp").exists()

    def test_clear_pid(self, tmp_path):
        """Removes PID file on exit."""
        role_dir = tmp_path / ".squidsquad" / "skill"
        role_dir.mkdir(parents=True)
        pid_file = role_dir / ".claude-pid"
        pid_file.write_text("12345", encoding="utf-8")
        thin_launcher._clear_pid(str(tmp_path), "skill")
        assert not pid_file.exists()

    def test_clear_pid_missing(self, tmp_path):
        """No error when PID file doesn't exist."""
        thin_launcher._clear_pid(str(tmp_path), "skill")  # should not raise


class TestEffortLevel:
    """#5573: per-agent effort level from config."""

    def test_reads_effort_from_config(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="max"):
            result = thin_launcher._get_effort_level("pm")
            assert result == "max"

    def test_defaults_to_high(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value=None):
            result = thin_launcher._get_effort_level("skill")
            assert result == "high"

    def test_rejects_invalid_level(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="turbo"):
            result = thin_launcher._get_effort_level("pm")
            assert result == "high"

    def test_handles_config_failure(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=Exception("no config")):
            result = thin_launcher._get_effort_level("pm")
            assert result == "high"


class TestClaudeInvocation:
    """Verify claude CLI flags passed by thin launcher."""

    def test_strict_mcp_config_flag(self, tmp_path):
        """#8308: --strict-mcp-config prevents MCP plugins from crowding out built-in tools."""
        sqdir = tmp_path / ".squidsquad" / "skill"
        sqdir.mkdir(parents=True)
        captured_cmd = []

        def mock_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            proc = MagicMock()
            proc.pid = 99999
            proc.wait.return_value = 0
            return proc

        with patch("thin_launcher.subprocess.Popen", side_effect=mock_popen), \
             patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("thin_launcher._get_interval", return_value="30"), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            thin_launcher.main()

        assert "--strict-mcp-config" in captured_cmd
        # Flag must appear before the spawn prompt (positional, last arg per #9725).
        prompt = captured_cmd[-1]
        assert prompt.startswith("/loop "), f"Expected /loop spawn prompt, got: {prompt}"
        flag_idx = captured_cmd.index("--strict-mcp-config")
        assert flag_idx < len(captured_cmd) - 1

    def test_append_system_prompt_includes_role(self, tmp_path):
        """Agent role is passed via --append-system-prompt."""
        sqdir = tmp_path / ".squidsquad" / "skill"
        sqdir.mkdir(parents=True)
        captured_cmd = []

        def mock_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            proc = MagicMock()
            proc.pid = 99999
            proc.wait.return_value = 0
            return proc

        with patch("thin_launcher.subprocess.Popen", side_effect=mock_popen), \
             patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("thin_launcher._get_interval", return_value="30"), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            thin_launcher.main()

        idx = captured_cmd.index("--append-system-prompt")
        assert captured_cmd[idx + 1] == "SQUIDSQUAD_ROLE=skill"


class TestSpawnPromptIsLoopRegistration:
    """#9725: spawn prompt registers /loop instead of running one inline cycle."""

    def test_prompt_is_loop_command(self, tmp_path):
        """Final positional arg starts with /loop."""
        sqdir = tmp_path / ".squidsquad" / "skill"
        sqdir.mkdir(parents=True)
        captured_cmd = []

        def mock_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            proc = MagicMock(); proc.pid = 99999; proc.wait.return_value = 0
            return proc

        with patch("thin_launcher.subprocess.Popen", side_effect=mock_popen), \
             patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("thin_launcher._get_interval", return_value="30"), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            thin_launcher.main()

        # Prompt is the final positional arg (after --dangerously-skip-permissions)
        prompt = captured_cmd[-1]
        assert prompt == "/loop 30m execute one Ralph Loop cycle"

    def test_legacy_boot_prompt_absent(self, tmp_path):
        """The pre-#9725 'Boot. Begin your first Ralph Loop cycle now.' prompt is gone."""
        sqdir = tmp_path / ".squidsquad" / "skill"
        sqdir.mkdir(parents=True)
        captured_cmd = []

        def mock_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            proc = MagicMock(); proc.pid = 99999; proc.wait.return_value = 0
            return proc

        with patch("thin_launcher.subprocess.Popen", side_effect=mock_popen), \
             patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("thin_launcher._get_interval", return_value="30"), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            thin_launcher.main()

        assert "Boot. Begin your first Ralph Loop cycle now." not in captured_cmd

    def test_interval_substituted_from_config(self, tmp_path):
        """Interval value flows from _get_interval() into the spawn prompt."""
        sqdir = tmp_path / ".squidsquad" / "skill"
        sqdir.mkdir(parents=True)
        captured_cmd = []

        def mock_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            proc = MagicMock(); proc.pid = 99999; proc.wait.return_value = 0
            return proc

        with patch("thin_launcher.subprocess.Popen", side_effect=mock_popen), \
             patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("thin_launcher._get_interval", return_value="15"), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            thin_launcher.main()

        assert captured_cmd[-1] == "/loop 15m execute one Ralph Loop cycle"


class TestGetInterval:
    """#9725: _get_interval reads from config.md and falls back safely."""

    def test_reads_interval_from_config(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="20"):
            assert thin_launcher._get_interval() == "20"

    def test_defaults_to_30_when_missing(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value=None):
            assert thin_launcher._get_interval() == "30"

    def test_defaults_to_30_on_empty_string(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value=""):
            assert thin_launcher._get_interval() == "30"

    def test_defaults_to_30_when_config_raises(self):
        def boom(_):
            raise RuntimeError("config unreadable")
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=boom):
            assert thin_launcher._get_interval() == "30"

    def test_handles_systemexit_from_config_get(self):
        """config.get_field calls sys.exit(1) on missing field — must not propagate."""
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", side_effect=SystemExit(1)):
            assert thin_launcher._get_interval() == "30"

    def test_strips_whitespace(self):
        with patch.dict("sys.modules", {"config": MagicMock()}), \
             patch("config.get_field", return_value="  45  "):
            assert thin_launcher._get_interval() == "45"


class TestThinLauncherBoot:
    """Thin launcher boot_remote integration."""

    def test_find_boot_script_prefers_thin_launcher(self, tmp_path):
        """boot_remote prefers thin launcher over wrapper scripts (#4966)."""
        import boot_remote

        # Create thin launcher
        scripts_dir = tmp_path / "references" / "scripts"
        scripts_dir.mkdir(parents=True)
        launcher = scripts_dir / "thin_launcher.py"
        launcher.write_text("# thin launcher")

        # Also create legacy wrapper
        sqdir = tmp_path / ".squidsquad"
        sqdir.mkdir()
        (sqdir / "start-skill.ps1").write_text("# legacy wrapper")

        path, script_type = boot_remote._find_boot_script(str(tmp_path), "skill")
        assert script_type == "thin"
        assert "thin_launcher" in str(path)


# ---------------------------------------------------------------------------
# Singleton enforcement (#8692)
# ---------------------------------------------------------------------------

class TestIsProcessAlive:
    """Cross-platform PID liveness."""

    def test_invalid_pid_is_not_alive(self):
        assert thin_launcher._is_process_alive(None) is False
        assert thin_launcher._is_process_alive(0) is False
        assert thin_launcher._is_process_alive(-1) is False

    def test_own_pid_is_alive(self):
        assert thin_launcher._is_process_alive(os.getpid()) is True

    def test_unlikely_pid_is_not_alive(self):
        # 2**31 - 1 is well above any reasonable PID and below the max
        # Windows/Linux PID. tasklist / os.kill should both report not-found.
        assert thin_launcher._is_process_alive(2_147_483_646) is False


class TestCheckSingleton:
    """Read .claude-pid and report whether another agent is alive."""

    def test_no_pid_file_returns_none(self, tmp_path):
        (tmp_path / ".squidsquad" / "skill").mkdir(parents=True)
        assert thin_launcher._check_singleton(str(tmp_path), "skill") is None

    def test_corrupt_pid_file_returns_none(self, tmp_path):
        d = tmp_path / ".squidsquad" / "skill"
        d.mkdir(parents=True)
        (d / ".claude-pid").write_text("not-a-pid", encoding="utf-8")
        assert thin_launcher._check_singleton(str(tmp_path), "skill") is None

    def test_stale_pid_returns_none(self, tmp_path):
        d = tmp_path / ".squidsquad" / "skill"
        d.mkdir(parents=True)
        (d / ".claude-pid").write_text("2147483646", encoding="utf-8")
        with patch("thin_launcher._is_process_alive", return_value=False):
            assert thin_launcher._check_singleton(str(tmp_path), "skill") is None

    def test_alive_pid_returns_pid(self, tmp_path):
        d = tmp_path / ".squidsquad" / "skill"
        d.mkdir(parents=True)
        (d / ".claude-pid").write_text("12345", encoding="utf-8")
        with patch("thin_launcher._is_process_alive", return_value=True):
            assert thin_launcher._check_singleton(str(tmp_path), "skill") == 12345

    def test_own_pid_treated_as_stale(self, tmp_path):
        """Defensive: if our own PID is in the file (shouldn't happen) it's stale."""
        d = tmp_path / ".squidsquad" / "skill"
        d.mkdir(parents=True)
        (d / ".claude-pid").write_text(str(os.getpid()), encoding="utf-8")
        assert thin_launcher._check_singleton(str(tmp_path), "skill") is None


class TestSingletonEnforcement:
    """main() refuses to boot when another live agent of the same role exists."""

    def test_refuses_when_live_pid_exists(self, tmp_path, capsys):
        d = tmp_path / ".squidsquad" / "skill"
        d.mkdir(parents=True)
        (d / ".claude-pid").write_text("12345", encoding="utf-8")

        with patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._is_process_alive", return_value=True), \
             patch("thin_launcher.subprocess.Popen") as mock_popen, \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            rc = thin_launcher.main()

        assert rc == 3
        mock_popen.assert_not_called()
        err = capsys.readouterr().err
        assert "REFUSED" in err
        assert "12345" in err
        assert "skill" in err

    def test_force_flag_overrides_singleton(self, tmp_path):
        """--force allows boot even when a live PID is recorded."""
        d = tmp_path / ".squidsquad" / "skill"
        d.mkdir(parents=True)
        (d / ".claude-pid").write_text("12345", encoding="utf-8")

        proc = MagicMock()
        proc.pid = 99999
        proc.wait.return_value = 0

        with patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._is_process_alive", return_value=True), \
             patch("thin_launcher.subprocess.Popen", return_value=proc), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("sys.argv", ["thin_launcher.py", "skill", "--force"]):
            rc = thin_launcher.main()

        assert rc == 0

    def test_proceeds_when_pid_is_stale(self, tmp_path):
        """Stale .claude-pid does not block boot."""
        d = tmp_path / ".squidsquad" / "skill"
        d.mkdir(parents=True)
        (d / ".claude-pid").write_text("12345", encoding="utf-8")

        proc = MagicMock()
        proc.pid = 99999
        proc.wait.return_value = 0

        with patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._is_process_alive", return_value=False), \
             patch("thin_launcher.subprocess.Popen", return_value=proc) as mock_popen, \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            rc = thin_launcher.main()

        assert rc == 0
        # Boot actually launched claude (singleton check passed despite stale PID).
        mock_popen.assert_called_once()

    def test_proceeds_when_no_pid_file(self, tmp_path):
        """No .claude-pid file → fresh boot proceeds normally."""
        (tmp_path / ".squidsquad" / "skill").mkdir(parents=True)

        proc = MagicMock()
        proc.pid = 99999
        proc.wait.return_value = 0

        with patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher.subprocess.Popen", return_value=proc), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            rc = thin_launcher.main()

        assert rc == 0


class TestWritePidFailure:
    """#8879: if _write_pid raises after Popen, claude must still be waited on."""

    @pytest.mark.parametrize("wait_code", [0, 42])
    def test_oserror_in_write_pid_does_not_orphan_child(
        self, tmp_path, capsys, wait_code,
    ):
        """_write_pid OSError is caught; proc.wait() still runs and exit code propagates."""
        (tmp_path / ".squidsquad" / "skill").mkdir(parents=True)

        proc = MagicMock()
        proc.pid = 99999
        proc.wait.return_value = wait_code
        proc.kill = MagicMock()

        with patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher.subprocess.Popen", return_value=proc), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("thin_launcher._write_pid",
                   side_effect=OSError("disk full")), \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            rc = thin_launcher.main()

        # Exit code reflects proc.wait(), not the OSError — both happy
        # path (0) and context-pressure exit (42) must propagate.
        assert rc == wait_code
        # We actually waited on the child instead of unwinding past it.
        proc.wait.assert_called_once()
        # Warning surfaced on stderr with the pid file path for operator triage.
        err = capsys.readouterr().err
        assert "WARNING" in err and "pid file" in err
        assert str(tmp_path / ".squidsquad" / "skill" / ".claude-pid") in err
