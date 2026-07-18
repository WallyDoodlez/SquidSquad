"""Comprehension tests for #4792 — sentinel cleanup, agent liveness model, operator entry point."""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "tests" / "comprehension" / "4792_spec.json"


@pytest.fixture(scope="module")
def comprehension_results(tmp_path_factory):
    """Run the comprehension pipeline once; SKIP (not FAIL) if the claude CLI is
    absent/unusable or the run is cache-hit — shared gate, #12748."""
    from comprehension_helpers import run_comprehension_or_skip
    return run_comprehension_or_skip(
        SPEC, tmp_path_factory.mktemp("comprehension"))


def _get(results, qid):
    return next((r for r in results if str(r.get("id")) == str(qid)), None)


class TestComprehension4792:
    """Live-agent CQ tests — require the `claude` CLI. Skip otherwise.

    Static hygiene checks for the same #4792 fragments live in
    `tests/test_4792_fragment_hygiene.py` and run in the regular suite.
    """

    def test_all_answered(self, comprehension_results):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        assert {str(q["id"]) for q in spec["questions"]} == {
            str(r["id"]) for r in comprehension_results
        }

    def test_q1_agent_liveness_model(self, comprehension_results):
        r = _get(comprehension_results, "1")
        assert r and r["pass"], f"Q-1: {r.get('reason')}"

    def test_q2_canonical_operator_entry_point(self, comprehension_results):
        r = _get(comprehension_results, "2")
        assert r and r["pass"], f"Q-2: {r.get('reason')}"
