"""Tests for references/scripts/boot_remote.py — PID-based agent boot detection."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import boot_remote


class TestRemovedLegacySentinelHelpers:
    """#4792 (CONTEXT-4792.md §5.2): legacy sentinel helpers deleted in
    Phase 2 of the sole-authority cleanup. Negative-guard tests that lock
    the removal so a future refactor can't silently bring them back."""

    def test_read_pid_file_removed(self):
        assert not hasattr(boot_remote, "_read_pid_file"), (
            "boot_remote._read_pid_file must stay removed — .claude-pid "
            "is the sole liveness signal per CONTEXT-4792.md §5.2"
        )

    def test_read_health_file_removed(self):
        assert not hasattr(boot_remote, "_read_health_file"), (
            "boot_remote._read_health_file must stay removed per "
            "CONTEXT-4792.md §5.2"
        )

    def test_clean_stale_restart_removed(self):
        assert not hasattr(boot_remote, "_clean_stale_restart"), (
            "boot_remote._clean_stale_restart must stay removed — restart "
            "intent lives in harness state per CONTEXT-4792.md §5.2"
        )

    def test_source_has_no_legacy_sentinel_reads(self):
        """Source-grep across all literal-quote forms (`'.pid'`, `\".pid\"`)
        so a reintroduction in any quoting style fails the guard.
        `.claude-pid` is the only `pid`-bearing literal allowed."""
        from pathlib import Path
        src = Path(boot_remote.__file__).read_text(encoding="utf-8")
        # Allow the `.claude-pid` literal which contains `.pid` as a
        # substring but is a different file.
        scrubbed = src.replace(".claude-pid", "")
        for name in (".pid", ".health", ".restart", ".stop"):
            for quote in ("'", '"'):
                token = f"{quote}{name}{quote}"
                assert token not in scrubbed, (
                    f"boot_remote must not reference legacy `{name}` "
                    f"(found {token!r}); CONTEXT-4792.md §5.2"
                )


