"""Live-system pytest for #9745 — consolidate wake-mode resolution.

AC (original #9745):
  - Single shared implementation (config.get_wake_mode is canonical)
  - Live callers import from the shared location
  - Dev suites green

RECONCILED #13163 (2026-06-21): #9745 consolidated wake-mode under the
config-field-driven model; #11401 then replaced that model with a HARNESS PROBE
(AGENT-RUNTIME §9.3) — no `event-driven:` config field, `boot-bootstrap.md`
removed, `get_wake_mode` no longer reads `config.get_field`. The config-field
behavioral/prose tests (old TC-4/TC-5/TC-5b/TC-5c) asserted that retired model
and failed unconditionally; they are retired here. Current probe behavior is
covered by `test_feat_9745_wake_mode_canonical.py` (re-run by TC-6). TC-2/TC-3
are narrowed to statusline_data.py, the sole remaining wake-mode delegator.
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

sys.path.insert(0, str(SCRIPTS))
import config  # noqa: E402


# TC-1
def test_tc_01_config_get_wake_mode_is_canonical():
    assert callable(getattr(config, "get_wake_mode", None)), (
        "config.get_wake_mode missing — canonical resolver not present"
    )


# TC-2
# Post-#11401 only statusline_data.py still resolves wake mode (compose._get_wake_mode
# was retired in E6/#10685; cycle_post.py no longer needs it). statusline_data.py
# remains the single live delegator to the canonical config.get_wake_mode (#13163).
@pytest.mark.parametrize("path", [
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


# TC-4, TC-5, TC-5b, TC-5c RETIRED (#13163): these asserted the PRE-#11401
# config-field-driven resolution model — `config.get_wake_mode` reading
# `event-driven[-<role>]` from config.md, and a `boot-bootstrap.md` fragment
# documenting those rules. #11401 replaced that model entirely: wake mode is now
# resolved by a HARNESS PROBE at agent boot (AGENT-RUNTIME §9.3) — there is no
# `event-driven:` config field, `boot-bootstrap.md` was removed, and
# `get_wake_mode` no longer reads `config.get_field`. The current probe behavior
# is covered by `tests/test_feat_9745_wake_mode_canonical.py` (which TC-6 below
# re-runs). The retired tests failed unconditionally (deleted-file read +
# config-field assertions against a probe) — pure stale-test noise, not coverage.


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
