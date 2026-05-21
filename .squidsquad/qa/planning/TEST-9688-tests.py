"""Live-system pytest for #9688 — orphan claude.exe Agent-tool subagent cleanup.

Maps 1:1 to TC-1…TC-12 in TEST-PLAN-9688.md. Tests run against the deployed
state of the repo: the live `orphan_cleanup.py` module, `cycle_post.py`,
`boot_remote.py`, `docs/ARCHITECTURE.md`, the diagnostics dir, and the
real process table (TC-12 only, dry-run).
"""

from __future__ import annotations

import importlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

# Walk up until we find references/scripts/compose.py — works from both
# .squidsquad/qa/planning/ and tests/.
def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "references" / "scripts" / "compose.py").exists():
            return parent
    raise RuntimeError(f"Could not locate repo root from {here}")

REPO_ROOT = _find_repo_root()
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
DOCS = REPO_ROOT / "docs"
DIAG_DIR = REPO_ROOT / ".squidsquad" / "diagnostics"

sys.path.insert(0, str(SCRIPTS_DIR))
import orphan_cleanup  # noqa: E402


# TC-1
def test_tc_01_orphan_cleanup_public_api():
    assert callable(orphan_cleanup.sweep)
    assert callable(orphan_cleanup._classify)
    summary = orphan_cleanup.sweep(invoked_by="qa-verify-tc1", dry_run=True)
    assert isinstance(summary, dict)
    for key in ("kept", "killed", "skipped_roles", "skipped_run",
                "platform", "invoked_by"):
        assert key in summary, f"sweep summary missing key {key!r}"


# TC-2
def test_tc_02_cycle_post_invokes_sweep_with_role_attribution():
    src = (SCRIPTS_DIR / "cycle_post.py").read_text(encoding="utf-8")
    assert "import orphan_cleanup" in src
    # Match either the f-string form or the .format form.
    assert re.search(
        r'orphan_cleanup\.sweep\(invoked_by=f["\']cycle_post:\{role\}["\']\)',
        src,
    ), "cycle_post must call orphan_cleanup.sweep(invoked_by=f'cycle_post:{role}')"


# TC-3
def test_tc_03_boot_remote_invokes_sweep_before_spawn():
    src = (SCRIPTS_DIR / "boot_remote.py").read_text(encoding="utf-8")
    assert "import orphan_cleanup" in src
    # Scope the order check to the boot_agent function body — the file also
    # defines _spawn_terminal at the top level, which would otherwise appear
    # earlier than the sweep call by raw byte index.
    boot_agent_def = src.find("def boot_agent(")
    assert boot_agent_def != -1, "boot_remote must define boot_agent"
    # Function body ends at next top-level `def ` or EOF.
    after = src[boot_agent_def + 1:]
    next_def = re.search(r"\ndef [A-Za-z_]", after)
    body_end = boot_agent_def + 1 + (next_def.start() if next_def else len(after))
    body = src[boot_agent_def:body_end]

    sweep_call = re.search(
        r'orphan_cleanup\.sweep\(invoked_by=f["\']boot_remote:\{role\}["\']\)',
        body,
    )
    assert sweep_call, (
        "boot_agent must call orphan_cleanup.sweep(invoked_by=f'boot_remote:{role}')"
    )
    spawn_call_idx = body.find("_spawn_terminal(")
    assert spawn_call_idx != -1, "boot_agent must invoke _spawn_terminal(…)"
    assert sweep_call.start() < spawn_call_idx, (
        "sweep must run BEFORE _spawn_terminal — orphan cleanup happens "
        "pre-spawn per CONTEXT-9688 §2.1"
    )


