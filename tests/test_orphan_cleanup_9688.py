"""Unit tests for #9688 — orphan claude.exe cleanup per CONTEXT-9688.md.

D7 locks 7 mandatory test scenarios; each gets a dedicated test below.
Additional tests cover the npm-install-path filter (CONTEXT D2 §7
Out-of-Scope), the CSV parser edge cases, the POSIX no-op, and the
JSONL diagnostics log shape (D4).

The CONTEXT reverses the initial protection model: `.claude-pid`
stores the **cmd.exe** PID, not the claude.exe PID. Tests assert that
``_resolve_protected_pids`` walks cmd.exe → child claude.exe via
``ParentProcessId``, and that classify uses the resulting ``protected``
set rather than comparing against the raw `.claude-pid` contents.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import orphan_cleanup  # noqa: E402


# Canonical npm-install claude.exe path used in fake CommandLines so the
# CONTEXT D2 path filter accepts the process.
NPM_CLAUDE = (
    r"C:\Users\test\AppData\Roaming\npm\node_modules"
    r"\@anthropic-ai\claude-code\bin\claude.exe"
)


def _fake_proc(pid, ppid, cmd=None):
    if cmd is None:
        cmd = f'"{NPM_CLAUDE}" --strict-mcp-config'
    return {"pid": pid, "ppid": ppid, "cmdline": cmd}


@pytest.fixture
def patched_log(tmp_path):
    """Redirect the diagnostics log to a tmp file so tests can read it back."""
    log = tmp_path / "orphan-cleanup.log"
    with patch.object(orphan_cleanup, "DIAGNOSTICS_LOG", log):
        yield log


def _read_log_lines(path):
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def _setup_pid_files(tmp_path, role_pids):
    """Create ``<tmp>/<role-clone>/.squidsquad/<role>/.claude-pid`` files;
    return ``(squid_dir, role_pid_map)`` where ``role_pid_map`` is what
    ``_role_pid_files()`` would return — tests patch that helper directly
    instead of trying to make ``_parse_local_config`` round-trip through a
    fake ``.local-config`` file.

    Returning the synthetic squid dir as the first element is kept for the
    handful of tests that exercise paths reading from it directly.
    """
    squid = tmp_path / ".squidsquad"
    role_pid_map = {}
    for role, pid in role_pids.items():
        # Each role's pid file lives under <its-own-clone>/.squidsquad/<role>/
        # in multi-clone setups. The tests use one shared tmp_path tree;
        # the resulting map mirrors what cross-clone discovery would return.
        d = squid / role
        d.mkdir(parents=True, exist_ok=True)
        pid_file = d / ".claude-pid"
        pid_file.write_text(str(pid), encoding="utf-8")
        role_pid_map[role] = pid_file
    return squid, role_pid_map


# ---------------------------------------------------------------------------
# D7 #1 — Empty process list → no kills
# ---------------------------------------------------------------------------

def test_d7_empty_process_list_no_kills(patched_log, tmp_path):
    squid, pid_map = _setup_pid_files(tmp_path, {})
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=[]), \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    killer.assert_not_called()
    assert result["killed"] == []
    assert result["skipped_run"] is False


# ---------------------------------------------------------------------------
# D7 #2 — Single protected agent (cmd.exe alive, claude.exe child) → no kills
# ---------------------------------------------------------------------------

def test_d7_single_protected_agent_no_kills(patched_log, tmp_path):
    cmd_pid = 1000
    claude_pid = 1001
    squid, pid_map = _setup_pid_files(tmp_path, {"skill": cmd_pid})
    procs = [_fake_proc(claude_pid, cmd_pid)]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=True), \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    killer.assert_not_called()
    assert result["killed"] == []
    log = _read_log_lines(patched_log)
    assert any(e.get("decision") == "kept"
               and "protected agent" in e.get("reason", "")
               for e in log), f"protected agent decision not logged; log={log}"


# ---------------------------------------------------------------------------
# D7 #3 — 4 protected agents (full squad) → no kills
# ---------------------------------------------------------------------------

def test_d7_full_squad_protected_no_kills(patched_log, tmp_path):
    roles = {"skill": 1000, "pm": 2000, "qa": 3000, "dm": 4000}
    squid, pid_map = _setup_pid_files(tmp_path, roles)
    procs = [
        _fake_proc(1001, 1000),
        _fake_proc(2001, 2000),
        _fake_proc(3001, 3000),
        _fake_proc(4001, 4000),
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=True), \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    killer.assert_not_called()
    assert result["killed"] == []
    assert sorted(result["kept"]) == [1001, 2001, 3001, 4001]


# ---------------------------------------------------------------------------
# D7 #4 — 1 protected + 1 orphan → 1 kill, parent_pid logged
# ---------------------------------------------------------------------------

def test_d7_orphan_killed_parent_pid_logged(patched_log, tmp_path):
    squid, pid_map = _setup_pid_files(tmp_path, {"skill": 1000})
    orphan_pid = 5005
    orphan_parent = 9999
    procs = [
        _fake_proc(1001, 1000),
        _fake_proc(orphan_pid, orphan_parent),
    ]
    def fake_alive(pid):
        return pid != orphan_parent
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", side_effect=fake_alive), \
         patch.object(orphan_cleanup, "_kill", return_value=True) as killer:
        result = orphan_cleanup.sweep()
    killer.assert_called_once_with(orphan_pid)
    assert result["killed"] == [orphan_pid]
    log = _read_log_lines(patched_log)
    kill_entries = [e for e in log if e.get("decision") == "killed"]
    assert len(kill_entries) == 1
    assert kill_entries[0]["pid"] == orphan_pid
    assert kill_entries[0]["parent_pid"] == orphan_parent, (
        "kill log entry must include parent_pid for forensic trace"
    )


# ---------------------------------------------------------------------------
# D7 #5 — 1 protected + 1 live subagent → no kills
# ---------------------------------------------------------------------------

def test_d7_live_subagent_with_non_protected_parent_not_killed(
    patched_log, tmp_path,
):
    squid, pid_map = _setup_pid_files(tmp_path, {"skill": 1000})
    subagent_parent = 7777
    procs = [
        _fake_proc(1001, 1000),
        _fake_proc(6006, subagent_parent),
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=True), \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    killer.assert_not_called()
    assert 6006 in result["kept"]


# ---------------------------------------------------------------------------
# D7 #6 — Missing .claude-pid for one role → ENTIRE cleanup skipped (D3)
# ---------------------------------------------------------------------------

def test_d7_missing_claude_pid_skips_entire_sweep(patched_log, tmp_path):
    squid, pid_map = _setup_pid_files(tmp_path, {"skill": 1000})
    # PM is configured (has a clone path resolvable via .local-config) but
    # its .claude-pid file is absent — D3 must fire.
    pid_map["pm"] = tmp_path / ".squidsquad" / "pm" / ".claude-pid"  # non-existent
    orphan_pid = 8008
    procs = [
        _fake_proc(1001, 1000),
        _fake_proc(orphan_pid, 99999),
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=True), \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    killer.assert_not_called()
    assert result["skipped_run"] is True, (
        "missing .claude-pid for any role must abort the ENTIRE sweep (D3)"
    )
    assert any(s["role"] == "pm" and "missing" in s["reason"]
               for s in result["skipped_roles"])


def test_no_roles_discoverable_skips_sweep(patched_log, tmp_path):
    """If `.local-config` is unavailable (returns empty {}), D3 fires too —
    rather miss the sweep than guess. This is the multi-clone safety net
    for the case where orphan_cleanup runs from a context without clone
    information."""
    procs = [_fake_proc(1001, 99999)]  # would be orphan if sweep ran
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value={}), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False), \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    killer.assert_not_called()
    assert result["skipped_run"] is True


def test_stale_pid_with_dead_cmdexe_also_skips_sweep(patched_log, tmp_path):
    """D3 also fires when .claude-pid exists but its cmd.exe is dead — that's
    a respawn race; rather miss the sweep than risk killing the new agent
    that's about to claim the role."""
    squid, pid_map = _setup_pid_files(tmp_path, {"skill": 1000, "pm": 2000})
    procs = [_fake_proc(1001, 1000)]
    def fake_alive(pid):
        return pid != 2000
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", side_effect=fake_alive), \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    killer.assert_not_called()
    assert result["skipped_run"] is True


