"""Tests for references/scripts/reboot_agent.py.

After #4792 Phase 2 (CONTEXT-4792.md §5.3) this file shrunk to two helpers:
``_kill_process`` and ``_read_claude_pid``. The previous orchestrators
(``reboot``, ``_kill_and_respawn``, ``_read_current_state``, ``_spawn_wrapper``,
``_get_clone_path``, ``_read_pid_file``) were deleted — restart orchestration
moved to the harness intent state machine. These tests cover the surviving
helpers plus negative-guard tests that lock the removal.
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import reboot_agent  # noqa: E402


# ---------------------------------------------------------------------------
# _read_claude_pid (kept)
# ---------------------------------------------------------------------------


class TestReadClaudePid:
    def test_returns_pid_and_alive_for_running_process(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        own_pid = os.getpid()
        (squid / ".claude-pid").write_text(str(own_pid), encoding="utf-8")
        pid, alive = reboot_agent._read_claude_pid(tmp_path, "skill")
        assert pid == own_pid
        assert alive is True

    def test_missing_file_returns_none_false(self, tmp_path):
        pid, alive = reboot_agent._read_claude_pid(tmp_path, "skill")
        assert pid is None
        assert alive is False

    def test_invalid_content_returns_none_false(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        (squid / ".claude-pid").write_text("not-a-pid", encoding="utf-8")
        pid, alive = reboot_agent._read_claude_pid(tmp_path, "skill")
        assert pid is None
        assert alive is False

    def test_dead_pid_returns_pid_and_alive_false(self, tmp_path):
        squid = tmp_path / ".squidsquad" / "skill"
        squid.mkdir(parents=True)
        # A PID we are very unlikely to actually own
        (squid / ".claude-pid").write_text("99999999", encoding="utf-8")
        pid, alive = reboot_agent._read_claude_pid(tmp_path, "skill")
        assert pid == 99999999
        assert alive is False


# ---------------------------------------------------------------------------
# _kill_process (kept; cross-platform)
# ---------------------------------------------------------------------------


class TestKillProcess:
    @pytest.mark.skipif(sys.platform != "win32",
                        reason="Windows-only — taskkill /F path")
    def test_kill_windows_uses_taskkill_force(self):
        with patch("reboot_agent.subprocess.run") as run:
            reboot_agent._kill_process(12345)
        run.assert_called_once()
        cmd = run.call_args[0][0]
        assert cmd[:2] == ["taskkill", "/F"], (
            "Windows kill must use taskkill /F for uninterruptible termination"
        )
        assert "12345" in cmd

    @pytest.mark.skipif(sys.platform == "win32",
                        reason="POSIX-only — SIGKILL path")
    def test_kill_posix_uses_sigkill(self):
        """SIGKILL is the only signal POSIX guarantees cannot be caught or
        ignored — required to match Windows taskkill /F semantics in force
        contexts (CONTEXT-4792.md §3.3 Q7)."""
        import signal
        with patch("reboot_agent.os.kill") as kill:
            reboot_agent._kill_process(12345)
        kill.assert_called_once_with(12345, signal.SIGKILL)

    @pytest.mark.skipif(sys.platform == "win32",
                        reason="POSIX-only — ProcessLookupError path")
    def test_kill_already_dead_pid_swallows_process_lookup_error(self):
        """POSIX: killing a non-existent PID raises ProcessLookupError; the
        helper must swallow it so callers don't crash on already-dead PIDs."""
        with patch("reboot_agent.os.kill", side_effect=ProcessLookupError()):
            # Must not raise
            reboot_agent._kill_process(12345)

    @pytest.mark.skipif(sys.platform == "win32",
                        reason="POSIX-only — PermissionError path")
    def test_kill_permission_error_swallowed(self):
        """POSIX: a process owned by another UID raises PermissionError on
        SIGKILL. The force-kill safety net runs inside update_health, which
        must NOT crash the harness on a permission denial — the next poll
        will re-evaluate."""
        with patch("reboot_agent.os.kill", side_effect=PermissionError()):
            reboot_agent._kill_process(12345)  # must not raise


