"""Live-system pytest for #9747 — eliminate [ROLE] placeholder in dev polling fragment.

AC: "Either polling fragments no longer contain placeholders needing runtime
LLM substitution, OR documented as accepted technical debt with a follow-up
issue." PR took option (a): eliminate the placeholder via a script helper
that reads SQUIDSQUAD_ROLE.

TC mapping:
  TC-1 → polling fragments have ZERO [ROLE] placeholders (dev + pm + qa + dm)
  TC-2 → cycle.py exposes `status-bar-self` subcommand
  TC-3 → status_bar_self() reads SQUIDSQUAD_ROLE env and writes current-state
  TC-4 → status_bar_self() fails loudly when SQUIDSQUAD_ROLE is missing/empty
  TC-5 → dev's tests/test_cycle.py 24/24 PASS
"""

from __future__ import annotations

import os
import re
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
SUB_SKILLS = REPO_ROOT / "references" / "sub-skills"

sys.path.insert(0, str(SCRIPTS_DIR))
import cycle  # noqa: E402


# TC-1
@pytest.mark.parametrize("role", ["dev", "pm", "qa", "dm"])
def test_tc_01_polling_fragment_has_no_role_placeholder(role):
    text = (SUB_SKILLS / "roles" / role / "ralph-loop-overview.md").read_text(
        encoding="utf-8"
    )
    assert "[ROLE]" not in text, (
        f"{role}/ralph-loop-overview.md still contains a [ROLE] placeholder; "
        f"#9747 requires elimination via the cycle.py status-bar-self helper "
        f"or equivalent."
    )


# TC-2
def test_tc_02_cycle_py_exposes_status_bar_self_subcommand():
    r = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "cycle.py"), "--help"],
        capture_output=True, text=True, timeout=30,
    )
    # Command should be listed in the help/docstring
    assert "status-bar-self" in (r.stdout + r.stderr), (
        "cycle.py --help does not advertise the status-bar-self subcommand"
    )
    # And the function exists
    assert callable(getattr(cycle, "status_bar_self", None)), (
        "cycle.py is missing the status_bar_self function"
    )


# TC-3
def test_tc_03_status_bar_self_uses_env_role_and_writes_current_state(
    monkeypatch, tmp_path
):
    role = "qa"
    monkeypatch.setenv("SQUIDSQUAD_ROLE", role)
    # status_bar() (which status_bar_self delegates to) writes under
    # SQUIDSQUAD_DIR / role. Redirect that to tmp.
    monkeypatch.setattr(cycle, "SQUIDSQUAD_DIR", tmp_path)
    (tmp_path / role).mkdir(parents=True, exist_ok=True)
    cycle.status_bar_self("testing", "qa-verify-9747")
    state = (tmp_path / role / "current-state").read_text(encoding="utf-8")
    assert "testing" in state
    assert "qa-verify-9747" in state


# TC-4
def test_tc_04_status_bar_self_fails_loudly_on_missing_env(monkeypatch):
    monkeypatch.delenv("SQUIDSQUAD_ROLE", raising=False)
    with pytest.raises(SystemExit) as exc:
        cycle.status_bar_self("idle", "no-env")
    assert exc.value.code != 0, (
        "status_bar_self must exit non-zero when SQUIDSQUAD_ROLE is missing"
    )

    # Also empty / whitespace
    monkeypatch.setenv("SQUIDSQUAD_ROLE", "   ")
    with pytest.raises(SystemExit) as exc:
        cycle.status_bar_self("idle", "whitespace-env")
    assert exc.value.code != 0


# TC-5
def test_tc_05_dev_cycle_suite_green():
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short",
         str(REPO_ROOT / "tests" / "test_cycle.py")],
        cwd=str(REPO_ROOT),
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=120,
    )
    assert r.returncode == 0, (
        f"test_cycle.py failed:\n{r.stdout}\n{r.stderr}"
    )
