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

    def test_windows_uses_openprocess_not_tasklist(self):
        """#9904: Windows path must use OpenProcess via ctypes, never
        shell out to tasklist (which takes 20+ s on some systems and
        wedges the harness)."""
        fake_kernel32 = MagicMock()
        fake_kernel32.OpenProcess.return_value = 12345  # nonzero handle
        # GetExitCodeProcess writes STILL_ACTIVE (259) via byref
        def get_exit(handle, exit_ptr):
            exit_ptr._obj.value = 259
            return 1
        fake_kernel32.GetExitCodeProcess.side_effect = get_exit
        fake_ctypes = MagicMock()
        fake_ctypes.windll.kernel32 = fake_kernel32
        fake_ctypes.c_ulong = __import__("ctypes").c_ulong
        fake_ctypes.byref = __import__("ctypes").byref
        with patch("process_utils.sys.platform", "win32"), \
             patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            assert process_utils.is_process_alive(12345) is True
            fake_kernel32.OpenProcess.assert_called_once()
            fake_kernel32.CloseHandle.assert_called_once()

    def test_windows_dead_process_returns_false(self):
        """OpenProcess succeeds but GetExitCodeProcess returns non-STILL_ACTIVE."""
        fake_kernel32 = MagicMock()
        fake_kernel32.OpenProcess.return_value = 12345
        def get_exit(handle, exit_ptr):
            exit_ptr._obj.value = 0  # process exited with 0
            return 1
        fake_kernel32.GetExitCodeProcess.side_effect = get_exit
        fake_ctypes = MagicMock()
        fake_ctypes.windll.kernel32 = fake_kernel32
        fake_ctypes.c_ulong = __import__("ctypes").c_ulong
        fake_ctypes.byref = __import__("ctypes").byref
        with patch("process_utils.sys.platform", "win32"), \
             patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            assert process_utils.is_process_alive(12345) is False
            fake_kernel32.CloseHandle.assert_called_once()

    def test_windows_openprocess_failure_returns_false(self):
        """OpenProcess returns 0 + ERROR_INVALID_PARAMETER → process unknown."""
        fake_kernel32 = MagicMock()
        fake_kernel32.OpenProcess.return_value = 0
        fake_kernel32.GetLastError.return_value = 87  # ERROR_INVALID_PARAMETER
        fake_ctypes = MagicMock()
        fake_ctypes.windll.kernel32 = fake_kernel32
        with patch("process_utils.sys.platform", "win32"), \
             patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            assert process_utils.is_process_alive(99999999) is False

    def test_windows_access_denied_means_alive(self):
        """ERROR_ACCESS_DENIED (5) means process exists, we just can't open it."""
        fake_kernel32 = MagicMock()
        fake_kernel32.OpenProcess.return_value = 0
        fake_kernel32.GetLastError.return_value = 5  # ERROR_ACCESS_DENIED
        fake_ctypes = MagicMock()
        fake_ctypes.windll.kernel32 = fake_kernel32
        with patch("process_utils.sys.platform", "win32"), \
             patch.dict(sys.modules, {"ctypes": fake_ctypes}):
            assert process_utils.is_process_alive(4) is True  # System PID

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
