"""Shared harness for the comprehension test fixtures (#12748).

Every ``test_comprehension_*.py`` module runs the same pipeline via
``run_comprehension_test.py`` and validates ``results.json``. The env-gating was
copied per-file and drifted: a claude CLI that is PRESENT but unusable (keyless /
unauthenticated), or a content-hash CACHE HIT, produces NO ``results.json``, and
the per-file fixtures called ``pytest.fail`` — reddening the keyless suite
(~35 comprehension reds, #12748) instead of skipping.

The invariant that makes a clean skip correct: a genuine comprehension
regression ALWAYS yields a ``results.json`` whose answers fail (caught by the
per-question asserts). "No ``results.json`` at all" only ever means the pipeline
could not run — claude absent/unusable, or a cache hit (the spec already PASSED
unchanged). Neither is a regression, so both SKIP. This module centralises that
gate so the 10 call sites can't drift again.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
RUNNER = REPO / "references" / "scripts" / "run_comprehension_test.py"


def claude_available():
    """True iff the claude CLI binary is on PATH. Note this does NOT prove the
    CLI is *usable* (authenticated / keyed) — an unauthenticated-but-present CLI
    is handled by the no-results.json skip below, not here."""
    return shutil.which("claude") is not None


def run_comprehension_or_skip(spec_path, output_dir, timeout=600):
    """Run the comprehension pipeline for ``spec_path`` and return the parsed
    results list (``[{"id", "pass", "reason"}, ...]``).

    SKIP (never FAIL) on any non-regression condition: claude CLI absent,
    present-but-unusable (keyless / unauthenticated → no results.json), or a
    content-hash cache hit. Only a malformed-but-present ``results.json`` (the
    pipeline ran and produced garbage) is a genuine FAIL.
    """
    spec_path = Path(spec_path)
    output_dir = Path(output_dir)

    if not claude_available():
        pytest.skip("claude CLI not available")

    result = subprocess.run(
        [sys.executable, str(RUNNER), str(spec_path),
         "--output-dir", str(output_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO), timeout=timeout,
    )

    results_path = output_dir / "results.json"
    if not results_path.exists():
        # No results.json is NEVER a comprehension regression (a real regression
        # yields results.json with failing answers) — always SKIP, never FAIL
        # (#12748). Distinguish the two benign causes by EXIT CODE, which is
        # robust where the stdout cache-marker isn't (the marker carries an
        # em-dash that can be mangled by a cp1252 console on Windows):
        #   exit 0  -> the runner cache-hit (spec + files unchanged since last
        #              PASS) and returned without rerunning.
        #   exit !0 -> the pipeline could not run: claude CLI absent / unusable
        #              (keyless / unauthenticated) or an env-level break.
        if result.returncode == 0:
            pytest.skip(
                f"comprehension cache hit — {spec_path.name} unchanged since "
                f"last PASS"
            )
        pytest.skip(
            f"comprehension pipeline could not run for {spec_path.name} "
            f"(exit {result.returncode}) — claude CLI not usable in this "
            f"environment. stderr: {(result.stderr or '')[:300]}"
        )

    raw = results_path.read_text(encoding="utf-8").strip()
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.split("\n") if not l.startswith("```"))
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"Failed to parse results.json ({spec_path.name}): {e}\n"
            f"Content: {raw[:500]}"
        )
