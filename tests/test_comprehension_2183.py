"""Comprehension tests for #2183 — simplified agent lifecycle."""

import json, subprocess, sys, shutil
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "tests" / "comprehension" / "2183_spec.json"
RUNNER = REPO / "references" / "scripts" / "run_comprehension_test.py"

@pytest.fixture(scope="module")
def comprehension_results(tmp_path_factory):
    if not shutil.which("claude"):
        pytest.skip("claude CLI not available")
    output_dir = tmp_path_factory.mktemp("comprehension-2183")
    result = subprocess.run(
        [sys.executable, str(RUNNER), str(SPEC), "--output-dir", str(output_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO), timeout=600)
    results_path = output_dir / "results.json"
    if not results_path.exists():
        pytest.fail(f"No results.json.\nstdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}")
    raw = results_path.read_text(encoding="utf-8").strip()
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.split("\n") if not l.startswith("```"))
    return json.loads(raw)

def _get(results, qid):
    return next((r for r in results if str(r.get("id")) == str(qid)), None)

class TestComprehension2183:
    def test_all_answered(self, comprehension_results):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        assert {str(q["id"]) for q in spec["questions"]} == {str(r["id"]) for r in comprehension_results}
    def test_q1(self, comprehension_results):
        r = _get(comprehension_results, "1"); assert r and r["pass"], f"Q-1: {r.get('reason')}"
    def test_q2(self, comprehension_results):
        r = _get(comprehension_results, "2"); assert r and r["pass"], f"Q-2: {r.get('reason')}"
    def test_q3(self, comprehension_results):
        r = _get(comprehension_results, "3"); assert r and r["pass"], f"Q-3: {r.get('reason')}"
    def test_q4(self, comprehension_results):
        r = _get(comprehension_results, "4"); assert r and r["pass"], f"Q-4: {r.get('reason')}"
    def test_q5(self, comprehension_results):
        r = _get(comprehension_results, "5"); assert r and r["pass"], f"Q-5: {r.get('reason')}"