# ---------------------------------------------------------------------------
# D7 #7 — Mix of all populations → only orphans killed
# ---------------------------------------------------------------------------

def test_d7_mixed_population_only_orphans_killed(patched_log, tmp_path):
    squid, pid_map = _setup_pid_files(tmp_path, {"skill": 1000, "pm": 2000})
    procs = [
        _fake_proc(1001, 1000),   # protected (skill)
        _fake_proc(2001, 2000),   # protected (pm)
        _fake_proc(3001, 7777),   # live subagent
        _fake_proc(4001, 9999),   # orphan
        _fake_proc(5001, 8888),   # orphan
    ]
    def fake_alive(pid):
        return pid in {1000, 2000, 7777}
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", side_effect=fake_alive), \
         patch.object(orphan_cleanup, "_kill", return_value=True):
        result = orphan_cleanup.sweep()
    assert sorted(result["killed"]) == [4001, 5001]
    assert sorted(result["kept"]) == [1001, 2001, 3001]


# ---------------------------------------------------------------------------
# CONTEXT D2 + §7 Out-of-Scope — npm-install-path filter
# ---------------------------------------------------------------------------

def test_non_npm_claude_exe_left_alone(patched_log, tmp_path):
    """User's own Claude Code CLI / IDE session running from a non-npm path
    must never be killed even if its parent is dead."""
    squid, pid_map = _setup_pid_files(tmp_path, {"skill": 1000})
    procs = [
        _fake_proc(1001, 1000),
        _fake_proc(7007, 99999,
                   cmd='"C:\\Program Files\\Claude\\claude.exe" --some-flag'),
    ]
    def fake_alive(pid):
        return pid == 1000
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", side_effect=fake_alive), \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    killer.assert_not_called()
    assert 7007 in result["kept"]
    log = _read_log_lines(patched_log)
    assert any(e.get("pid") == 7007 and "out of scope" in e.get("reason", "")
               for e in log)


