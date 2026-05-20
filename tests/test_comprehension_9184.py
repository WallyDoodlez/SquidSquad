"""Comprehension tests for #9184 — restructure planning + verification.

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
SPEC = REPO / "tests" / "comprehension" / "9184_spec.json"
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

    output_dir = tmp_path_factory.mktemp("comprehension-9184")
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


class TestComprehension9184:
    """All 7 comprehension questions for #9184 must pass."""

    def test_all_questions_answered(self, comprehension_results):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        expected_ids = {str(q["id"]) for q in spec["questions"]}
        actual_ids = {str(r["id"]) for r in comprehension_results}
        assert expected_ids == actual_ids, (
            f"Missing answers for: {expected_ids - actual_ids}"
        )

    def test_q1_pm_produces_no_test_plan(self, comprehension_results):
        r = _get_result(comprehension_results, "1")
        assert r is not None, "Q-1 result not found"
        assert r["pass"], f"Q-1 FAIL: {r.get('reason', 'no reason')}"

    def test_q2_ac_list_lives_in_issue_body_and_context(self, comprehension_results):
        r = _get_result(comprehension_results, "2")
        assert r is not None, "Q-2 result not found"
        assert r["pass"], f"Q-2 FAIL: {r.get('reason', 'no reason')}"

    def test_q3_qa_writes_test_plan_under_qa_planning(self, comprehension_results):
        r = _get_result(comprehension_results, "3")
        assert r is not None, "Q-3 result not found"
        assert r["pass"], f"Q-3 FAIL: {r.get('reason', 'no reason')}"

    def test_q4_qa_owns_cq_specs(self, comprehension_results):
        r = _get_result(comprehension_results, "4")
        assert r is not None, "Q-4 result not found"
        assert r["pass"], f"Q-4 FAIL: {r.get('reason', 'no reason')}"

    def test_q5_dev_writes_unit_tests_same_pr(self, comprehension_results):
        r = _get_result(comprehension_results, "5")
        assert r is not None, "Q-5 result not found"
        assert r["pass"], f"Q-5 FAIL: {r.get('reason', 'no reason')}"

    def test_q6_qa_executes_against_live_system(self, comprehension_results):
        r = _get_result(comprehension_results, "6")
        assert r is not None, "Q-6 result not found"
        assert r["pass"], f"Q-6 FAIL: {r.get('reason', 'no reason')}"

    def test_q7_ac_walk_path_resolution(self, comprehension_results):
        r = _get_result(comprehension_results, "7")
        assert r is not None, "Q-7 result not found"
        assert r["pass"], f"Q-7 FAIL: {r.get('reason', 'no reason')}"
