"""Tests for references/scripts/process_utils.py (#8891, #9903, #9904)."""

import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import process_utils


class TestIsProcessAlive:
    """Cross-platform PID liveness — canonical implementation (#8891)."""

    def test_none_is_not_alive(self):
        assert process_utils.is_process_alive(None) is False

    def test_zero_is_not_alive(self):
        # os.kill(0, ...) targets the calling process group on POSIX —
        # we never want a 0 to be treated as "alive". Stay strict.
        assert process_utils.is_process_alive(0) is False

    def test_negative_is_not_alive(self):
        # Negative PIDs are process groups on POSIX; reject them.
        assert process_utils.is_process_alive(-1) is False
        assert process_utils.is_process_alive(-12345) is False

    def test_own_pid_is_alive(self):
        # The test runner's own PID is obviously alive.
        assert process_utils.is_process_alive(os.getpid()) is True

    def test_unlikely_pid_is_not_alive(self):
        # 2**31 - 2 is well above any plausible PID.
        assert process_utils.is_process_alive(2_147_483_646) is False

    def test_oserror_returns_false_on_posix(self):
        """POSIX branch swallows OSError from os.kill and returns False."""
        with patch("process_utils.sys.platform", "linux"), \
             patch("process_utils.os.kill", side_effect=OSError("boom")):
            assert process_utils.is_process_alive(12345) is False

    def test_permission_error_returns_false_on_posix(self):
        with patch("process_utils.sys.platform", "linux"), \
             patch("process_utils.os.kill", side_effect=PermissionError):
            assert process_utils.is_process_alive(12345) is False

    def test_posix_kill_signal_zero(self):
        """POSIX branch calls os.kill(pid, 0) and returns True on success."""
        with patch("process_utils.sys.platform", "linux"), \
             patch("process_utils.os.kill") as kill:
            assert process_utils.is_process_alive(12345) is True
            kill.assert_called_once_with(12345, 0)

    # ---- Win32 branch (#10440 reshape: monkey-patch _win32_kernel32 +
    # ctypes.get_last_error directly; the old sys.modules['ctypes'] patch
    # no longer works because ctypes is imported at module level). ----

    def _fake_kernel32_for_win_tests(self, monkeypatch):
        fake = MagicMock(name="kernel32")
        monkeypatch.setattr(process_utils, "_win32_kernel32", lambda: fake)
        monkeypatch.setattr(process_utils.sys, "platform", "win32")
        return fake

    def test_windows_uses_openprocess_not_tasklist(self, monkeypatch):
        """#9904: Windows path must use OpenProcess via ctypes, never
        shell out to tasklist (which takes 20+ s on some systems and
        wedges the harness)."""
        fake_kernel32 = self._fake_kernel32_for_win_tests(monkeypatch)
        fake_kernel32.OpenProcess.return_value = 12345  # nonzero handle

        def get_exit(handle, exit_ptr):
            exit_ptr._obj.value = 259
            return 1

        fake_kernel32.GetExitCodeProcess.side_effect = get_exit
        assert process_utils.is_process_alive(12345) is True
        fake_kernel32.OpenProcess.assert_called_once()
        fake_kernel32.CloseHandle.assert_called_once()

    def test_windows_dead_process_returns_false(self, monkeypatch):
        """OpenProcess succeeds but GetExitCodeProcess returns non-STILL_ACTIVE."""
        fake_kernel32 = self._fake_kernel32_for_win_tests(monkeypatch)
        fake_kernel32.OpenProcess.return_value = 12345

        def get_exit(handle, exit_ptr):
            exit_ptr._obj.value = 0  # process exited with 0
            return 1

        fake_kernel32.GetExitCodeProcess.side_effect = get_exit
        assert process_utils.is_process_alive(12345) is False
        fake_kernel32.CloseHandle.assert_called_once()

    def test_windows_openprocess_failure_invalid_param_returns_false(self, monkeypatch):
        """OpenProcess returns 0 + ERROR_INVALID_PARAMETER → process unknown.

        #10440: read via ctypes.get_last_error (use_last_error pattern),
        not kernel32.GetLastError — the per-thread last-error slot must
        be captured by ctypes immediately after the call.
        """
        fake_kernel32 = self._fake_kernel32_for_win_tests(monkeypatch)
        fake_kernel32.OpenProcess.return_value = 0
        monkeypatch.setattr(process_utils.ctypes, "get_last_error", lambda: 87)
        assert process_utils.is_process_alive(99999999) is False

    def test_windows_access_denied_means_alive(self, monkeypatch):
        """ERROR_ACCESS_DENIED (5) means process exists, we just can't open it."""
        fake_kernel32 = self._fake_kernel32_for_win_tests(monkeypatch)
        fake_kernel32.OpenProcess.return_value = 0
        monkeypatch.setattr(process_utils.ctypes, "get_last_error", lambda: 5)
        assert process_utils.is_process_alive(4) is True  # System PID

    def test_windows_get_exit_code_failure_treated_as_alive(self, monkeypatch):
        """If GetExitCodeProcess returns 0 (call failed) but OpenProcess
        succeeded, the process existed when we held the handle —
        conservative: still alive. Lock the existing semantics."""
        fake_kernel32 = self._fake_kernel32_for_win_tests(monkeypatch)
        fake_kernel32.OpenProcess.return_value = 1
        fake_kernel32.GetExitCodeProcess.return_value = 0
        assert process_utils.is_process_alive(1234) is True
        fake_kernel32.CloseHandle.assert_called_once()

    def test_windows_close_handle_runs_on_exception(self, monkeypatch):
        """try/finally MUST close the handle even when GetExitCodeProcess
        raises — otherwise every error path leaks a kernel handle."""
        fake_kernel32 = self._fake_kernel32_for_win_tests(monkeypatch)
        fake_kernel32.OpenProcess.return_value = 7
        fake_kernel32.GetExitCodeProcess.side_effect = RuntimeError("boom")
        import pytest as _pt
        with _pt.raises(RuntimeError):
            process_utils.is_process_alive(1234)
        fake_kernel32.CloseHandle.assert_called_once_with(7)