class TestKillProcessPidValidation10530:
    """#10530: _kill_process must reject None / non-int / <= 0 PIDs before
    calling os.kill or taskkill. ``os.kill(0, SIGKILL)`` would send to the
    whole process group (incl. the harness itself); ``os.kill(-1, SIGKILL)``
    would sweep every process the calling user can signal.
    """

    @pytest.mark.parametrize("bad_pid", [None, 0, -1, -12345, True, False])
    def test_invalid_pid_does_not_call_kill_posix(self, bad_pid):
        if sys.platform == "win32":
            with patch("reboot_agent.subprocess.run") as run:
                reboot_agent._kill_process(bad_pid)
            run.assert_not_called()
        else:
            with patch("reboot_agent.os.kill") as kill:
                reboot_agent._kill_process(bad_pid)
            kill.assert_not_called()

    @pytest.mark.parametrize("bad_pid", ["1234", "not-a-pid", 1.5, [12345], object()])
    def test_non_int_pid_does_not_call_kill(self, bad_pid):
        if sys.platform == "win32":
            with patch("reboot_agent.subprocess.run") as run:
                reboot_agent._kill_process(bad_pid)
            run.assert_not_called()
        else:
            with patch("reboot_agent.os.kill") as kill:
                reboot_agent._kill_process(bad_pid)
            kill.assert_not_called()

    @pytest.mark.skipif(sys.platform == "win32",
                        reason="POSIX-only — TypeError path on os.kill")
    def test_kill_type_error_swallowed(self):
        """If a bad-type PID slips past the guard (e.g. a Mock object),
        os.kill raises TypeError. Mirror the ProcessLookupError /
        PermissionError swallow behavior so the harness doesn't crash."""
        with patch("reboot_agent.os.kill", side_effect=TypeError("bad pid")):
            # Pass a valid-shape int so the guard doesn't catch it before
            # the stub gets to raise.
            reboot_agent._kill_process(12345)  # must not raise

    @pytest.mark.skipif(sys.platform != "win32",
                        reason="Windows-only — taskkill subprocess path")
    def test_kill_windows_missing_taskkill_swallowed(self):
        """If taskkill is absent (Windows Server Core, broken PATH),
        subprocess.run raises FileNotFoundError before `check=False` can
        do anything. The helper must swallow it — same best-effort
        posture as the POSIX branch."""
        with patch("reboot_agent.subprocess.run",
                   side_effect=FileNotFoundError("taskkill not found")):
            reboot_agent._kill_process(12345)  # must not raise


# ---------------------------------------------------------------------------
# Negative guards — removed orchestrators
# ---------------------------------------------------------------------------


class TestRemovedHelpers:
    """#4792 Phase 2 (CONTEXT-4792.md §5.3): the following symbols were
    deleted. Restart orchestration moved to the harness intent state
    machine + the 60s force-kill safety net in update_health. These tests
    lock the removal so a future refactor can't silently reintroduce a
    parallel restart path."""

    @pytest.mark.parametrize("name", [
        "reboot",
        "_kill_and_respawn",
        "_read_current_state",
        "_spawn_wrapper",
        "_get_clone_path",
        "_read_pid_file",
    ])
    def test_symbol_removed(self, name):
        assert not hasattr(reboot_agent, name), (
            f"reboot_agent.{name} must stay removed per CONTEXT-4792.md §5.3"
        )

    def test_source_has_no_legacy_sentinel_reads(self):
        """Source-grep across all literal-quote forms (`'.pid'`, `\".pid\"`,
        and the path-join form `/ \".pid\"`) so a reintroduction in any
        quoting style fails the guard. `.claude-pid` is the only `pid`-bearing
        literal allowed."""
        import re
        src = Path(reboot_agent.__file__).read_text(encoding="utf-8")
        # Replace `.claude-pid` so the search for bare `.pid` doesn't
        # false-positive on the allowed filename.
        scrubbed = src.replace(".claude-pid", "")
        for name in (".pid", ".stop", ".health", ".restart"):
            # Catch any literal occurrence regardless of quoting style.
            for quote in ("'", '"'):
                token = f"{quote}{name}{quote}"
                assert token not in scrubbed, (
                    f"reboot_agent must not reference legacy `{name}` "
                    f"(found {token!r}); CONTEXT-4792.md §5.3"
                )


# ---------------------------------------------------------------------------
# main() — deprecated CLI surface (Phase 2 retains a deprecation pointer;
# Phase 3 removes the CLI entirely)
# ---------------------------------------------------------------------------


class TestMainDeprecationStub:
    def test_main_returns_exit_code_two(self, capsys):
        rc = reboot_agent.main()
        assert rc == 2
        err = capsys.readouterr().err
        assert "DEPRECATED" in err
        assert "/agents/" in err  # mentions the harness API replacement