# ---------------------------------------------------------------------------
# CONTEXT D6 — POSIX no-op
# ---------------------------------------------------------------------------

def test_posix_runs_and_exits_silently(patched_log, tmp_path):
    squid, pid_map = _setup_pid_files(tmp_path, {})
    with patch.object(orphan_cleanup, "_is_windows", return_value=False), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes") as listed, \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    listed.assert_not_called()
    killer.assert_not_called()
    assert result["killed"] == []
    log = _read_log_lines(patched_log)
    assert any(e.get("decision") == "skipped"
               and "non-windows" in e.get("reason", "") for e in log)


# ---------------------------------------------------------------------------
# CONTEXT D4 — JSONL diagnostics log shape
# ---------------------------------------------------------------------------

def test_d4_log_is_jsonl_with_required_fields(patched_log, tmp_path):
    squid, pid_map = _setup_pid_files(tmp_path, {"skill": 1000})
    procs = [
        _fake_proc(1001, 1000),
        _fake_proc(2002, 99999),
    ]
    def fake_alive(pid):
        return pid == 1000
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", side_effect=fake_alive), \
         patch.object(orphan_cleanup, "_kill", return_value=True):
        orphan_cleanup.sweep(invoked_by="cycle_post:skill")
    log = _read_log_lines(patched_log)
    assert len(log) >= 2, "expected one log entry per classified process"
    for entry in log:
        assert "timestamp" in entry
        assert "decision" in entry
        assert "reason" in entry
        if "pid" in entry:
            assert "parent_pid" in entry, entry


# ---------------------------------------------------------------------------
# CSV parser edges (kept from R1 regression coverage)
# ---------------------------------------------------------------------------

def test_csv_split_handles_commas_inside_cmdline():
    row = '"4321","6789","claude.exe --flag a,b,c --cwd D:\\foo"'
    parts = orphan_cleanup._split_csv_three(row)
    assert parts == ("4321", "6789", "claude.exe --flag a,b,c --cwd D:\\foo")