class TestWin32KernelBinding:
    """#10440: the typed kernel32 binding caches + sets explicit argtypes."""

    def test_cache_returns_same_object(self, monkeypatch):
        monkeypatch.setattr(process_utils, "_CACHED_KERNEL32", None)
        if process_utils.sys.platform != "win32":
            import pytest as _pt
            _pt.skip("WinDLL is Windows-only; cache test runs only on win32")
        first = process_utils._win32_kernel32()
        second = process_utils._win32_kernel32()
        assert first is second

    def test_argtypes_set_for_64bit_handle_correctness(self, monkeypatch):
        monkeypatch.setattr(process_utils, "_CACHED_KERNEL32", None)
        if process_utils.sys.platform != "win32":
            import pytest as _pt
            _pt.skip("WinDLL is Windows-only")
        from ctypes import wintypes
        k = process_utils._win32_kernel32()
        # restype on OpenProcess must be HANDLE (full pointer width)
        # instead of the ctypes default c_int (32-bit signed). That's
        # the ABI-correctness half of #10440.
        assert k.OpenProcess.restype is wintypes.HANDLE
        assert k.GetExitCodeProcess.restype is wintypes.BOOL
        assert k.CloseHandle.restype is wintypes.BOOL

    def test_no_platform_module_imported(self):
        """#9903 regression: platform.system() hangs on Python 3.12 Windows
        via the WMI path. process_utils must not import platform at all."""
        assert not hasattr(process_utils, "platform")

    def test_no_subprocess_in_module(self):
        """#9904 regression: must not shell out to tasklist (slow path)."""
        assert not hasattr(process_utils, "subprocess")


class TestModuleReexports:
    """Importers should be able to alias via `as _is_process_alive`."""

    def test_boot_remote_alias_points_at_process_utils(self):
        import boot_remote
        assert boot_remote._is_process_alive is process_utils.is_process_alive

    def test_health_check_alias_points_at_process_utils(self):
        import health_check
        assert health_check._is_process_alive is process_utils.is_process_alive

    def test_reboot_agent_alias_points_at_process_utils(self):
        import reboot_agent
        assert reboot_agent._is_process_alive is process_utils.is_process_alive
