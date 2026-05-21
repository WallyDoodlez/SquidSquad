"""Live-system pytest for #9746 — regenerate agent-instructions.md + drift detection.

AC: (1) references/agent-instructions.md regenerated and committed.
    (2) CI check / pre-commit hook preventing future drift.

This QA file complements dev's tests/test_feat_9746_agent_instructions_drift.py by
adding live-system structural assertions:
  TC-1 → agent-instructions.md exists on disk and is non-trivial
  TC-2 → agent-instructions.md matches a fresh compose.compose_all() output
  TC-3 → agent-instructions.md has the post-#9588 boot-bootstrap section
  TC-4 → agent-instructions.md has no stale pre-#9588 inline ralph-loop-overview marker
  TC-5 → agent-instructions.md has no pre-#9478 branch-workflow vestiges
  TC-6 → dev's drift test exists at the documented path
  TC-7 → dev's drift test is discoverable by plain `pytest tests/` invocation
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
CANONICAL = REPO_ROOT / "references" / "agent-instructions.md"
SCRIPTS_DIR = REPO_ROOT / "references" / "scripts"
DRIFT_TEST = REPO_ROOT / "tests" / "test_feat_9746_agent_instructions_drift.py"

sys.path.insert(0, str(SCRIPTS_DIR))
import compose  # noqa: E402


# TC-1
def test_tc_01_canonical_exists_and_non_trivial():
    assert CANONICAL.exists(), f"{CANONICAL} not regenerated"
    text = CANONICAL.read_text(encoding="utf-8")
    assert len(text.splitlines()) > 500, (
        f"agent-instructions.md unexpectedly short ({len(text.splitlines())} lines) "
        f"— compose.py all probably failed silently"
    )


# TC-2
def test_tc_02_canonical_matches_fresh_compose():
    fresh = compose.compose_all()
    on_disk = CANONICAL.read_text(encoding="utf-8")
    assert fresh == on_disk, (
        "references/agent-instructions.md drifted from fresh compose_all() — "
        "regenerate via `python references/scripts/compose.py all`"
    )


# TC-3
def test_tc_03_has_boot_bootstrap_section():
    text = CANONICAL.read_text(encoding="utf-8")
    assert "<!-- sub-skill: boot-bootstrap -->" in text, (
        "agent-instructions.md missing boot-bootstrap sub-skill (#9588 regression)"
    )
    assert "## Boot — Mode Detection (#9588)" in text, (
        "agent-instructions.md missing the bootstrap heading"
    )


# TC-4
def test_tc_04_no_stale_inline_ralph_loop_overview():
    text = CANONICAL.read_text(encoding="utf-8")
    # The wrapper marker would only appear if compose inlined the fragment.
    assert "<!-- sub-skill: ralph-loop-overview -->" not in text, (
        "agent-instructions.md inlines ralph-loop-overview — pre-#9588 stale content"
    )


# TC-5
def test_tc_05_no_branch_workflow_vestiges():
    """#9478 removed branch_workflow; canonical must not bring it back."""
    lower = CANONICAL.read_text(encoding="utf-8").lower()
    for token in ("branch-workflow", "branch workflow", "branch_workflow"):
        assert token not in lower, (
            f"agent-instructions.md contains pre-#9478 token {token!r}"
        )


# TC-6
def test_tc_06_drift_test_exists():
    assert DRIFT_TEST.exists(), (
        f"AC-2 unsatisfied: drift test missing at {DRIFT_TEST}"
    )


# TC-7
def test_tc_07_drift_test_runs_green_under_plain_pytest():
    """The 'CI check' in AC-2 must run under the standard pytest invocation
    used by humans + future CI. Plain `pytest tests/test_feat_9746_*.py`
    discovers it via default pattern matching and must pass.
    """
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short", str(DRIFT_TEST)],
        cwd=str(REPO_ROOT),
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=120,
    )
    assert r.returncode == 0, (
        f"Drift test failed under plain pytest:\n{r.stdout}\n{r.stderr}"
    )
