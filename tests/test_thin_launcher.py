"""Tests for references/scripts/thin_launcher.py (#4966)."""

import json
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
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            thin_launcher.main()

        assert "--strict-mcp-config" in captured_cmd
        # #11512: spawn prompt is the mode-neutral boot trigger (last positional),
        # NOT a /loop command — mode selection belongs to boot Step 1.
        prompt = captured_cmd[-1]
        assert prompt == thin_launcher._SPAWN_PROMPT
        assert not prompt.startswith("/loop "), (
            f"spawn prompt must not force loop mode; got {prompt!r}"
        )
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
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            thin_launcher.main()

        idx = captured_cmd.index("--append-system-prompt")
        assert captured_cmd[idx + 1] == "SQUIDSQUAD_ROLE=skill"


class TestSpawnPromptIsModeNeutral:
    """#11512: spawn prompt is a mode-neutral boot trigger, NOT a /loop command.

    Mode selection (event vs polling) belongs to composed CLAUDE.md boot
    Step 1 (step:cycle/boot). The launcher must not preempt that probe by
    forcing a /loop registration on the first turn (the pre-#11512 #9725
    behavior), or event mode is never reached when the harness is up.
    """

    @staticmethod
    def _spawn_cmd(tmp_path, role="skill"):
        sqdir = tmp_path / ".squidsquad" / role
        sqdir.mkdir(parents=True)
        captured_cmd = []

        def mock_popen(cmd, **kwargs):
            captured_cmd.extend(cmd)
            proc = MagicMock(); proc.pid = 99999; proc.wait.return_value = 0
            return proc

        with patch("thin_launcher.subprocess.Popen", side_effect=mock_popen), \
             patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("sys.argv", ["thin_launcher.py", role]):
            thin_launcher.main()
        return captured_cmd

    def test_prompt_is_the_neutral_boot_trigger(self, tmp_path):
        """Final positional arg is exactly _SPAWN_PROMPT."""
        cmd = self._spawn_cmd(tmp_path)
        assert cmd[-1] == thin_launcher._SPAWN_PROMPT

    def test_prompt_does_not_force_loop_mode(self, tmp_path):
        """No argument in the spawned command is a /loop directive."""
        cmd = self._spawn_cmd(tmp_path)
        assert not any(isinstance(a, str) and a.startswith("/loop") for a in cmd), (
            f"spawn command must not contain a /loop directive; got {cmd!r}"
        )

    def test_prompt_defers_mode_to_boot_step_1(self, tmp_path):
        """The neutral prompt directs the agent to the probe-then-decide boot step."""
        cmd = self._spawn_cmd(tmp_path)
        prompt = cmd[-1].lower()
        assert "step 1" in prompt or "step:cycle/boot" in prompt
        assert "probe" in prompt

    def test_legacy_boot_prompt_absent(self, tmp_path):
        """The pre-#9725 'Boot. Begin your first Ralph Loop cycle now.' prompt is gone."""
        cmd = self._spawn_cmd(tmp_path)
        assert "Boot. Begin your first Ralph Loop cycle now." not in cmd

    def test_no_interval_helper_remains(self):
        """#11512: _get_interval was removed with the /loop spawn prompt."""
        assert not hasattr(thin_launcher, "_get_interval")


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


class TestWin32KernelBinding10440:
    """#10440: typed kernel32 binding with use_last_error + explicit argtypes."""

    def test_win32_branch_uses_get_last_error_not_kernel32_getlasterror(self, monkeypatch):
        # When OpenProcess returns 0, the failure-branch read MUST go
        # through ``ctypes.get_last_error`` (per-thread, captured by
        # ctypes immediately) not ``kernel32.GetLastError`` (racy).
        fake_kernel32 = MagicMock(name="kernel32")
        fake_kernel32.OpenProcess.return_value = 0
        # If the code ever reaches back into kernel32.GetLastError() we'd
        # see this AttributeError-like miss; configure to raise loudly.
        fake_kernel32.GetLastError.side_effect = AssertionError(
            "GetLastError must NOT be read off the WinDLL — use ctypes.get_last_error"
        )
        monkeypatch.setattr(thin_launcher, "_win32_kernel32", lambda: fake_kernel32)
        monkeypatch.setattr(thin_launcher.sys, "platform", "win32")
        # Stage 1: ACCESS_DENIED → alive
        import ctypes as _c
        monkeypatch.setattr(_c, "get_last_error", lambda: 5)
        assert thin_launcher._is_process_alive(1234) is True
        # Stage 2: INVALID_PARAMETER → dead
        monkeypatch.setattr(_c, "get_last_error", lambda: 87)
        assert thin_launcher._is_process_alive(1234) is False

    @pytest.mark.skipif(sys.platform != "win32", reason="WinDLL is Windows-only")
    def test_typed_binding_includes_toolhelp32(self, monkeypatch):
        # DS finding 1 follow-up: _win32_list_descendants used to read
        # ctypes.windll.kernel32 directly, leaving CreateToolhelp32Snapshot
        # / Process32First / Process32Next without argtypes — HANDLE
        # truncation to c_int + INVALID_HANDLE_VALUE comparison broken.
        monkeypatch.setattr(thin_launcher, "_CACHED_KERNEL32", None)
        from ctypes import wintypes
        k = thin_launcher._win32_kernel32()
        assert k.CreateToolhelp32Snapshot.restype is wintypes.HANDLE
        assert k.Process32First.restype is wintypes.BOOL
        assert k.Process32Next.restype is wintypes.BOOL


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

    def test_alive_claude_pid_returns_pid(self, tmp_path):
        d = tmp_path / ".squidsquad" / "skill"
        d.mkdir(parents=True)
        (d / ".claude-pid").write_text("12345", encoding="utf-8")
        # #12294: held only when the live PID is image-verified as claude.
        with patch("thin_launcher._is_claude_process_alive", return_value=True):
            assert thin_launcher._check_singleton(str(tmp_path), "skill") == 12345

    def test_recycled_nonclaude_pid_returns_none(self, tmp_path):
        """#12294 AC3: a live PID recycled by a non-claude process is stale —
        image verification stops it from defeating singleton enforcement."""
        d = tmp_path / ".squidsquad" / "skill"
        d.mkdir(parents=True)
        (d / ".claude-pid").write_text("12345", encoding="utf-8")
        with patch("thin_launcher._is_process_alive", return_value=True), \
             patch("thin_launcher._image_name_for_pid", return_value="explorer.exe"):
            assert thin_launcher._check_singleton(str(tmp_path), "skill") is None

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
             patch("thin_launcher._is_claude_process_alive", return_value=True), \
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


