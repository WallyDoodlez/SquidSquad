"""#13323 — INDEPENDENT verifier regression guard (QA).

Docstring-only fix: after #13318 moved the launcher to `.squidsquad/start.sh`, two
wizard.py docstrings still said the old repo-root `./start.sh`. No behavioral surface
(functional `cold_start_cmd` was already correct), so the guard is a source-text
assertion that the stale prose does not return.

AC map (from the #13323 issue body "Suggested fix"):
  AC1  the two wizard.py docstring/comment refs say `.squidsquad/start.sh`
  AC2  no bare `./start.sh` remains anywhere in wizard.py
  AC3  the functional cold_start_cmd is unchanged (`.squidsquad/start.sh`)
"""
import os
import re

WIZARD = os.path.join(
    os.path.dirname(__file__), "..", "references", "scripts", "wizard.py"
)


def _text():
    with open(WIZARD, encoding="utf-8") as f:
        return f.read()


def test_no_bare_repo_root_start_sh_in_wizard():
    """AC2: no bare './start.sh' token survives (docstrings were the last holdouts).

    Matches './start.sh' NOT preceded by '.squidsquad/' — so '.squidsquad/start.sh'
    never trips it."""
    text = _text()
    stale = [
        m.start() for m in re.finditer(r"\./start\.sh", text)
        if not text[max(0, m.start() - 11):m.start()].endswith(".squidsquad/")
    ]
    assert not stale, f"bare './start.sh' still present at offsets {stale}"


def test_functional_cold_start_cmd_correct():
    """AC3: the functional emitted command is the migrated path."""
    assert '"cold_start_cmd": ".squidsquad/start.sh"' in _text()


def test_docstrings_reference_migrated_path():
    """AC1: the migrated path appears in the restart docstrings region."""
    text = _text()
    assert text.count(".squidsquad/start.sh") >= 3, (
        "expected the migrated path in both docstrings + the functional dict"
    )
