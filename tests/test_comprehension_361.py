"""Comprehension tests for #361 — project-adaptive role souls."""

import json
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "tests" / "comprehension" / "361_spec.json"

@pytest.fixture(scope="module")
def comprehension_results(tmp_path_factory):
    """Run the comprehension pipeline once; SKIP (not FAIL) if the claude CLI is
    absent/unusable or the run is cache-hit — shared gate, #12748."""
    from comprehension_helpers import run_comprehension_or_skip
    return run_comprehension_or_skip(
        SPEC, tmp_path_factory.mktemp("comprehension"))


def _get(results, qid):
    return next((r for r in results if str(r.get("id")) == str(qid)), None)

class TestComprehension361:
    def test_all_answered(self, comprehension_results):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        assert {str(q["id"]) for q in spec["questions"]} == {str(r["id"]) for r in comprehension_results}
    def test_q1_new_signal(self, comprehension_results):
        r = _get(comprehension_results, "1"); assert r and r["pass"], f"Q-1: {r.get('reason')}"
    def test_q2_contradiction(self, comprehension_results):
        r = _get(comprehension_results, "2"); assert r and r["pass"], f"Q-2: {r.get('reason')}"
    def test_q3_cap_consolidation(self, comprehension_results):
        r = _get(comprehension_results, "3"); assert r and r["pass"], f"Q-3: {r.get('reason')}"