class TestStaleScheduledLockReclaim:
    """#11641: before launch, thin_launcher clears a stale claude-code
    scheduler lock (.claude/scheduled_tasks.lock with a DEAD holder PID) so a
    crashed-startup loop can't persist — but never stomps a LIVE-held lock."""

    def _write_lock(self, clone_path, pid):
        lock = Path(clone_path) / ".claude" / "scheduled_tasks.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        # Mirror the real claude-code lock shape (see #11641 repro backup).
        body = {"sessionId": "abc", "pid": pid,
                "procStart": "639168942179987460", "acquiredAt": 1781312891613}
        lock.write_text(json.dumps(body), encoding="utf-8")
        return lock

    def test_dead_holder_lock_reclaimed(self, tmp_path, capsys):
        """Dead holder PID -> lock removed, reclamation logged."""
        lock = self._write_lock(tmp_path, 25628)
        with patch("thin_launcher._is_process_alive", return_value=False):
            reclaimed = thin_launcher._reclaim_stale_scheduled_lock(str(tmp_path))
        assert reclaimed is True
        assert not lock.exists()
        assert "reclaimed stale scheduled-tasks lock" in capsys.readouterr().out

    def test_live_holder_lock_preserved(self, tmp_path):
        """Live holder PID -> lock left untouched (never stomp a live lock)."""
        lock = self._write_lock(tmp_path, 4242)
        with patch("thin_launcher._is_process_alive", return_value=True):
            reclaimed = thin_launcher._reclaim_stale_scheduled_lock(str(tmp_path))
        assert reclaimed is False
        assert lock.exists()

    def test_no_lock_is_noop(self, tmp_path):
        """No lock file (no .claude dir) -> no error, nothing reclaimed."""
        assert thin_launcher._reclaim_stale_scheduled_lock(str(tmp_path)) is False

    def test_unparseable_lock_preserved(self, tmp_path, capsys):
        """Corrupt lock (no readable pid) -> conservative: leave it + warn.
        We cannot prove the holder dead, and the proven #11641 failure mode is
        a dead-but-parseable PID; clearing risks stomping a live holder."""
        lock = Path(tmp_path) / ".claude" / "scheduled_tasks.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text("}{ not json", encoding="utf-8")
        with patch("thin_launcher._is_process_alive", return_value=False):
            reclaimed = thin_launcher._reclaim_stale_scheduled_lock(str(tmp_path))
        assert reclaimed is False
        assert lock.exists()
        assert "WARNING" in capsys.readouterr().err

    def test_missing_pid_field_preserved(self, tmp_path):
        """Valid JSON but no `pid` key -> cannot prove dead -> leave it."""
        lock = Path(tmp_path) / ".claude" / "scheduled_tasks.lock"
        lock.parent.mkdir(parents=True)
        lock.write_text(json.dumps({"sessionId": "abc"}), encoding="utf-8")
        assert thin_launcher._reclaim_stale_scheduled_lock(str(tmp_path)) is False
        assert lock.exists()

    def test_main_launch_path_invokes_reclaim(self, tmp_path):
        """Wiring: the spawn path actually calls the reclaimer before Popen —
        the fix is worthless if it ships unwired (#11641 names the spawn path
        as the runtime actor)."""
        (tmp_path / ".squidsquad" / "skill").mkdir(parents=True)
        proc = MagicMock()
        proc.pid = 11111
        proc.wait.return_value = 0
        with patch("thin_launcher.os.getcwd", return_value=str(tmp_path)), \
             patch("thin_launcher.subprocess.Popen", return_value=proc), \
             patch("thin_launcher._get_effort_level", return_value="high"), \
             patch("thin_launcher._resolve_claude_exe_pid", return_value=11111), \
             patch("thin_launcher.shutil.which", return_value="/usr/bin/claude"), \
             patch("thin_launcher._reclaim_stale_scheduled_lock") as mock_reclaim, \
             patch("sys.argv", ["thin_launcher.py", "skill"]):
            rc = thin_launcher.main()
        assert rc == 0
        mock_reclaim.assert_called_once_with(str(tmp_path))


class TestImageNameForPid12294:
    """#12294: thin_launcher's local mirror of process_utils.image_name_for_pid."""

    def test_none_and_nonpositive(self):
        assert thin_launcher._image_name_for_pid(None) is None
        assert thin_launcher._image_name_for_pid(0) is None
        assert thin_launcher._image_name_for_pid(-2) is None

    def test_win32_uses_all_procs_lowercased(self, monkeypatch):
        monkeypatch.setattr(thin_launcher.sys, "platform", "win32")
        monkeypatch.setattr(
            thin_launcher, "_win32_all_procs",
            lambda: {4242: (10, "Claude.exe"), 99: (10, "node.exe")},
        )
        assert thin_launcher._image_name_for_pid(4242) == "claude.exe"

    def test_win32_not_found_is_none(self, monkeypatch):
        """Undetermined image (PID absent from snapshot) — caller falls back."""
        monkeypatch.setattr(thin_launcher.sys, "platform", "win32")
        monkeypatch.setattr(
            thin_launcher, "_win32_all_procs", lambda: {99: (10, "node.exe")},
        )
        assert thin_launcher._image_name_for_pid(4242) is None

    def test_posix_reads_proc_comm(self, monkeypatch):
        monkeypatch.setattr(thin_launcher.sys, "platform", "linux")
        fake = MagicMock(name="proc-comm")
        fake.read_text.return_value = "Claude\n"
        monkeypatch.setattr(thin_launcher, "Path", lambda *a, **k: fake)
        assert thin_launcher._image_name_for_pid(4242) == "claude"

    def test_posix_oserror_is_none(self, monkeypatch):
        monkeypatch.setattr(thin_launcher.sys, "platform", "linux")
        fake = MagicMock(name="proc-comm")
        fake.read_text.side_effect = OSError("no /proc")
        monkeypatch.setattr(thin_launcher, "Path", lambda *a, **k: fake)
        assert thin_launcher._image_name_for_pid(4242) is None


class TestIsClaudeProcessAlive12294:
    """#12294: thin_launcher's local image-verified liveness mirror."""

    def test_dead_is_false(self, monkeypatch):
        monkeypatch.setattr(thin_launcher, "_is_process_alive", lambda pid: False)
        assert thin_launcher._is_claude_process_alive(123) is False

    def test_alive_claude_is_true(self, monkeypatch):
        monkeypatch.setattr(thin_launcher, "_is_process_alive", lambda pid: True)
        monkeypatch.setattr(thin_launcher, "_image_name_for_pid", lambda pid: "claude.exe")
        assert thin_launcher._is_claude_process_alive(123) is True

    def test_alive_nonclaude_is_false(self, monkeypatch):
        monkeypatch.setattr(thin_launcher, "_is_process_alive", lambda pid: True)
        monkeypatch.setattr(thin_launcher, "_image_name_for_pid", lambda pid: "explorer.exe")
        assert thin_launcher._is_claude_process_alive(123) is False

    def test_alive_undetermined_falls_back_to_liveness(self, monkeypatch):
        monkeypatch.setattr(thin_launcher, "_is_process_alive", lambda pid: True)
        monkeypatch.setattr(thin_launcher, "_image_name_for_pid", lambda pid: None)
        assert thin_launcher._is_claude_process_alive(123) is True


class TestWin32AllProcs12294:
    """#12294: _win32_all_procs feeds both descendant walk and image lookup."""

    @pytest.mark.skipif(sys.platform != "win32", reason="toolhelp32 is Windows-only")
    def test_returns_self_and_known_processes(self):
        procs = thin_launcher._win32_all_procs()
        assert isinstance(procs, dict)
        assert procs, "snapshot should never be empty on a live Windows host"
        # our own PID must be present, mapped to (ppid, image_name)
        assert os.getpid() in procs
        ppid, name = procs[os.getpid()]
        assert isinstance(ppid, int)
        assert name.lower().startswith("python")

    @pytest.mark.skipif(sys.platform != "win32", reason="toolhelp32 is Windows-only")
    def test_descendants_still_work_after_refactor(self):
        # _win32_list_descendants now delegates to _win32_all_procs; smoke-test
        # it still returns a list without error for our own PID.
        out = thin_launcher._win32_list_descendants(os.getpid())
        assert isinstance(out, list)
