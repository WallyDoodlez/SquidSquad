"""Unit tests for #9688 — orphan claude.exe cleanup.

Three protections are non-negotiable and each gets at least one dedicated
test:

  1. **Self-protection** — the live agent PID (from ``.claude-pid``) and the
     current Python interpreter PID must never appear in the kill list.
  2. **Clone-scoped** — processes whose command line does not reference the
     clone path are left alone. Another SquidSquad clone on the same Windows
     box must survive a cleanup run.
  3. **Parent-dead** — a subagent whose parent is still alive is still doing
     useful work; only parent-dead orphans are killed.

The cleanup runs against a real ``Get-CimInstance`` snapshot on Windows; the
tests inject a fake snapshot via the module-level helpers so they pass on
Linux CI too.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import orphan_cleanup  # noqa: E402


CLONE = Path(r"D:\Dev\Dev\SquidSquad-2")


def _fake_proc(pid: int, ppid: int, cmd: str) -> dict:
    return {"pid": pid, "ppid": ppid, "cmdline": cmd}


# --- Self-protection -------------------------------------------------------

def test_live_agent_pid_never_in_kill_list():
    """The PID recorded in .claude-pid must be excluded even if it would
    otherwise qualify as an orphan (clone match + parent dead)."""
    live_pid = 11111
    procs = [
        _fake_proc(live_pid, 99999, f"claude.exe ... cwd={CLONE}"),
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False):
        orphans = orphan_cleanup.find_orphans(
            "skill", clone_path=CLONE, live_pid=live_pid,
        )
    assert orphans == [], (
        "live agent PID slipped into the kill list — self-protection broken"
    )


def test_missing_claude_pid_does_not_endanger_live_agent():
    """REGRESSION for #9688 R1 LOW: when `.claude-pid` is absent or
    unparseable, ``_read_live_pid`` returns ``None`` and the explicit
    live-PID exclusion no longer fires. The secondary protections
    (clone-scope + parent-dead) must keep the live agent safe — its
    parent (the launcher cmd.exe) is alive, so the parent-dead check
    rejects it. Verify that contract end-to-end.
    """
    live_agent_pid = 22222
    orphan_pid = 33333
    procs = [
        _fake_proc(live_agent_pid, 11111, f"claude.exe ... cwd={CLONE}"),
        _fake_proc(orphan_pid, 99999, f"claude.exe ... cwd={CLONE}"),
    ]
    # 11111 = launcher cmd.exe (alive); 99999 = dead parent of orphan.
    def fake_alive(pid):
        return pid == 11111
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", side_effect=fake_alive):
        # live_pid=None simulates absent/unparseable .claude-pid.
        orphans = orphan_cleanup.find_orphans(
            "skill", clone_path=CLONE, live_pid=None,
        )
    pids = {p["pid"] for p in orphans}
    assert live_agent_pid not in pids, (
        f"live agent PID {live_agent_pid} would be killed when .claude-pid "
        f"is missing — secondary protections (parent-alive) failed to hold"
    )
    assert orphan_pid in pids, (
        f"actual orphan {orphan_pid} not detected — sanity check failed"
    )


def test_own_python_pid_never_in_kill_list():
    """The Python interpreter running this script must be excluded even when
    no .claude-pid is available."""
    own = os.getpid()
    procs = [
        _fake_proc(own, 99999, f"claude.exe ... cwd={CLONE}"),
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False):
        orphans = orphan_cleanup.find_orphans(
            "skill", clone_path=CLONE, live_pid=None,
        )
    assert orphans == [], (
        "own PID slipped into the kill list — running orphan_cleanup must "
        "never target the process that ran it"
    )


# --- Clone-scoped ----------------------------------------------------------

def test_other_clone_processes_are_skipped():
    """A claude.exe from a different SquidSquad clone must not be touched."""
    other_clone = Path(r"D:\Dev\Dev\OtherClone")
    procs = [
        _fake_proc(2222, 99999, f"claude.exe ... cwd={other_clone}"),
        _fake_proc(3333, 99999, f"claude.exe ... cwd={CLONE}"),
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False):
        orphans = orphan_cleanup.find_orphans(
            "skill", clone_path=CLONE, live_pid=None,
        )
    pids = {p["pid"] for p in orphans}
    assert 2222 not in pids, "killed a process from a different clone — scope broken"
    assert 3333 in pids, "missed an orphan from this clone — scope too strict"


def test_clone_match_is_case_insensitive():
    """Path match must not depend on drive-letter case; Windows paths come
    back from CIM in either casing depending on how the agent was started."""
    procs = [
        _fake_proc(4444, 99999,
                   f"claude.exe ... cwd={str(CLONE).lower()}"),
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False):
        orphans = orphan_cleanup.find_orphans(
            "skill", clone_path=CLONE, live_pid=None,
        )
    assert any(p["pid"] == 4444 for p in orphans), (
        "case-mismatched clone path was incorrectly rejected"
    )


def test_sibling_clone_with_path_prefix_not_killed():
    """REGRESSION for the BLOCKER caught in code review (#9688 R1): a plain
    substring match would false-positive a sibling clone whose absolute
    path begins with this clone's path. ``D:\\Dev\\SquidSquad-2`` as the
    needle would otherwise match ``D:\\Dev\\SquidSquad-2-other`` because
    the latter is a superset string. The fix requires the next character
    after the needle to be a path separator, quote, or end-of-string.
    """
    sibling = r"D:\Dev\Dev\SquidSquad-2-other"
    procs = [
        _fake_proc(7001, 99999, f"claude.exe ... cwd={sibling}\\sub"),
        _fake_proc(7002, 99999, f"claude.exe ... cwd={sibling}"),
        _fake_proc(7003, 99999, f"claude.exe ... cwd={CLONE}"),
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False):
        orphans = orphan_cleanup.find_orphans(
            "skill", clone_path=CLONE, live_pid=None,
        )
    pids = {p["pid"] for p in orphans}
    assert 7001 not in pids and 7002 not in pids, (
        f"sibling clone with path prefix `{sibling}` was incorrectly killed "
        f"— the boundary-aware path match is broken; would silently destroy "
        f"a parallel clone's agent on every cycle"
    )
    assert 7003 in pids, (
        "the genuine in-clone orphan was rejected — boundary check is too "
        "strict"
    )


def test_clone_match_accepts_path_at_eos_quote_or_separator():
    """Three valid boundary terminators after the clone path: path
    separator (most common), closing quote (CIM emits quoted cmdline
    sometimes), and end-of-string. Each one must match."""
    cases = [
        f"claude.exe --cwd {CLONE}\\.squidsquad\\skill",  # separator
        f'claude.exe --cwd "{CLONE}"',                    # quote
        f"claude.exe --cwd {CLONE}",                      # end-of-string
    ]
    for cmd in cases:
        assert orphan_cleanup._matches_clone(cmd, CLONE), (
            f"valid boundary terminator rejected for cmdline: {cmd!r}"
        )


# --- Parent-dead -----------------------------------------------------------

def test_subagent_with_live_parent_is_not_orphan():
    """An Agent-tool subagent whose cmd.exe parent is still alive is mid-task
    and must not be killed."""
    procs = [
        _fake_proc(5555, 7777, f"claude.exe ... cwd={CLONE}"),  # parent live
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=True):
        orphans = orphan_cleanup.find_orphans(
            "skill", clone_path=CLONE, live_pid=None,
        )
    assert orphans == [], (
        "a subagent with a LIVE parent was flagged as an orphan — would "
        "interrupt active Agent-tool work"
    )


def test_subagent_with_dead_parent_is_orphan():
    """The actual #9688 scenario: subagent's parent cmd.exe has exited,
    subagent is now reparented to a dead PID — kill it."""
    procs = [
        _fake_proc(6666, 99999, f"claude.exe ... cwd={CLONE}"),  # parent dead
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False):
        orphans = orphan_cleanup.find_orphans(
            "skill", clone_path=CLONE, live_pid=None,
        )
    assert [p["pid"] for p in orphans] == [6666]


def test_parent_in_snapshot_is_treated_as_alive():
    """If the parent PID is itself another claude.exe in our snapshot, that
    parent is alive by construction (we just enumerated it) — child is not
    an orphan even without an extra is_pid_alive call."""
    procs = [
        _fake_proc(7777, 0, f"claude.exe ... cwd={CLONE}"),     # live root
        _fake_proc(8888, 7777, f"claude.exe ... cwd={CLONE}"),  # child of 7777
    ]
    # _is_pid_alive should NOT be consulted for pid 7777 — the snapshot
    # short-circuits. Set it to False to make any leak loud.
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False) as alive:
        orphans = orphan_cleanup.find_orphans(
            "skill", clone_path=CLONE, live_pid=7777,
        )
    pids = {p["pid"] for p in orphans}
    assert 8888 not in pids, (
        "child of a live snapshot parent was killed — snapshot short-circuit "
        "broken"
    )
    # 7777 is the live agent PID we just told find_orphans about — also
    # excluded by the self-protection check.
    assert 7777 not in pids


# --- Platform gating -------------------------------------------------------

def test_posix_returns_empty_without_calling_powershell():
    """find_orphans must short-circuit on non-Windows. Cycle_post runs on
    every host; this guard prevents a PowerShell invocation on Linux CI."""
    with patch.object(orphan_cleanup, "_is_windows", return_value=False), \
         patch.object(orphan_cleanup, "_list_claude_processes") as listed:
        orphans = orphan_cleanup.find_orphans("skill")
    assert orphans == []
    listed.assert_not_called()


# --- CSV parsing edge case -------------------------------------------------

def test_csv_split_handles_commas_inside_cmdline():
    """``Get-CimInstance`` quotes the CommandLine column, but the column
    body legitimately contains commas (Agent-tool flags etc.). The hand-
    rolled splitter must keep them with the cmdline field, not break them
    out as new columns."""
    row = '"4321","6789","claude.exe --flag a,b,c --cwd D:\\foo"'
    parts = orphan_cleanup._split_csv_three(row)
    assert parts is not None
    pid_s, ppid_s, cmd = parts
    assert pid_s == "4321"
    assert ppid_s == "6789"
    assert cmd == "claude.exe --flag a,b,c --cwd D:\\foo"


def test_csv_split_rejects_malformed_row():
    """An unquoted or partial row returns None — we'd rather drop a single
    row than corrupt the parsed PID."""
    assert orphan_cleanup._split_csv_three("nonsense") is None
    assert orphan_cleanup._split_csv_three('"only-one-field"') is None


def test_csv_split_unescapes_embedded_doubled_quotes():
    """REGRESSION for #9688 R1 MEDIUM: PowerShell ConvertTo-Csv escapes
    embedded ``"`` by doubling it to ``""``. The CommandLine column
    legitimately contains quoted args (e.g. ``--config "C:\\path with
    space"``), so the row arrives with sequences like ``""C:\\path""``
    that the parser must collapse back to ``"C:\\path"`` to keep the
    cmdline accurate for downstream matching and logging.
    """
    row = (
        '"1234","5678",'
        '"claude.exe --config ""D:\\Dev\\Dev\\SquidSquad-2"" --extra arg"'
    )
    parts = orphan_cleanup._split_csv_three(row)
    assert parts is not None
    pid_s, ppid_s, cmd = parts
    assert pid_s == "1234"
    assert ppid_s == "5678"
    # The doubled quotes must be collapsed; downstream path matching
    # works on the unescaped path, not the doubled-up version.
    assert cmd == 'claude.exe --config "D:\\Dev\\Dev\\SquidSquad-2" --extra arg', (
        f"PowerShell `\"\"` escaping not unwrapped — cmd was {cmd!r}"
    )


# --- cleanup() integration -------------------------------------------------

def test_cleanup_dry_run_does_not_kill():
    """Dry-run mode reports found orphans without invoking taskkill."""
    procs = [
        _fake_proc(9999, 88888, f"claude.exe ... cwd={CLONE}"),
    ]
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False), \
         patch.object(orphan_cleanup, "_read_live_pid", return_value=None), \
         patch.object(orphan_cleanup, "REPO_ROOT", CLONE), \
         patch.object(orphan_cleanup, "kill_orphan") as killer:
        result = orphan_cleanup.cleanup("skill", dry_run=True)
    killer.assert_not_called()
    assert result["found"] == [9999]
    assert result["killed"] == []


def test_cleanup_records_killed_and_skipped():
    """The cleanup summary distinguishes between PIDs taskkill succeeded on
    and PIDs that refused (returned non-zero) — caller logs both."""
    procs = [
        _fake_proc(1001, 88888, f"claude.exe ... cwd={CLONE}"),
        _fake_proc(1002, 88888, f"claude.exe ... cwd={CLONE}"),
    ]
    # 1001 dies cleanly, 1002 refuses.
    def fake_kill(pid):
        return pid == 1001
    with patch.object(orphan_cleanup, "_is_windows", return_value=True), \
         patch.object(orphan_cleanup, "_list_claude_processes", return_value=procs), \
         patch.object(orphan_cleanup, "_is_pid_alive", return_value=False), \
         patch.object(orphan_cleanup, "_read_live_pid", return_value=None), \
         patch.object(orphan_cleanup, "REPO_ROOT", CLONE), \
         patch.object(orphan_cleanup, "kill_orphan", side_effect=fake_kill):
        result = orphan_cleanup.cleanup("skill", dry_run=False)
    assert sorted(result["killed"]) == [1001]
    assert sorted(result["skipped"]) == [1002]
