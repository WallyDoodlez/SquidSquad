"""Tests for references/scripts/process_utils.py (#8891)."""

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
        # 2**31 - 2 is well above any plausible PID; tasklist / os.kill
        # both report not-found.
        assert process_utils.is_process_alive(2_147_483_646) is False

    def test_oserror_returns_false(self):
        """Implementation defensively swallows OSError and returns False."""
        with patch("process_utils.platform.system", return_value="Linux"), \
             patch("process_utils.os.kill", side_effect=OSError("boom")):
            assert process_utils.is_process_alive(12345) is False

    def test_permission_error_returns_false(self):
        """PermissionError (process exists but not ours on some OSes) → False."""
        with patch("process_utils.platform.system", return_value="Linux"), \
             patch("process_utils.os.kill", side_effect=PermissionError):
            assert process_utils.is_process_alive(12345) is False

    def test_windows_branch_parses_tasklist(self):
        """Windows branch checks for the PID string in tasklist stdout."""
        fake_proc = MagicMock(stdout="some preamble PID:12345 more\n")
        with patch("process_utils.platform.system", return_value="Windows"), \
             patch("process_utils.subprocess.run", return_value=fake_proc) as run:
            assert process_utils.is_process_alive(12345) is True
            # Sanity-check we called tasklist with the right PID filter.
            args = run.call_args[0][0]
            assert args[0] == "tasklist"
            assert "PID eq 12345" in args

    def test_windows_branch_returns_false_when_pid_absent(self):
        fake_proc = MagicMock(stdout="INFO: No tasks matching\n")
        with patch("process_utils.platform.system", return_value="Windows"), \
             patch("process_utils.subprocess.run", return_value=fake_proc):
            assert process_utils.is_process_alive(99999999) is False


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
