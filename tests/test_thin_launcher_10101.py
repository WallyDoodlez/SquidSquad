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
    """Fast path: no descendant walk needed.

    Triggered when:
    - claude_exe_used is None (defensive — caller didn't tell us), or
    - on non-Windows AND the executable ends in .exe / extensionless.

    Windows always walks regardless of extension (DS 10101 F4) to
    eliminate the .cmd/.bat/.ps1 allowlist fragility.
    """

    def test_returns_wrapper_pid_when_claude_exe_used_is_none(self):
        """None path takes the fast path on every platform."""
        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=99,
            claude_exe_used=None,
            _list_children=lambda p: pytest.fail("should not walk tree"),
        )
        assert pid == 99

    def test_unix_exe_path_skips_walk(self, monkeypatch):
        """POSIX + .exe → fast path. Mock sys.platform to make the
        test deterministic on any host."""
        monkeypatch.setattr(thin_launcher.sys, "platform", "linux")
        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=12345,
            claude_exe_used="/usr/bin/claude.exe",
            _list_children=lambda p: pytest.fail("should not walk tree"),
        )
        assert pid == 12345

    def test_unix_extensionless_skips_walk(self, monkeypatch):
        """POSIX + extensionless claude binary → fast path."""
        monkeypatch.setattr(thin_launcher.sys, "platform", "linux")
        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=12345,
            claude_exe_used="/usr/local/bin/claude",
            _list_children=lambda p: pytest.fail("should not walk tree"),
        )
        assert pid == 12345


class TestResolveClaudeExePidWindowsAlwaysWalks:
    """DS 10101 F4: on Windows, walk the descendant tree regardless of
    the resolved executable extension. Eliminates the .cmd/.bat/.ps1
    allowlist fragility — a future npm shim with a different extension
    (e.g. .vbs, .com) won't silently re-introduce the stale-wrapper bug.
    """

    def test_windows_walks_even_for_exe(self, monkeypatch):
        """Windows + .exe → walks anyway, in case Popen's child PID
        is still wrapped (cmd /c invocation, AV interposition, etc.)."""
        monkeypatch.setattr(thin_launcher.sys, "platform", "win32")
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            return [{"pid": 8765, "name": "claude.exe"}]

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=8764,
            claude_exe_used="C:\\bin\\claude.exe",
            _now=now_fn, _sleep=sleep_fn,
            _list_children=children_of,
        )
        assert pid == 8765

    def test_windows_walks_for_unknown_extension(self, monkeypatch):
        """Windows + .vbs (hypothetical future shim) → walks anyway."""
        monkeypatch.setattr(thin_launcher.sys, "platform", "win32")
        now_fn, sleep_fn = _stub_clock()

        def children_of(parent_pid):
            return [{"pid": 9999, "name": "claude.exe"}]

        pid = thin_launcher._resolve_claude_exe_pid(
            wrapper_pid=9998,
            claude_exe_used="C:\\bin\\claude.vbs",
            _now=now_fn, _sleep=sleep_fn,
            _list_children=children_of,
        )
        assert pid == 9999


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


class TestRealDescendantWalkersSmoke:
    """DS 10101 F2: smoke tests for the platform-specific walkers.

    The resolver tests above inject `_list_children` stubs, so the real
    `_win32_list_descendants` / `_posix_list_descendants` walkers aren't
    exercised. These smoke tests call them with the running process's
    PID and validate shape — proof the walker can read the live process
    table on this OS without crashing.
    """

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only walker")
    def test_win32_walker_returns_list_of_dicts_with_expected_keys(self):
        import os
        result = thin_launcher._win32_list_descendants(os.getpid())
        assert isinstance(result, list)
        # The test process may or may not have child processes — what we
        # validate is that whatever it returns, each entry has the right
        # shape: {"pid": int, "name": str}.
        for entry in result:
            assert isinstance(entry, dict)
            assert "pid" in entry and isinstance(entry["pid"], int)
            assert "name" in entry and isinstance(entry["name"], str)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only walker")
    def test_win32_walker_does_not_include_parent_pid(self):
        """Walker returns descendants, not the parent itself."""
        import os
        my_pid = os.getpid()
        result = thin_launcher._win32_list_descendants(my_pid)
        assert all(entry["pid"] != my_pid for entry in result)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-only walker")
    def test_win32_walker_returns_empty_for_nonexistent_pid(self):
        """Walker handles a PID that doesn't exist (using a very large value
        that's extremely unlikely to be a real PID)."""
        result = thin_launcher._win32_list_descendants(2**31 - 1)
        assert result == []

    @pytest.mark.skipif(not Path("/proc").is_dir(), reason="POSIX /proc walker")
    def test_posix_walker_returns_list_of_dicts_with_expected_keys(self):
        import os
        result = thin_launcher._posix_list_descendants(os.getpid())
        assert isinstance(result, list)
        for entry in result:
            assert isinstance(entry, dict)
            assert "pid" in entry and isinstance(entry["pid"], int)
            assert "name" in entry and isinstance(entry["name"], str)

    @pytest.mark.skipif(not Path("/proc").is_dir(), reason="POSIX /proc walker")
    def test_posix_walker_does_not_include_parent_pid(self):
        import os
        my_pid = os.getpid()
        result = thin_launcher._posix_list_descendants(my_pid)
        assert all(entry["pid"] != my_pid for entry in result)


class TestDescendantMaxDepth:
    """DS 10101 F3: the BFS walker is depth-capped to bound traversal
    on pathological process trees. _DESCENDANT_MAX_DEPTH=5 is generous
    headroom over the realistic cmd.exe → claude.exe depth-1 case.
    """

    def test_max_depth_constant_is_sensible(self):
        assert thin_launcher._DESCENDANT_MAX_DEPTH >= 2  # cmd → node → claude
        assert thin_launcher._DESCENDANT_MAX_DEPTH <= 20  # not unbounded
