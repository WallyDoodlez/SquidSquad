"""Comprehension tests for #1428 — deterministic QA verification framework.

Runs the comprehension test pipeline: spawns test + eval agents via claude CLI,
then asserts all questions pass based on the structured results.json.

Requires claude CLI in PATH. Skipped if not available.
"""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "tests" / "comprehension" / "1428_spec.json"


@pytest.fixture(scope="module")
def comprehension_results(tmp_path_factory):
    """Run the comprehension pipeline once; SKIP (not FAIL) if the claude CLI is
    absent/unusable or the run is cache-hit — shared gate, #12748."""
    from comprehension_helpers import run_comprehension_or_skip
    return run_comprehension_or_skip(
        SPEC, tmp_path_factory.mktemp("comprehension"))


def _get_result(results, question_id):
    """Find a specific question result by ID."""
    for r in results:
        if str(r.get("id")) == str(question_id):
            return r
    return None


class TestComprehension1428:
    """All 5 comprehension questions for #1428 must pass."""

    def test_all_questions_answered(self, comprehension_results):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        expected_ids = {str(q["id"]) for q in spec["questions"]}
        actual_ids = {str(r["id"]) for r in comprehension_results}
        assert expected_ids == actual_ids, (
            f"Missing answers for: {expected_ids - actual_ids}"
        )

    def test_q1_blocked_not_defer_for_missing_api_key(self, comprehension_results):
        r = _get_result(comprehension_results, "1")
        assert r is not None, "Q-1 result not found"
        assert r["pass"], f"Q-1 FAIL: {r.get('reason', 'no reason')}"

    def test_q2_zero_gap_gate_on_tc_failure(self, comprehension_results):
        r = _get_result(comprehension_results, "2")
        assert r is not None, "Q-2 result not found"
        assert r["pass"], f"Q-2 FAIL: {r.get('reason', 'no reason')}"

    def test_q3_human_verification_routing(self, comprehension_results):
        r = _get_result(comprehension_results, "3")
        assert r is not None, "Q-3 result not found"
        assert r["pass"], f"Q-3 FAIL: {r.get('reason', 'no reason')}"

    def test_q4_blocked_gate_absolute(self, comprehension_results):
        r = _get_result(comprehension_results, "4")
        assert r is not None, "Q-4 result not found"
        assert r["pass"], f"Q-4 FAIL: {r.get('reason', 'no reason')}"

    def test_q5_unlabeled_tc_is_a_gap(self, comprehension_results):
        r = _get_result(comprehension_results, "5")
        assert r is not None, "Q-5 result not found"
        assert r["pass"], f"Q-5 FAIL: {r.get('reason', 'no reason')}"
