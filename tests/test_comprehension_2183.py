"""Comprehension tests for #2183 — simplified agent lifecycle.

Requires claude CLI in PATH. Skipped if not available.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SPEC = REPO / "tests" / "comprehension" / "2183_spec.json"
RUNNER = REPO / "references" / "scripts" / "run_comprehension_test.py"


def _claude_available():
    import shutil
    return shutil.which("claude") is not None


@pytest.fixture(scope="module")
def comprehension_results(tmp_path_factory):
    if not _claude_available():
        pytest.skip("claude CLI not available")

    output_dir = tmp_path_factory.mktemp("comprehension-2183")
    result = subprocess.run(
        [sys.executable, str(RUNNER), str(SPEC), "--output-dir", str(output_dir)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        cwd=str(REPO), timeout=600,
    )

    results_path = output_dir / "results.json"
    if not results_path.exists():
        pytest.fail(f"No results.json.\nstdout: {result.stdout[:1000]}\nstderr: {result.stderr[:1000]}")

    raw = results_path.read_text(encoding="utf-8").strip()
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.split("\n") if not l.startswith("```"))

    return json.loads(raw)


def _get_result(results, qid):
    for r in results:
        if str(r.get("id")) == str(qid):
            return r
    return None


class TestComprehension2183:
    def test_all_questions_answered(self, comprehension_results):
        spec = json.loads(SPEC.read_text(encoding="utf-8"))
        expected = {str(q["id"]) for q in spec["questions"]}
        actual = {str(r["id"]) for r in comprehension_results}
        assert expected == actual

    def test_q1_context_pressure_self_restart(self, comprehension_results):
        r = _get_result(comprehension_results, "1")
        assert r and r["pass"], f"Q-1 FAIL: {r.get('reason')}"

    def test_q2_pm_detects_stale_heartbeat(self, comprehension_results):
        r = _get_result(comprehension_results, "2")
        assert r and r["pass"], f"Q-2 FAIL: {r.get('reason')}"

    def test_q3_no_template_self_restart(self, comprehension_results):
        r = _get_result(comprehension_results, "3")
        assert r and r["pass"], f"Q-3 FAIL: {r.get('reason')}"

    def test_q4_three_guarantees(self, comprehension_results):
        r = _get_result(comprehension_results, "4")
        assert r and r["pass"], f"Q-4 FAIL: {r.get('reason')}"

    def test_q5_crash_retry(self, comprehension_results):
        r = _get_result(comprehension_results, "5")
        assert r and r["pass"], f"Q-5 FAIL: {r.get('reason')}"
