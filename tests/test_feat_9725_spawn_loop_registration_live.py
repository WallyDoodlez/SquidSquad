"""Live-system pytest for the thin_launcher spawn prompt.

ORIGIN #9725 made the spawn prompt a literal `/loop <N>m ...` registration.
#11512 SUPERSEDES that: forcing /loop on the first turn preempted composed
CLAUDE.md boot Step 1 (the harness probe that selects event vs polling mode),
so every agent booted loop mode and event mode was never reached. The spawn
prompt is now a mode-neutral boot trigger (`thin_launcher._SPAWN_PROMPT`) and
mode selection lives solely in boot Step 1. These cases assert the #11512
contract.

TC mapping:
  TC-1 → #11512: thin_launcher.main builds a command whose last positional is
              the mode-neutral _SPAWN_PROMPT, contains no /loop directive, and
              still excludes the pre-#9725 "Boot. Begin your first Ralph Loop
              cycle now." prompt.
  TC-5 → dev unit suite green (`tests/test_thin_launcher.py`)
  TC-6 → live-witness: agents on this team commit one `<role>: cycle <N>`
         per cycle regardless of wake mode (cycle_post fires under both event
         and loop modes). Structural smoke check on origin/main history.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


def _find_repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "references" / "scripts" / "compose.py").exists():
            return parent
    raise RuntimeError(f"Could not locate repo root from {here}")


REPO_ROOT = _find_repo_root()
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"

sys.path.insert(0, str(SCRIPTS_DIR))
import thin_launcher  # noqa: E402


# TC-1
def test_tc_01_spawn_prompt_is_mode_neutral_boot_trigger(monkeypatch):
    # Bypass the #8692 singleton check (this very session holds the role's
    # .claude-pid lock — without this, main() refuses to spawn).
    monkeypatch.setattr(thin_launcher, "_check_singleton", lambda cp, r: None)
    # Skip the post-spawn pid file write so we don't trample the live agent.
    monkeypatch.setattr(thin_launcher, "_write_pid", lambda *a, **k: None)
    monkeypatch.setattr(thin_launcher, "_clear_pid", lambda *a, **k: None)
    captured = {}

    class FakeProc:
        pid = 12345
        def poll(self):
            return 0
        def wait(self, timeout=None):
            return 0
        def send_signal(self, sig):
            pass

    def fake_popen(cmd, *args, **kwargs):
        captured["cmd"] = list(cmd)
        return FakeProc()

    monkeypatch.setattr(thin_launcher.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(thin_launcher.shutil, "which", lambda x: "/fake/claude")
    monkeypatch.setattr(thin_launcher, "_is_process_alive", lambda pid: True)
    # Use a role that does NOT match the running session's .claude-pid singleton
    # in case the bypass above is somehow incomplete.
    monkeypatch.setattr(sys, "argv", ["thin_launcher.py", "skill"])
    monkeypatch.setattr(thin_launcher.os, "chdir", lambda p: None)

    try:
        thin_launcher.main()
    except SystemExit:
        pass

    cmd = captured.get("cmd", [])
    assert cmd, "thin_launcher.main did not invoke subprocess.Popen"
    last = cmd[-1]
    # #11512: last positional is the mode-neutral boot trigger, not a /loop cmd.
    assert last == thin_launcher._SPAWN_PROMPT
    assert not any(
        isinstance(a, str) and a.startswith("/loop") for a in cmd
    ), f"spawn command must not force loop mode; got {cmd!r}"
    # Defensive: old hard-imperative prompt must not appear anywhere
    assert "Boot. Begin your first Ralph Loop cycle now." not in " ".join(cmd), (
        "Old pre-#9725 spawn prompt leaked into the command"
    )
    # _get_interval was removed with the /loop prompt (#11512).
    assert not hasattr(thin_launcher, "_get_interval")


# TC-5
def test_tc_05_dev_thin_launcher_suite_green():
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short",
         str(REPO_ROOT / "tests" / "test_thin_launcher.py")],
        cwd=str(REPO_ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    assert r.returncode == 0, (
        f"test_thin_launcher.py failed:\n{r.stdout}\n{r.stderr}"
    )


# TC-6
def test_tc_06_running_clone_shows_loop_evidence_in_git_log():
    """Structural smoke: this very QA session was spawned via the new spawn
    prompt and has been cycling. Inspect git log on origin/main for QA cycle
    commits matching the standard `qa: cycle <N>` pattern. Pre-#9725 stalled
    agents produced zero cycle commits between reboots; post-#9725 each cycle
    fires reliably.
    """
    r = subprocess.run(
        ["git", "log", "origin/main", "--oneline", "-50",
         "--grep", "^qa: cycle \\(state\\|[0-9]\\+\\)"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
    )
    if r.returncode != 0:
        pytest.skip(f"git log unavailable: {r.stderr}")
    lines = [ln for ln in r.stdout.splitlines() if ln.strip()]
    assert len(lines) >= 3, (
        f"Expected ≥3 recent `qa: cycle …` commits on origin/main as "
        f"evidence of reliable /loop cycling under #9725; found "
        f"{len(lines)}: {lines[:5]}"
    )
