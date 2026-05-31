"""Verifier-owned executable tests for #10348 (health_check SystemExit catch).

Derived from .squidsquad/qa/planning/TEST-PLAN-10348.md, which was derived
from the issue body (Recommendation + "Out of scope but observed" cleanup)
— NOT from the worker's PR diff.

Run: python -m pytest .squidsquad/qa/planning/TEST-10348-tests.py -v
"""

import ast
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import health_check  # noqa: E402


# --- TC-1 ------------------------------------------------------------------


def test_tc_01_system_exit_returns_default():
    """AC-1: SystemExit from config.get_field -> returns the documented 30."""
    with patch("config.get_field", side_effect=SystemExit(1)):
        assert health_check._read_interval() == 30


# --- TC-2 ------------------------------------------------------------------


def test_tc_02_live_no_exit_1_on_missing_interval(tmp_path):
    """AC-1: live-system reproduction — running health_check.py against a
    config.md that lacks `Iteration Interval > Minutes` must not exit 1
    with `ERROR: Field 'interval' not found`. Before the fix this was the
    documented bug; after the fix the script should fall through to the
    30-minute default and exit on a documented code (0 healthy / 2 unknown).
    """
    (tmp_path / ".squidsquad").mkdir()
    # config.md without `Iteration Interval > Minutes` field — but with the
    # minimum SquidSquad Version field so other parsers don't blow up.
    (tmp_path / ".squidsquad" / "config.md").write_text(
        "# SquidSquad Config\n\n- **SquidSquad Version**: 0.0.1\n",
        encoding="utf-8",
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "health_check.py")],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    assert result.returncode != 1 or "Field 'interval' not found" not in result.stderr, (
        f"Pre-fix bug reproduced — exit 1 with missing-interval error.\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )


# --- TC-3 ------------------------------------------------------------------


def test_tc_03_value_error_still_returns_default():
    """AC-2: ValueError still returns 30 (no regression of pre-existing catch)."""
    with patch("config.get_field", side_effect=ValueError("bad")):
        assert health_check._read_interval() == 30


# --- TC-4 ------------------------------------------------------------------


def test_tc_04_keyboard_interrupt_propagates():
    """AC-3: KeyboardInterrupt must NOT be swallowed — Ctrl+C aborts."""
    with patch("config.get_field", side_effect=KeyboardInterrupt):
        with pytest.raises(KeyboardInterrupt):
            health_check._read_interval()


# --- TC-5 ------------------------------------------------------------------


def test_tc_05_dead_imports_dropped():
    """AC-4: `os`, `platform`, `subprocess` must not be top-level imports."""
    src = (SCRIPTS / "health_check.py").read_text(encoding="utf-8")
    tree = ast.parse(src)
    top_imports = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top_imports.add(node.module.split(".")[0])
    forbidden = {"os", "platform", "subprocess"}
    leaked = forbidden & top_imports
    assert not leaked, (
        f"AC-4: dead imports still present at module top level: {sorted(leaked)}"
    )


# --- TC-6 ------------------------------------------------------------------


def test_tc_06_worker_regression_suite_passes():
    """AC-1 + AC-3 cross-check via worker's own suite."""
    test_file = REPO_ROOT / "tests" / "test_health_check.py"
    assert test_file.exists(), f"{test_file} missing"
    result = subprocess.run(
        [sys.executable, "-m", "pytest", str(test_file), "-v", "--tb=short"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"Worker regression suite must pass.\nSTDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )
    # Both named regression tests must be in the collected run
    assert "test_system_exit_returns_default" in result.stdout
    assert "test_keyboard_interrupt_propagates" in result.stdout