def test_csv_split_rejects_malformed_row():
    assert orphan_cleanup._split_csv_three("nonsense") is None
    assert orphan_cleanup._split_csv_three('"only-one-field"') is None


def test_csv_split_unescapes_embedded_doubled_quotes():
    row = (
        '"1234","5678",'
        '"claude.exe --config ""D:\\Path with space"" --extra"'
    )
    parts = orphan_cleanup._split_csv_three(row)
    assert parts is not None
    assert parts[2] == 'claude.exe --config "D:\\Path with space" --extra'


# ---------------------------------------------------------------------------
# Defensive: the running Python interpreter must never be targeted
# ---------------------------------------------------------------------------

def test_own_pid_never_targeted(patched_log, tmp_path):
    """The Python running the cleanup module must not be killed even if
    (impossibly) it was listed by Get-CimInstance as a claude.exe with a
    dead parent — defense in depth."""
    import os as _os
    own = _os.getpid()
    squid, pid_map = _setup_pid_files(tmp_path, {"skill": 1000})
    procs = [
        _fake_proc(1001, 1000),
        _fake_proc(own, 99999),
    ]
    def fake_alive(pid):
        return pid == 1000
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", side_effect=fake_alive), \
         patch.object(orphan_cleanup, "_kill") as killer:
        result = orphan_cleanup.sweep()
    called_pids = {call.args[0] for call in killer.call_args_list}
    assert own not in called_pids
    assert own not in result["killed"]


# ---------------------------------------------------------------------------
# #9937 — _kill re-verifies PID is still claude.exe before taskkill
# ---------------------------------------------------------------------------


