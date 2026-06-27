"""#12748 — comprehension fixtures must SKIP (not FAIL) when the pipeline can't
run in a keyless / unauthenticated environment or hits the cache.

Exercises the shared gate in comprehension_helpers.run_comprehension_or_skip
with mocks, so it is deterministic regardless of whether the claude CLI is
present in the test environment.
"""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))

import comprehension_helpers as ch  # noqa: E402


def _cp(returncode=0, stdout="", stderr=""):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_skips_when_claude_absent(tmp_path):
    with patch.object(ch, "claude_available", return_value=False):
        with pytest.raises(pytest.skip.Exception):
            ch.run_comprehension_or_skip(tmp_path / "spec.json", tmp_path / "out")


def test_skips_on_cache_hit(tmp_path):
    # Runner exit 0 with no results.json == cache hit (spec unchanged). The
    # detection is exit-code based, not stdout-marker based (#12748).
    out = tmp_path / "out"
    out.mkdir()
    with patch.object(ch, "claude_available", return_value=True), \
         patch.object(ch.subprocess, "run",
                      return_value=_cp(0, "Skipped — files unchanged since last PASS")):
        with pytest.raises(pytest.skip.Exception) as exc:
            ch.run_comprehension_or_skip(tmp_path / "x_spec.json", out)
    assert "cache hit" in str(exc.value)


def test_skips_when_no_results_json_keyless(tmp_path):
    """claude binary present but unusable -> pipeline exits non-zero, writes no
    results.json -> SKIP (was the FAIL that reddened keyless suites)."""
    out = tmp_path / "out"
    out.mkdir()
    with patch.object(ch, "claude_available", return_value=True), \
         patch.object(ch.subprocess, "run",
                      return_value=_cp(1, "", "auth error: no API key")):
        with pytest.raises(pytest.skip.Exception) as exc:
            ch.run_comprehension_or_skip(tmp_path / "spec.json", out)
    assert "could not run" in str(exc.value) and "not usable" in str(exc.value)


def test_returns_parsed_results_when_present(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "results.json").write_text(
        '[{"id": "1", "pass": true, "reason": "ok"}]', encoding="utf-8")
    with patch.object(ch, "claude_available", return_value=True), \
         patch.object(ch.subprocess, "run", return_value=_cp(0)):
        results = ch.run_comprehension_or_skip(tmp_path / "spec.json", out)
    assert results == [{"id": "1", "pass": True, "reason": "ok"}]


def test_strips_code_fences_from_results(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "results.json").write_text(
        '```json\n[{"id": "1", "pass": true}]\n```', encoding="utf-8")
    with patch.object(ch, "claude_available", return_value=True), \
         patch.object(ch.subprocess, "run", return_value=_cp(0)):
        results = ch.run_comprehension_or_skip(tmp_path / "spec.json", out)
    assert results == [{"id": "1", "pass": True}]


def test_fails_on_malformed_present_results(tmp_path):
    """A present-but-malformed results.json means the pipeline RAN and produced
    garbage — that IS a real anomaly, so FAIL (not skip)."""
    out = tmp_path / "out"
    out.mkdir()
    (out / "results.json").write_text("not json{", encoding="utf-8")
    with patch.object(ch, "claude_available", return_value=True), \
         patch.object(ch.subprocess, "run", return_value=_cp(0)):
        # pytest.fail raises Failed (a BaseException-derived outcome, distinct
        # from Skipped) — a present-but-garbage results.json is a real FAIL.
        with pytest.raises(pytest.fail.Exception):
            ch.run_comprehension_or_skip(tmp_path / "spec.json", out)


def test_pipeline_comprehension_modules_use_the_shared_helper():
    """Guard: every comprehension module that RUNS THE PIPELINE (defines a
    ``comprehension_results`` fixture) routes through the shared gate, so the
    per-file FAIL-instead-of-SKIP drift can't return (#12748). Spec-integrity
    modules (no pipeline, deterministic keyless) are out of scope."""
    files = sorted(TESTS.glob("test_comprehension_*.py"))
    pipeline = [f for f in files
                if "def comprehension_results" in f.read_text(encoding="utf-8")]
    assert len(pipeline) >= 7, f"expected ≥7 pipeline modules, got {len(pipeline)}"
    for f in pipeline:
        text = f.read_text(encoding="utf-8")
        assert "run_comprehension_or_skip" in text, (
            f"{f.name} must use comprehension_helpers.run_comprehension_or_skip"
        )
        # The pipeline fixture must SKIP (via the helper), never FAIL, on a
        # missing results.json — the exact #12748 keyless-red regression.
        assert "did not produce results.json" not in text, (
            f"{f.name} still FAILs on missing results.json (#12748)"
        )
        assert "No results.json" not in text, (
            f"{f.name} still FAILs on missing results.json (#12748)"
        )