# TC-4
def test_tc_04_diagnostics_log_is_jsonl_with_d4_schema(tmp_path, monkeypatch):
    log_path = tmp_path / "orphan-cleanup.jsonl"
    monkeypatch.setattr(orphan_cleanup, "DIAGNOSTICS_LOG", log_path)
    # Force POSIX path so we get the "skipped" log entry deterministically
    monkeypatch.setattr(orphan_cleanup, "_is_windows", lambda: False)
    orphan_cleanup.sweep(invoked_by="qa-verify-tc4", dry_run=True)
    assert log_path.exists(), "diagnostics log not created"
    lines = [ln for ln in log_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert lines, "diagnostics log is empty after sweep"
    last = json.loads(lines[-1])
    # D4 schema: at minimum timestamp + decision + reason for skip records;
    # per-process records add pid + parent_pid.
    assert "timestamp" in last
    assert "decision" in last
    assert "reason" in last
    assert last["invoked_by"] == "qa-verify-tc4"


# TC-5
def test_tc_05_classify_routes_each_population_correctly():
    own = os.getpid()
    npm_cmd = (
        r"C:\Users\x\AppData\Roaming\npm\node_modules\@anthropic-ai"
        r"\claude-code\bin\claude.exe"
    )
    other_cmd = r"C:\Other\bin\claude.exe"

    # Patch _is_pid_alive to a deterministic set: 1000 alive (mocked cmd.exe),
    # 2000 alive (live subagent parent), 9999 dead (orphan parent).
    alive = {1000, 2000}
    with mock.patch.object(orphan_cleanup, "_is_pid_alive",
                            side_effect=lambda p: p in alive):
        protected = {1001}  # claude.exe child of cmd.exe 1000

        # Protected agent
        d, _ = orphan_cleanup._classify(
            {"pid": 1001, "ppid": 1000, "cmdline": npm_cmd}, protected
        )
        assert d == "kept"

        # Orphan (parent 9999 dead, npm path)
        d, r = orphan_cleanup._classify(
            {"pid": 1234, "ppid": 9999, "cmdline": npm_cmd}, protected
        )
        assert d == "killed"
        assert "orphan" in r

        # Live subagent (parent alive but not in protected set)
        d, _ = orphan_cleanup._classify(
            {"pid": 5678, "ppid": 2000, "cmdline": npm_cmd}, protected
        )
        assert d == "kept"

        # Non-npm claude.exe
        d, r = orphan_cleanup._classify(
            {"pid": 4321, "ppid": 9999, "cmdline": other_cmd}, protected
        )
        assert d == "kept"
        assert "out of scope" in r


# TC-6
def test_tc_06_posix_runs_silently_no_kills(monkeypatch, tmp_path):
    monkeypatch.setattr(orphan_cleanup, "_is_windows", lambda: False)
    monkeypatch.setattr(orphan_cleanup, "DIAGNOSTICS_LOG",
                        tmp_path / "orphan-cleanup.jsonl")
    kill_calls = []
    monkeypatch.setattr(orphan_cleanup, "_kill",
                        lambda pid: kill_calls.append(pid) or True)
    summary = orphan_cleanup.sweep(invoked_by="qa-verify-posix")
    assert summary["killed"] == []
    assert summary["kept"] == []
    assert kill_calls == [], "POSIX path must not invoke _kill"


# TC-7
def test_tc_07_unit_suite_covers_seven_d7_cases():
    r = subprocess.run(
        [sys.executable, "-m", "pytest",
         str(REPO_ROOT / "tests" / "test_orphan_cleanup_9688.py"),
         "-q", "--tb=short"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert r.returncode == 0, f"Unit suite failed:\n{r.stdout}\n{r.stderr}"
    test_text = (REPO_ROOT / "tests" / "test_orphan_cleanup_9688.py").read_text(
        encoding="utf-8"
    )
    # Each of the 7 D7 cases must have at least one corresponding test function.
    d7_signatures = [
        "empty_process_list",
        "single_protected_agent",
        "full_squad_protected",
        "orphan_killed",
        "live_subagent",
        "missing_claude_pid",
        "mixed_population",
    ]
    for sig in d7_signatures:
        assert re.search(rf"def test_\w*{sig}\w*\(", test_text), (
            f"D7 case {sig!r} has no matching test function in the unit suite"
        )


# TC-8
def test_tc_08_architecture_md_has_locked_d8_sections():
    text = (DOCS / "ARCHITECTURE.md").read_text(encoding="utf-8")
    for heading in (
        "### Agent Process Tree",
        "### `.claude-pid` convention",
        "### Killing agents",
        "### Three claude.exe populations",
    ):
        assert heading in text, f"ARCHITECTURE.md missing locked heading {heading!r}"
    # Locked phrasing markers from CONTEXT-9688 §3
    for marker in (
        "python.exe (thin_launcher.py)",
        "cmd.exe (claude.CMD shim from npm install)",
        "claude.exe (the actual agent)",
        "taskkill /F /T",
        "Protected agent",
        "Live subagent",
        "Orphan",
    ):
        assert marker in text, f"ARCHITECTURE.md missing locked phrase {marker!r}"


# TC-9
def test_tc_09_non_npm_claude_exe_is_kept():
    decision, reason = orphan_cleanup._classify(
        {"pid": 1234, "ppid": 9999, "cmdline": r"C:\Other\claude.exe"},
        protected=set(),
    )
    assert decision == "kept"
    assert "out of scope" in reason.lower()


# TC-10
def test_tc_10_missing_pid_file_aborts_entire_sweep(monkeypatch, tmp_path):
    monkeypatch.setattr(orphan_cleanup, "_is_windows", lambda: True)
    monkeypatch.setattr(
        orphan_cleanup, "_list_claude_processes",
        lambda: [{"pid": 1234, "ppid": 9999,
                  "cmdline": r"x\node_modules\@anthropic-ai\claude-code\bin\claude.exe"}],
    )
    monkeypatch.setattr(
        orphan_cleanup, "_role_pid_files",
        lambda: {"skill": tmp_path / "nonexistent.claude-pid"},
    )
    monkeypatch.setattr(orphan_cleanup, "DIAGNOSTICS_LOG",
                        tmp_path / "orphan-cleanup.jsonl")
    summary = orphan_cleanup.sweep(invoked_by="qa-verify-tc10", dry_run=True)
    assert summary["skipped_run"] is True
    assert summary["skipped_roles"], "skipped_roles list should be populated"
    assert summary["killed"] == []


# TC-11
def test_tc_11_own_pid_never_killed(monkeypatch, tmp_path):
    own = os.getpid()
    monkeypatch.setattr(orphan_cleanup, "_is_windows", lambda: True)
    monkeypatch.setattr(
        orphan_cleanup, "_list_claude_processes",
        lambda: [{
            "pid": own, "ppid": 9999,
            "cmdline": r"x\node_modules\@anthropic-ai\claude-code\bin\claude.exe",
        }],
    )
    monkeypatch.setattr(orphan_cleanup, "_role_pid_files", lambda: {})
    monkeypatch.setattr(orphan_cleanup, "DIAGNOSTICS_LOG",
                        tmp_path / "orphan-cleanup.jsonl")
    # With no roles → skipped_run per D3. But own-pid filter should still
    # prevent inclusion in killed. Force the skip-path off by patching
    # _resolve_protected_pids to return empty without skips.
    monkeypatch.setattr(
        orphan_cleanup, "_resolve_protected_pids",
        lambda role_pid_files, processes: (set(), []),
    )
    kill_calls = []
    monkeypatch.setattr(orphan_cleanup, "_kill",
                        lambda pid: kill_calls.append(pid) or True)
    summary = orphan_cleanup.sweep(invoked_by="qa-verify-tc11")
    assert own not in summary["killed"]
    assert own not in kill_calls


# TC-12
def test_tc_12_live_smoke_dry_run_does_not_crash():
    summary = orphan_cleanup.sweep(invoked_by="qa-verify-live", dry_run=True)
    assert isinstance(summary, dict)
    assert summary["invoked_by"] == "qa-verify-live"
    # The live agent (this very process) must never appear in killed.
    assert os.getpid() not in summary["killed"]