class TestKillReverify9937:
    """#9937: _kill must re-verify the target is still a claude.exe
    process at kill time. Windows can recycle a PID for any executable
    between the _list_claude_processes() snapshot and the taskkill call;
    without re-verification, an unrelated process at the recycled PID
    would be force-killed (contradicting CONTEXT-9688 D2's 'never touch
    the user's IDE' guarantee).
    """

    def test_kill_skipped_when_pid_recycled_to_non_claude(self):
        """If _pid_is_claude_exe returns False (PID gone or recycled to
        a different executable), _kill must NOT call taskkill — and must
        return False."""
        with patch.object(orphan_cleanup, "_pid_is_claude_exe", return_value=False), \
             patch.object(orphan_cleanup, "subprocess") as mock_sp:
            result = orphan_cleanup._kill(12345)
        assert result is False
        # taskkill must not have fired.
        mock_sp.run.assert_not_called()

    def test_kill_proceeds_when_pid_still_claude(self):
        """When the re-verify confirms the PID still names a claude.exe,
        taskkill fires as before."""
        fake_result = type("R", (), {"returncode": 0})()
        with patch.object(orphan_cleanup, "_pid_is_claude_exe", return_value=True), \
             patch.object(orphan_cleanup, "_is_windows", return_value=True), \
             patch.object(orphan_cleanup.subprocess, "run", return_value=fake_result) as mock_run:
            result = orphan_cleanup._kill(12345)
        assert result is True
        # The actual taskkill call should have happened exactly once,
        # with /F /PID 12345.
        assert mock_run.called
        args = mock_run.call_args.args[0]
        assert args[0] == "taskkill"
        assert "/F" in args
        assert "12345" in args

    def test_pid_is_claude_exe_parses_tasklist_csv(self):
        """_pid_is_claude_exe must accept tasklist's CSV output and
        return True only when the first column (image name) is
        'claude.exe' (case-insensitive)."""
        fake = type("R", (), {
            "returncode": 0,
            "stdout": '"claude.exe","12345","Console","1","123,456 K"\n',
        })()
        with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
             patch.object(orphan_cleanup.subprocess, "run", return_value=fake):
            assert orphan_cleanup._pid_is_claude_exe(12345) is True

    def test_pid_is_claude_exe_rejects_other_exe(self):
        """Recycled to notepad.exe (or anything not claude.exe) — False."""
        fake = type("R", (), {
            "returncode": 0,
            "stdout": '"notepad.exe","12345","Console","1","8,000 K"\n',
        })()
        with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
             patch.object(orphan_cleanup.subprocess, "run", return_value=fake):
            assert orphan_cleanup._pid_is_claude_exe(12345) is False

    def test_pid_is_claude_exe_handles_case_insensitive(self):
        """Windows is case-insensitive; tasklist may emit Claude.EXE or
        CLAUDE.EXE depending on how the process was launched. Match
        must be case-insensitive."""
        for variant in ('"Claude.exe","12345"', '"CLAUDE.EXE","12345"'):
            fake = type("R", (), {"returncode": 0, "stdout": variant + ',"Console","1","100 K"\n'})()
            with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
                 patch.object(orphan_cleanup.subprocess, "run", return_value=fake):
                assert orphan_cleanup._pid_is_claude_exe(12345) is True, (
                    f"case-insensitive match failed for variant: {variant!r}"
                )

    def test_pid_is_claude_exe_returns_false_on_dead_pid(self):
        """If tasklist returns no matching row (PID is gone), the
        function returns False — caller must NOT proceed with the kill."""
        fake = type("R", (), {
            "returncode": 0,
            "stdout": "INFO: No tasks are running which match the specified criteria.\n",
        })()
        with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
             patch.object(orphan_cleanup.subprocess, "run", return_value=fake):
            assert orphan_cleanup._pid_is_claude_exe(12345) is False

    def test_pid_is_claude_exe_returns_false_on_invalid_pid(self):
        """Zero / negative PIDs are nonsense; return False without
        making any subprocess call."""
        with patch.object(orphan_cleanup.subprocess, "run") as mock_run:
            assert orphan_cleanup._pid_is_claude_exe(0) is False
            assert orphan_cleanup._pid_is_claude_exe(-1) is False
            assert orphan_cleanup._pid_is_claude_exe(None) is False
            mock_run.assert_not_called()

    def test_pid_is_claude_exe_returns_false_on_tasklist_failure(self):
        """If tasklist itself errors (OSError, TimeoutExpired), the
        verifier must return False — better to skip a kill than risk
        killing the wrong process when we can't verify."""
        for exc in (OSError("tasklist missing"),
                    orphan_cleanup.subprocess.TimeoutExpired(["tasklist"], 10)):
            with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
                 patch.object(orphan_cleanup.subprocess, "run", side_effect=exc):
                assert orphan_cleanup._pid_is_claude_exe(12345) is False

    def test_end_to_end_recycled_pid_is_not_killed(self, patched_log, tmp_path):
        """Integration: orphan in snapshot has its PID recycled by the
        time _kill is called. The sweep classified it as orphan based
        on the snapshot, but the re-verify catches the recycle and
        skips the kill. Resulting summary lists the PID under 'kept'
        (taskkill returned non-zero per the existing 'taskkill returned
        non-zero' fallback path), not 'killed'.
        """
        squid, pid_map = _setup_pid_files(tmp_path, {"skill": 1000})
        # Snapshot: orphan claude.exe (parent dead) — would normally be killed.
        procs = [
            _fake_proc(1001, 1000),        # protected (cmd.exe 1000 alive)
            _fake_proc(9999, 88888),       # orphan candidate (parent 88888 dead)
        ]
        def fake_alive(pid):
            # cmd.exe 1000 alive (protected role), other parents dead.
            return pid == 1000
        # By kill time, PID 9999 was recycled to a non-claude process.
        with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
             patch.object(orphan_cleanup, "_role_pid_files", return_value=pid_map), \
             patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
             patch.object(orphan_cleanup, "_is_pid_alive", side_effect=fake_alive), \
             patch.object(orphan_cleanup, "_pid_is_claude_exe", return_value=False):
            result = orphan_cleanup.sweep()
        # The recycled PID must NOT be in 'killed'.
        assert 9999 not in result["killed"], (
            "#9937 regression: recycled PID was killed despite _pid_is_claude_exe=False"
        )
