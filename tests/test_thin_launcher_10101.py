"""Tests for #10101 — thin_launcher records actual claude.exe PID, not wrapper.

Background: ``shutil.which("claude")`` on Windows-via-npm returns
``claude.CMD`` (a cmd shim). ``subprocess.Popen`` invokes cmd.exe which
runs the shim and spawns the actual ``claude.exe``. The Popen child PID
is the cmd.exe wrapper, not claude.exe. The wrapper exits in seconds;
claude.exe outlives it by hours. Recording the wrapper PID makes
singleton check fail forever after the wrapper dies.

These tests exercise ``_resolve_claude_exe_pid`` in isolation with
injected fakes — no real subprocess, no real filesystem.
"""

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "references" / "scripts"))

import thin_launcher  # noqa: E402


def _stub_clock(start=0.0):
    """Return (now_fn, sleep_fn) that share a virtual clock."""
    state = {"t": start}

    def now_fn():
        return state["t"]

    def sleep_fn(secs):
        state["t"] += secs

    return now_fn, sleep_fn


class TestResolveClaudeExePidFastPath:
    """When claude_exe_used is a real .exe, no resolution is needed."""

    def test_returns_wrapper_pid_for_direct_exe_path(self):
        """If shutil.which returned a .exe, that IS the claude PID."""
        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=12345,
            claude_exe_used="/usr/bin/claude.exe",
            _list_children=lambda p: pytest.fail("should not walk tree"),
        )
        assert pid == 12345

    def test_returns_wrapper_pid_for_unix_no_extension(self):
        """POSIX claude binary has no extension — also the fast path."""
        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=12345,
            claude_exe_used="/usr/local/bin/claude",
            _list_children=lambda p: pytest.fail("should not walk tree"),
        )
        assert pid == 12345

    def test_returns_wrapper_pid_when_claude_exe_used_is_none(self):
        """Defensive — None path treated as non-shim."""
        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=99,
            claude_exe_used=None,
            _list_children=lambda p: pytest.fail("should not walk tree"),
        )
        assert pid == 99


class TestResolveClaudeExePidShimPath:
    """When claude_exe_used is a .cmd/.bat/.ps1, walk the descendant tree."""

    def test_finds_direct_child_claude_exe_immediately(self):
        """Wrapper has claude.exe as a direct child — return on first poll."""
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            if parent_pid == 1000:
                return [{"pid": 1001, "name": "claude.exe"}]
            return []

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=1000,
            claude_exe_used="C:\\Users\\foo\\AppData\\Roaming\\npm\\claude.CMD",
            _now=now_fn,
            _sleep=sleep_fn,
            _list_children=children_of,
        )
        assert pid == 1001

    def test_case_insensitive_shim_suffix(self):
        """`.cmd`, `.CMD`, and `.Cmd` all trigger the descendant walk."""
        now_fn, sleep_fn = _stub_clock()
        seen = {"called": False}

        def children_of(parent_pid):
            seen["called"] = True
            return [{"pid": 2002, "name": "claude.exe"}]

        for suffix in (".cmd", ".CMD", ".Cmd"):
            seen["called"] = False
            pid = thin_launcher._resolve_claude_exe_pid(
                wrapper_pid=2001,
                claude_exe_used=f"/tmp/claude{suffix}",
                _now=now_fn, _sleep=sleep_fn,
                _list_children=children_of,
            )
            assert seen["called"], f"shim suffix {suffix} did not trigger walk"
            assert pid == 2002

    def test_finds_grandchild_claude_exe_via_bfs(self):
        """The descendant walker returns the full subtree of `parent_pid`.

        Production implementations (``_win32_list_descendants`` and
        ``_posix_list_descendants``) BFS internally and return all
        descendants in one call. The test stub mirrors that contract:
        for ``parent_pid=3000``, it returns BOTH the direct child node.exe
        AND the grandchild claude.exe in a single list.
        """
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            assert parent_pid == 3000  # resolver only ever asks about wrapper
            return [
                {"pid": 3001, "name": "node.exe"},
                {"pid": 3002, "name": "claude.exe"},
            ]

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=3000,
            claude_exe_used="/x/claude.CMD",
            _now=now_fn, _sleep=sleep_fn,
            _list_children=children_of,
        )
        assert pid == 3002

    def test_polls_until_claude_exe_appears(self):
        """First N polls return nothing; eventually claude.exe arrives."""
        calls = {"n": 0}
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            calls["n"] += 1
            if calls["n"] < 3:
                return []  # claude.exe not spawned yet
            return [{"pid": 4001, "name": "claude.exe"}]

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=4000,
            claude_exe_used="C:\\npm\\claude.CMD",
            _now=now_fn, _sleep=sleep_fn,
            _list_children=children_of,
        )
        assert pid == 4001
        assert calls["n"] == 3

    def test_falls_back_to_wrapper_pid_on_timeout(self, capsys):
        """When claude.exe never appears, return wrapper PID + warn."""
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            return [{"pid": 5001, "name": "cmd.exe"}]  # only cmd.exe, no claude.exe

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=5000,
            claude_exe_used="/x/claude.cmd",
            _now=now_fn, _sleep=sleep_fn,
            _list_children=children_of,
        )
        assert pid == 5000  # falls back to wrapper
        err = capsys.readouterr().err
        assert "could not resolve claude.exe descendant" in err
        assert "#10101" in err

    def test_ignores_non_claude_descendants(self):
        """Other children of wrapper (helpers, conhost) are not mistaken for claude.exe."""
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            return [
                {"pid": 6001, "name": "conhost.exe"},
                {"pid": 6002, "name": "claude.exe"},
                {"pid": 6003, "name": "node.exe"},
            ]

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=6000,
            claude_exe_used="/x/claude.CMD",
            _now=now_fn, _sleep=sleep_fn,
            _list_children=children_of,
        )
        assert pid == 6002  # picks claude.exe, not the siblings

    def test_list_children_exception_does_not_crash(self):
        """If the descendant walker raises, swallow and fall back gracefully."""
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            raise PermissionError("simulated")

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=7000,
            claude_exe_used="/x/claude.CMD",
            _now=now_fn, _sleep=sleep_fn,
            _list_children=children_of,
        )
        # Should fall back to wrapper after timeout, not raise.
        assert pid == 7000


class TestResolveClaudeExePidBatAndPs1:
    """Covers .bat and .ps1 shim variants alongside .cmd."""

    def test_bat_shim_triggers_walk(self):
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            return [{"pid": 8001, "name": "claude.exe"}]

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=8000,
            claude_exe_used="C:\\bin\\claude.bat",
            _now=now_fn, _sleep=sleep_fn,
            _list_children=children_of,
        )
        assert pid == 8001

    def test_ps1_shim_triggers_walk(self):
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            return [{"pid": 9001, "name": "claude.exe"}]

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=9000,
            claude_exe_used="C:\\bin\\claude.ps1",
            _now=now_fn, _sleep=sleep_fn,
            _list_children=children_of,
        )
        assert pid == 9001
