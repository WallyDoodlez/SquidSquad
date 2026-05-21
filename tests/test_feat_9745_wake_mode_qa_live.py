"""Live-system pytest for #9745 — consolidate wake-mode resolution.

AC:
  - Single shared implementation
  - All three Python callers import from the shared location
  - Bootstrap prose verified against the code via test
"""

from __future__ import annotations

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
SCRIPTS = REPO_ROOT / "references" / "scripts"
SUB_SKILLS = REPO_ROOT / "references" / "sub-skills"

sys.path.insert(0, str(SCRIPTS))
import config  # noqa: E402


# TC-1
def test_tc_01_config_get_wake_mode_is_canonical():
    assert callable(getattr(config, "get_wake_mode", None)), (
        "config.get_wake_mode missing — canonical resolver not present"
    )


# TC-2
@pytest.mark.parametrize("path", [
    "compose.py",
    "cycle_post.py",
    "statusline_data.py",
])
def test_tc_02_caller_delegates_to_config_get_wake_mode(path):
    src = (SCRIPTS / path).read_text(encoding="utf-8")
    assert "from config import get_wake_mode" in src or \
           "config.get_wake_mode" in src, (
        f"{path} does not delegate to config.get_wake_mode — duplication "
        f"persists, AC unmet."
    )


# TC-3
@pytest.mark.parametrize("path", [
    "compose.py",
    "cycle_post.py",
    "statusline_data.py",
])
def test_tc_03_caller_has_no_inline_field_probe(path):
    """The three callers used to duplicate the resolution rules (probe
    event-driven-<role>, then event-driven, then default). After #9745,
    the inline probe must be gone — only the delegating wrapper remains.
    """
    src = (SCRIPTS / path).read_text(encoding="utf-8")
    # The hallmark of the duplicated logic was iterating both candidate
    # field names in a single function. If both field names appear inside
    # the SAME function body, the duplicate logic is still there.
    # Use a coarse heuristic: the candidate-field tuple
    #   ("event-driven-{role}", "event-driven")
    # only appears in the canonical config.get_wake_mode after #9745.
    if "event-driven-" in src and "event-driven\"" in src and \
       "for field in" in src:
        # Likely the inline tuple iteration. Confirm it's not in a comment.
        # Allow it iff the only `event-driven` mention is in a delegation
        # docstring (compose/cycle_post mention it for documentation).
        # Strict check: look for a loop over field candidates.
        assert not re.search(
            r'for field in \(.*event-driven-.*, *"event-driven"\)', src
        ), (
            f"{path} still iterates the field candidate tuple inline — "
            f"resolution rules duplicated."
        )


# TC-4
def test_tc_04_bootstrap_prose_matches_config_docstring():
    """The bootstrap fragment describes the same resolution rules in prose.
    Audit: ensure both the bootstrap and config.get_wake_mode mention the
    same key facts (per-role override → global default → polling fallback).
    """
    boot = (SUB_SKILLS / "common" / "boot-bootstrap.md").read_text(encoding="utf-8")
    cfg_src = (SCRIPTS / "config.py").read_text(encoding="utf-8")
    cfg_fn_start = cfg_src.find("def get_wake_mode(")
    assert cfg_fn_start != -1, "config.get_wake_mode missing"
    # Slice the function body up to ~600 bytes — docstring + key logic.
    cfg_excerpt = cfg_src[cfg_fn_start:cfg_fn_start + 2500]

    # Key facts both must mention.
    for fact, where in (
        ("event-driven-", boot),   # per-role override mention in prose
        ("event-driven-", cfg_excerpt),  # ditto in canonical code
        ("event-driven", boot),
        ("event-driven", cfg_excerpt),
        ("polling", boot),
        ("polling", cfg_excerpt),
    ):
        assert fact in where, (
            f"Audit fail: {fact!r} not present in expected source — "
            f"prose/code drift between bootstrap and config.get_wake_mode"
        )


# TC-5
def test_tc_05_resolution_behavior_per_role_override(monkeypatch):
    """Behavioral: per-role override takes precedence over global default."""
    # Patch config.get_field to mimic config.md contents
    def fake(field):
        if field == "event-driven-skill":
            return "yes"
        if field == "event-driven":
            return "no"
        raise SystemExit(1)
    monkeypatch.setattr(config, "get_field", fake)
    assert config.get_wake_mode("skill") == "event-driven"


def test_tc_05b_resolution_behavior_global_fallback(monkeypatch):
    def fake(field):
        if field == "event-driven":
            return "yes"
        raise SystemExit(1)
    monkeypatch.setattr(config, "get_field", fake)
    assert config.get_wake_mode("qa") == "event-driven"


def test_tc_05c_resolution_behavior_default_polling(monkeypatch):
    def fake(field):
        raise SystemExit(1)
    monkeypatch.setattr(config, "get_field", fake)
    assert config.get_wake_mode("dm") == "polling"


# TC-6
def test_tc_06_dev_suites_green():
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "--tb=short",
         str(REPO_ROOT / "tests" / "test_feat_9745_wake_mode_canonical.py"),
         str(REPO_ROOT / "tests" / "test_compose.py"),
         str(REPO_ROOT / "tests" / "test_statusline_data.py")],
        cwd=str(REPO_ROOT),
        capture_output=True, encoding="utf-8", errors="replace",
        timeout=180,
    )
    assert r.returncode == 0, (
        f"Dev suites failed:\n{r.stdout}\n{r.stderr}"
    )
