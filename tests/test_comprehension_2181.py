"""Comprehension tests for #2181 — DM delivery enables feature flags.

Runs the comprehension test pipeline: spawns test + eval agents via claude CLI,
then asserts all questions pass based on the structured results.json.

Requires claude CLI in PATH. Skipped if not available.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "tests" / "comprehension" / "2181_spec.json"
RUNNER = REPO / "references" / "scripts" / "run_comprehension_test.py"


def _claude_available():
    """Check if claude CLI is available."""
    import shutil
    return shutil.which("claude") is not None


@pytest.fixture(scope="module")
def comprehension_results(tmp_path_factory):
    """Run the comprehension pipeline once and return parsed results."""
    if not _claude_available():
        pytest.skip("claude CLI not available")

    output_dir = tmp_path_factory.mktemp("comprehension-2181")
    result = subprocess.run(
        [sys.executable, str(RUNNER), str(SPEC), "--output-dir", str(output_dir)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(REPO),
        timeout=600,
    )

    results_path = output_dir / "results.json"
    if not results_path.exists():
        pytest.fail(
            f"Comprehension pipeline did not produce results.json.\n"
            f"stdout: {result.stdout[:1000]}\n"
            f"stderr: {result.stderr[:1000]}"
        )

    raw = results_path.read_text(encoding="utf-8").strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(l for l in lines if not l.startswith("```"))

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        pytest.fail(f"Failed to parse results.json: {e}\nContent: {raw[:500]}")


def _get_result(results, question_id):
    """Find a specific question result by ID."""
    for r in results:
        if str(r.get("id")) == str(question_id):
            return r
    return None


class TestComprehension2181:
    """All 3 comprehension questions for #2181 must pass."""

    def test_all_questions_answered(self, comprehension_results):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        expected_ids = {str(q["id"]) for q in spec["questions"]}
        actual_ids = {str(r["id"]) for r in comprehension_results}
        assert expected_ids == actual_ids, (
            f"Missing answers for: {expected_ids - actual_ids}"
        )

    def test_q1_enable_flag_on_shipping_project(self, comprehension_results):
        r = _get_result(comprehension_results, "1")
        assert r is not None, "Q-1 result not found"
        assert r["pass"], f"Q-1 FAIL: {r.get('reason', 'no reason')}"

    def test_q2_flag_detection_method(self, comprehension_results):
        r = _get_result(comprehension_results, "2")
        assert r is not None, "Q-2 result not found"
        assert r["pass"], f"Q-2 FAIL: {r.get('reason', 'no reason')}"

    def test_q3_no_flag_skip(self, comprehension_results):
        r = _get_result(comprehension_results, "3")
        assert r is not None, "Q-3 result not found"
        assert r["pass"], f"Q-3 FAIL: {r.get('reason', 'no reason')}"
