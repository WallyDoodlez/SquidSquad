"""Comprehension tests for #4792 — sentinel cleanup, sole liveness signal, operator entry point."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "tests" / "comprehension" / "4792_spec.json"
RUNNER = REPO / "references" / "scripts" / "run_comprehension_test.py"


@pytest.fixture(scope="module")
def comprehension_results(tmp_path_factory):
    if not shutil.which("claude"):
        pytest.skip("claude CLI not available")
    output_dir = tmp_path_factory.mktemp("comprehension-4792")
    result = subprocess.run(
        [sys.executable, str(RUNNER), str(SPEC), "--output-dir", str(output_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO), timeout=600,
    )
    results_path = output_dir / "results.json"
    if not results_path.exists():
        pytest.fail(
            f"No results.json.\nstdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
        )
    raw = results_path.read_text(encoding="utf-8").strip()
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.split("\n") if not l.startswith("```"))
    return json.loads(raw)


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

    def test_q1_sole_liveness_signal(self, comprehension_results):
        r = _get(comprehension_results, "1")
        assert r and r["pass"], f"Q-1: {r.get('reason')}"

    def test_q2_canonical_operator_entry_point(self, comprehension_results):
        r = _get(comprehension_results, "2")
        assert r and r["pass"], f"Q-2: {r.get('reason')}"