class TestParseLocalConfigMandatory:
    """Tests for #3100 — .local-config is mandatory, no global fallback."""

    def test_valid_local_config_parses(self, tmp_path):
        """When .local-config exists with valid entries, parse them."""
        skill_path = tmp_path / "project" / "skill"
        config = tmp_path / ".local-config"
        config.write_text(f"- **skill**: {skill_path}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config):
            result = boot_remote._parse_local_config()

        assert result["skill"] == skill_path

    def test_missing_local_config_exits(self, tmp_path):
        """When .local-config is missing, exit with code 2 and clear error."""
        with patch.object(boot_remote, "LOCAL_CONFIG", tmp_path / "missing"):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_empty_local_config_exits(self, tmp_path):
        """When .local-config exists but has no valid entries, exit with code 2."""
        config = tmp_path / ".local-config"
        config.write_text("# comment only\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_no_global_clones_fallback(self, tmp_path):
        """Global ~/.squidsquad/clones/ is never used, even if it exists (#3100)."""
        global_clones = tmp_path / "fakehome" / ".squidsquad" / "clones"
        global_clones.mkdir(parents=True)
        (global_clones / "skill").write_text(f"{tmp_path / 'fallback'}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", tmp_path / "missing"):
            with pytest.raises(SystemExit) as exc_info:
                boot_remote._parse_local_config()
        assert exc_info.value.code == 2

    def test_cross_project_isolation(self, tmp_path):
        """Only .local-config entries are returned — no global leakage (#2750, #3100)."""
        projectA_skill = tmp_path / "projectA" / "skill"

        config = tmp_path / ".local-config"
        config.write_text(f"- **skill**: {projectA_skill}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config):
            result = boot_remote._parse_local_config()

        assert result["skill"] == projectA_skill
        assert "pm" not in result
        assert "dm" not in result

    def test_hyphenated_role_names(self, tmp_path):
        """#8561: Hyphenated role names like dev-ios must be parsed correctly."""
        config = tmp_path / ".local-config"
        config.write_text(
            "- **dev-ios**: ../project-dev-ios\n"
            "- **pm-skill**: ../project-pm-skill\n"
            "- **skill**: .\n"
        )
        with patch.object(boot_remote, "LOCAL_CONFIG", config), \
             patch.object(boot_remote, "REPO_ROOT", tmp_path):
            result = boot_remote._parse_local_config()
        assert "dev-ios" in result
        assert "pm-skill" in result
        assert "skill" in result


class TestGetClonePath:
    """Regression tests for _get_clone_path() JSON serialization (#5915)."""

    def test_returns_str_not_path(self, tmp_path):
        """_get_clone_path must return str so AgentState is JSON-serializable."""
        config = tmp_path / ".local-config"
        config.write_text(f"- **skill**: {tmp_path / 'skill-clone'}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config):
            result = boot_remote._get_clone_path("skill")

        assert isinstance(result, str), (
            f"_get_clone_path must return str, got {type(result).__name__}"
        )
        # Must be JSON-serializable (the original bug)
        import json
        json.dumps({"clone_path": result})  # Should not raise

    def test_fallback_returns_str(self, tmp_path):
        """Fallback to REPO_ROOT also returns str."""
        config = tmp_path / ".local-config"
        config.write_text(f"- **pm**: {tmp_path / 'pm-clone'}\n")

        with patch.object(boot_remote, "LOCAL_CONFIG", config):
            result = boot_remote._get_clone_path("skill")  # not in config

        assert isinstance(result, str)


class TestIsProcessAlive:
    def test_none_pid_is_not_alive(self):
        assert boot_remote._is_process_alive(None) is False

    def test_current_process_is_alive(self):
        assert boot_remote._is_process_alive(os.getpid()) is True

    def test_nonexistent_pid_is_not_alive(self):
        assert boot_remote._is_process_alive(99999999) is False


class TestNeedsBoot:
    @patch("boot_remote._get_clone_path")
    def test_stop_sentinel_no_longer_blocks_boot(self, mock_clone, tmp_path):
        """#4792: a stale `.stop` file in a clone no longer blocks boot.

        Lifecycle intent now lives in harness state, not on disk. The split
        brain caused by lingering `.stop` files (removing one in the primary
        repo not affecting clones) is the bug this issue closes.
        """
        mock_clone.return_value = tmp_path
        # Even with the file present, boot must NOT be blocked by it
        stop_file = tmp_path / ".squidsquad" / "skill" / ".stop"
        stop_file.parent.mkdir(parents=True)
        stop_file.write_text("legacy sentinel — should be ignored")
        needs, reason, _ = boot_remote._needs_boot("skill")
        # boot proceeds (no PID file present, so booting fresh)
        assert needs is True
        # And the reason should NOT mention `.stop`
        assert ".stop" not in reason

    def test_has_stop_sentinel_function_removed(self):
        """#4792: _has_stop_sentinel was removed from boot_remote."""
        assert not hasattr(boot_remote, "_has_stop_sentinel")

    @patch("boot_remote._get_clone_path")
    def test_no_pid_needs_boot(self, mock_clone, tmp_path):
        mock_clone.return_value = tmp_path
        (tmp_path / ".squidsquad" / "skill").mkdir(parents=True)
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "no PID" in reason or "not running" in reason

    @patch("boot_remote._is_process_alive", return_value=True)
    @patch("boot_remote._get_clone_path")
    def test_alive_process_skipped(self, mock_clone, mock_alive, tmp_path):
        """#4792 Phase 2: liveness is read from `.claude-pid` only."""
        mock_clone.return_value = tmp_path
        pid_file = tmp_path / ".squidsquad" / "skill" / ".claude-pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("12345")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "alive" in reason

    @patch("boot_remote._is_process_alive", return_value=False)
    @patch("boot_remote._get_clone_path")
    def test_dead_process_needs_boot(self, mock_clone, mock_alive, tmp_path):
        """#4792 Phase 2: dead `.claude-pid` triggers boot needed."""
        mock_clone.return_value = tmp_path
        pid_file = tmp_path / ".squidsquad" / "skill" / ".claude-pid"
        pid_file.parent.mkdir(parents=True)
        pid_file.write_text("99999")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        assert "dead" in reason


    @patch("boot_remote._get_clone_path")
    def test_corrupt_claude_pid_warns_stderr(self, mock_clone, tmp_path, capsys):
        """#8160 + #4792: corrupt .claude-pid must warn AND surface a
        distinct 'corrupt' reason rather than the misleading
        'no PID file found' message."""
        mock_clone.return_value = tmp_path
        pid_dir = tmp_path / ".squidsquad" / "skill"
        pid_dir.mkdir(parents=True)
        (pid_dir / ".claude-pid").write_text("not-a-number", encoding="utf-8")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is True
        captured = capsys.readouterr()
        assert "WARNING" in captured.err
        assert "corrupt" in captured.err or ".claude-pid" in captured.err
        # #4792 Phase 2 review iter-1 finding: reason must distinguish
        # corrupt from missing so operators see the file-exists-but-broken
        # state.
        assert "corrupt" in reason


class TestBootAgentSkip:
    @patch("boot_remote._needs_boot", return_value=(False, "alive (PID 123)", "/tmp"))
    def test_alive_agent_skipped(self, mock_needs):
        result = boot_remote.boot_agent("skill")
        assert result["action"] == "skip"
        assert result["success"] is True


# ---------------------------------------------------------------------------
# #3348 regression: heartbeat epoch parsing + UTF-16 PID file
# ---------------------------------------------------------------------------

# TestReadHealthFileHeartbeat, TestNeedsBootHeartbeat, and
# TestReadPidFileUtf16 were removed in #8979 Phase 2 (#4792 sole-authority
# cleanup) — `_read_health_file` and `_read_pid_file` no longer exist. The
# `TestRemovedLegacySentinelHelpers` class above locks the removal with
# negative-guard tests.


# ---------------------------------------------------------------------------
# #3347 regression: inter-process boot lock (.booting sentinel)
# ---------------------------------------------------------------------------

class TestBootingSentinel:
    def test_no_sentinel_returns_false(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        assert boot_remote._has_booting_sentinel(tmp_path, "skill") is False

    def test_recent_sentinel_returns_true(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".booting").write_text(str(os.getpid()), encoding="utf-8")
        assert boot_remote._has_booting_sentinel(tmp_path, "skill") is True

    def test_stale_sentinel_returns_false(self, tmp_path):
        """Sentinel older than TTL is treated as stale and cleaned up."""
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        booting = squid / ".booting"
        booting.write_text("99999", encoding="utf-8")
        # Backdate mtime
        old_time = time.time() - boot_remote.BOOTING_SENTINEL_TTL - 10
        os.utime(booting, (old_time, old_time))
        assert boot_remote._has_booting_sentinel(tmp_path, "skill") is False
        assert not booting.exists()  # Stale sentinel was cleaned up

    def test_write_sentinel_succeeds(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        assert boot_remote._write_booting_sentinel(tmp_path, "skill") is True
        assert (squid / ".booting").exists()

    def test_write_sentinel_blocked_by_existing(self, tmp_path):
        """Second write fails if recent sentinel exists."""
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".booting").write_text(str(os.getpid()), encoding="utf-8")
        assert boot_remote._write_booting_sentinel(tmp_path, "skill") is False

    def test_clear_sentinel(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".booting").write_text("123", encoding="utf-8")
        boot_remote._clear_booting_sentinel(tmp_path, "skill")
        assert not (squid / ".booting").exists()


class TestNeedsBootWithSentinel:
    @patch("boot_remote._get_clone_path")
    def test_booting_sentinel_prevents_boot(self, mock_clone, tmp_path):
        """Active .booting sentinel means boot already in progress — skip."""
        mock_clone.return_value = tmp_path
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".booting").write_text(str(os.getpid()), encoding="utf-8")
        needs, reason, _ = boot_remote._needs_boot("skill")
        assert needs is False
        assert "boot already in progress" in reason


class TestBootAgentLock:
    @patch("boot_remote._spawn_terminal", return_value=(True, "spawned", 12345))
    @patch("boot_remote._find_boot_script", return_value=(Path("/tmp/start.sh"), "sh"))
    @patch("boot_remote._needs_boot", return_value=(True, "dead", "/tmp/clone"))
    def test_writes_sentinel_before_spawn(self, mock_needs, mock_script, mock_spawn, tmp_path):
        """boot_agent writes .booting sentinel before spawning."""
        with patch("boot_remote._write_booting_sentinel", return_value=True) as mock_write, \
             patch("boot_remote._clear_booting_sentinel") as mock_clear:
            result = boot_remote.boot_agent("skill")
        assert result["action"] == "spawn"
        assert result["success"] is True
        mock_write.assert_called_once()
        mock_clear.assert_not_called()  # Cleared by wrapper, not boot_remote on success

    @patch("boot_remote._spawn_terminal", return_value=(False, "failed", None))
    @patch("boot_remote._find_boot_script", return_value=(Path("/tmp/start.sh"), "sh"))
    @patch("boot_remote._needs_boot", return_value=(True, "dead", "/tmp/clone"))
    def test_clears_sentinel_on_spawn_failure(self, mock_needs, mock_script, mock_spawn, tmp_path):
        """boot_agent clears .booting sentinel when spawn fails."""
        with patch("boot_remote._write_booting_sentinel", return_value=True) as mock_write, \
             patch("boot_remote._clear_booting_sentinel") as mock_clear:
            result = boot_remote.boot_agent("skill")
        assert result["success"] is False
        assert result.get("terminal_pid") is None
        mock_clear.assert_called_once()

    @patch("boot_remote._find_boot_script", return_value=(Path("/tmp/start.sh"), "sh"))
    @patch("boot_remote._needs_boot", return_value=(True, "dead", "/tmp/clone"))
    def test_skips_if_sentinel_blocked(self, mock_needs, mock_script):
        """boot_agent skips if another boot is in progress."""
        with patch("boot_remote._write_booting_sentinel", return_value=False):
            result = boot_remote.boot_agent("skill")
        assert result["action"] == "skip"
        assert "another boot in progress" in result["message"]


# #3349 stale .restart sentinel cleanup tests removed in #8979 Phase 2
# (#4792 sole-authority cleanup): `_clean_stale_restart` was deleted along
# with `boot_agent`'s call site. Restart intent now lives exclusively in
# harness state — no on-disk `.restart` sentinel exists for the wrapper
# to read or for boot to clean. The `TestRemovedLegacySentinelHelpers`
# class at the top of this file locks the removal.


class TestGetAllRoles:
    @patch("boot_remote._parse_dev_agents", return_value=["skill", "qa"])
    @patch("boot_remote._parse_local_config", return_value={"skill": Path("/tmp")})
    def test_includes_pm_from_config(self, mock_local, mock_devs, tmp_path):
        config = tmp_path / "config.md"
        config.write_text("- **PM**: always present\n- **DM**: present\n")
        squid_dir = tmp_path
        with patch.object(boot_remote, "SQUIDSQUAD_DIR", squid_dir), \
             patch.object(boot_remote, "CONFIG_MD", config):
            roles = boot_remote._get_all_roles()
            assert "pm" in roles
            assert "skill" in roles
            assert "qa" in roles
            assert "dm" in roles

    @patch("boot_remote._parse_dev_agents", return_value=["skill"])
    @patch("boot_remote._parse_local_config", return_value={"skill": Path("/tmp")})
    def test_mandatory_roles_always_present(self, mock_local, mock_devs):
        """Fixed team: PM + QA + DM always present regardless of config (#6261)."""
        roles = boot_remote._get_all_roles()
        assert "pm" in roles
        assert "qa" in roles
        assert "dm" in roles
        assert "skill" in roles


# ---------------------------------------------------------------------------
# #7286: _spawn_macos uses temp .sh file to avoid AppleScript quoting issues
# ---------------------------------------------------------------------------

class TestSpawnMacosTempFile:
    """Verify _spawn_macos writes a temp .sh file instead of inlining commands."""

    @patch("boot_remote.subprocess.Popen")
    @patch("boot_remote.os.chmod")
    def test_creates_temp_sh_file(self, mock_chmod, mock_popen, tmp_path):
        """_spawn_macos writes the shell command to a temp .sh file."""
        script = tmp_path / "thin_launcher.py"
        script.write_text("# placeholder")
        ok, msg, _pid = boot_remote._spawn_macos(tmp_path, "skill", script, "thin")
        assert ok is True
        assert "osascript" in msg

        # Popen should have been called with osascript
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert args[0] == "osascript"
        assert args[1] == "-e"

        # The AppleScript should reference a temp .sh file, not inline the path
        apple_script = args[2]
        assert "squidsquad-boot-" in apple_script
        assert ".sh" in apple_script

        # chmod should have been called with 0o700
        mock_chmod.assert_called_once()
        chmod_args = mock_chmod.call_args[0]
        assert chmod_args[1] == 0o700

    @patch("boot_remote.subprocess.Popen")
    @patch("boot_remote.os.chmod")
    def test_temp_file_contains_correct_command_thin(self, mock_chmod, mock_popen, tmp_path):
        """Temp .sh file contains cd + python command for thin launcher."""
        script = tmp_path / "thin_launcher.py"
        script.write_text("# placeholder")

        # Capture the temp file before it's cleaned up by intercepting Popen
        written_files = []
        original_named = tempfile.NamedTemporaryFile

        def capture_tempfile(*args, **kwargs):
            result = original_named(*args, **kwargs)
            written_files.append(result.name)
            return result

        with patch("boot_remote.tempfile.NamedTemporaryFile", side_effect=capture_tempfile):
            ok, _, _pid = boot_remote._spawn_macos(tmp_path, "skill", script, "thin")

        assert ok is True
        assert len(written_files) == 1
        content = Path(written_files[0]).read_text()
        assert "#!/bin/bash" in content
        assert "python" in content
        assert "skill" in content
        assert "rm -f" in content  # self-cleanup line

        # Clean up the temp file
        Path(written_files[0]).unlink(missing_ok=True)

    @patch("boot_remote.subprocess.Popen")
    @patch("boot_remote.os.chmod")
    def test_temp_file_contains_correct_command_legacy(self, mock_chmod, mock_popen, tmp_path):
        """Temp .sh file contains cd + bash command for legacy wrapper."""
        script = tmp_path / "start.sh"
        script.write_text("# placeholder")

        written_files = []
        original_named = tempfile.NamedTemporaryFile

        def capture_tempfile(*args, **kwargs):
            result = original_named(*args, **kwargs)
            written_files.append(result.name)
            return result

        with patch("boot_remote.tempfile.NamedTemporaryFile", side_effect=capture_tempfile):
            ok, _, _pid = boot_remote._spawn_macos(tmp_path, "skill", script, "legacy")

        assert ok is True
        content = Path(written_files[0]).read_text()
        assert "bash" in content
        assert "python" not in content or "thin" not in content

        Path(written_files[0]).unlink(missing_ok=True)

    @patch("boot_remote.subprocess.Popen")
    @patch("boot_remote.os.chmod")
    def test_special_chars_in_path_safe(self, mock_chmod, mock_popen, tmp_path):
        """Paths with single quotes and spaces are safely written to temp file."""
        # Double quotes are invalid in Windows paths, so test with single quotes
        # and spaces — these would still break AppleScript string interpolation.
        special_dir = tmp_path / "it's a test dir"
        special_dir.mkdir(parents=True)
        script = special_dir / "thin_launcher.py"
        script.write_text("# placeholder")

        written_files = []
        original_named = tempfile.NamedTemporaryFile

        def capture_tempfile(*args, **kwargs):
            result = original_named(*args, **kwargs)
            written_files.append(result.name)
            return result

        with patch("boot_remote.tempfile.NamedTemporaryFile", side_effect=capture_tempfile):
            ok, msg, _pid = boot_remote._spawn_macos(special_dir, "skill", script, "thin")

        assert ok is True

        # The AppleScript should NOT contain the special-char path directly —
        # it should only reference the safe temp file path
        apple_args = mock_popen.call_args[0][0]
        apple_script = apple_args[2]
        assert "it's" not in apple_script

        # The temp file contents should have the path (shell-quoted by shlex)
        content = Path(written_files[0]).read_text()
        # shlex.quote escapes single quotes, so check for the directory
        # name components that survive quoting
        assert "test dir" in content

        Path(written_files[0]).unlink(missing_ok=True)

    @pytest.mark.skipif(sys.platform == "win32",
                        reason="Double quotes invalid in Windows paths")
    @patch("boot_remote.subprocess.Popen")
    @patch("boot_remote.os.chmod")
    def test_double_quotes_in_path_safe(self, mock_chmod, mock_popen, tmp_path):
        """Paths with double quotes don't leak into AppleScript string."""
        special_dir = tmp_path / 'it"s a test'
        special_dir.mkdir(parents=True)
        script = special_dir / "thin_launcher.py"
        script.write_text("# placeholder")

        written_files = []
        original_named = tempfile.NamedTemporaryFile

        def capture_tempfile(*args, **kwargs):
            result = original_named(*args, **kwargs)
            written_files.append(result.name)
            return result

        with patch("boot_remote.tempfile.NamedTemporaryFile", side_effect=capture_tempfile):
            ok, msg, _pid = boot_remote._spawn_macos(special_dir, "skill", script, "thin")

        assert ok is True

        # AppleScript must not contain the double quote from the path
        apple_args = mock_popen.call_args[0][0]
        apple_script = apple_args[2]
        # The only double quotes should be AppleScript string delimiters
        # and the safe temp file path
        assert 'it"s' not in apple_script

        Path(written_files[0]).unlink(missing_ok=True)

    def test_spawn_failure_returns_false(self, tmp_path):
        """When subprocess.Popen raises, _spawn_macos returns (False, error)."""
        script = tmp_path / "thin_launcher.py"
        script.write_text("# placeholder")

        with patch("boot_remote.subprocess.Popen", side_effect=OSError("no osascript")):
            ok, msg, _pid = boot_remote._spawn_macos(tmp_path, "skill", script, "thin")

        assert ok is False
        assert "macOS spawn failed" in msg
