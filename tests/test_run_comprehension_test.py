"""Tests for references/scripts/run_comprehension_test.py (#4052).

Covers: content-hash caching, cache path resolution, spec parsing.
Agent invocation is mocked — these are unit tests, not integration tests.
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_comprehension_test as rct


# ---------------------------------------------------------------------------
# _compute_hash
# ---------------------------------------------------------------------------

class TestComputeHash:
    def test_returns_hex_digest(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{"files": []}', encoding="utf-8")
        result = rct._compute_hash(str(spec), [])
        assert isinstance(result, str)
        assert len(result) == 64  # SHA256 hex

    def test_different_content_different_hash(self, tmp_path):
        spec1 = tmp_path / "spec1.json"
        spec2 = tmp_path / "spec2.json"
        spec1.write_text('{"a": 1}', encoding="utf-8")
        spec2.write_text('{"a": 2}', encoding="utf-8")
        h1 = rct._compute_hash(str(spec1), [])
        h2 = rct._compute_hash(str(spec2), [])
        assert h1 != h2

    def test_includes_listed_files(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text("{}", encoding="utf-8")
        f1 = tmp_path / "file1.txt"
        f1.write_text("content1", encoding="utf-8")

        h_without = rct._compute_hash(str(spec), [])
        h_with = rct._compute_hash(str(spec), [str(f1)])
        assert h_without != h_with

    def test_missing_spec_returns_none(self, tmp_path):
        result = rct._compute_hash(str(tmp_path / "nonexistent.json"), [])
        assert result is None

    def test_missing_listed_file_returns_none(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text("{}", encoding="utf-8")
        result = rct._compute_hash(str(spec), [str(tmp_path / "missing.txt")])
        assert result is None


# ---------------------------------------------------------------------------
# _cache_path
# ---------------------------------------------------------------------------

class TestCachePath:
    def test_uses_spec_stem(self):
        result = rct._cache_path("/some/path/my-test.json")
        assert result.name == "my-test.hash"

    def test_under_cache_dir(self):
        result = rct._cache_path("spec.json")
        assert ".cache" in str(result)


# ---------------------------------------------------------------------------
# _check_cache / _write_cache
# ---------------------------------------------------------------------------

class TestCacheRoundTrip:
    def test_cache_miss_on_empty(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{"files": []}', encoding="utf-8")
        with patch.object(rct, "CACHE_DIR", tmp_path / ".cache"):
            assert rct._check_cache(str(spec), []) is False

    def test_cache_hit_after_write(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{"files": []}', encoding="utf-8")
        with patch.object(rct, "CACHE_DIR", tmp_path / ".cache"):
            rct._write_cache(str(spec), [])
            assert rct._check_cache(str(spec), []) is True

    def test_cache_miss_after_file_change(self, tmp_path):
        spec = tmp_path / "spec.json"
        f1 = tmp_path / "file1.txt"
        spec.write_text('{"files": []}', encoding="utf-8")
        f1.write_text("version1", encoding="utf-8")
        with patch.object(rct, "CACHE_DIR", tmp_path / ".cache"):
            rct._write_cache(str(spec), [str(f1)])
            # Modify the file
            f1.write_text("version2", encoding="utf-8")
            assert rct._check_cache(str(spec), [str(f1)]) is False

    def test_write_cache_atomic(self, tmp_path):
        """Cache write uses .tmp then rename — no leftover .tmp."""
        spec = tmp_path / "spec.json"
        spec.write_text("{}", encoding="utf-8")
        with patch.object(rct, "CACHE_DIR", tmp_path / ".cache"):
            rct._write_cache(str(spec), [])
            assert not (tmp_path / ".cache" / "spec.tmp").exists()
            assert (tmp_path / ".cache" / "spec.hash").exists()


# ---------------------------------------------------------------------------
# _find_claude
# ---------------------------------------------------------------------------

class TestFindClaude:
    def test_returns_string_or_none(self):
        result = rct._find_claude()
        assert result is None or isinstance(result, str)

    def test_finds_claude_on_path(self):
        with patch.object(rct.shutil, "which", return_value="/usr/bin/claude"):
            result = rct._find_claude()
        assert result == "/usr/bin/claude"

    def test_returns_none_when_not_found(self):
        with patch.object(rct.shutil, "which", return_value=None), \
             patch.dict("os.environ", {"APPDATA": "/nonexistent"}, clear=False):
            result = rct._find_claude()
        assert result is None


# ---------------------------------------------------------------------------
# run_test — cache skip path
# ---------------------------------------------------------------------------

class TestRunAgentTimeout:
    """#6819: _run_agent timeout must be caught, not crash the script."""

    def test_run_agent_has_timeout(self):
        """_run_agent passes timeout=300 to subprocess.run."""
        import inspect
        source = inspect.getsource(rct._run_agent)
        assert "timeout=" in source, "_run_agent must set subprocess timeout"

    def test_timeout_handling_in_run_test(self):
        """#6819: run_test wraps _run_agent in try/except TimeoutExpired."""
        import inspect
        source = inspect.getsource(rct.run_test)
        assert "TimeoutExpired" in source, (
            "#6819: run_test must handle subprocess.TimeoutExpired"
        )


class TestRunTestCacheSkip:
    def test_cache_hit_returns_none(self, tmp_path):
        """When cache hits, run_test returns (None, None) without spawning agents."""
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({
            "files": [],
            "questions": [{"id": "Q1", "question": "test?", "expected": "yes"}],
        }), encoding="utf-8")
        with patch.object(rct, "CACHE_DIR", tmp_path / ".cache"), \
             patch.object(rct, "_check_cache", return_value=True):
            results, out_dir = rct.run_test(str(spec))
        assert results is None
        assert out_dir is None


# ---------------------------------------------------------------------------
# Empty results guard — #8569
# ---------------------------------------------------------------------------

class TestEmptyResultsGuard:
    """#8569: Empty eval results must be treated as failure, not vacuous pass."""

    def test_empty_results_returns_empty_list(self, tmp_path):
        """run_test returns empty list (not None) when eval produces no results."""
        from unittest.mock import MagicMock

        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({
            "files": [],
            "questions": [{"id": "Q1", "question": "test?", "expected": "yes"}],
        }), encoding="utf-8")

        # Mock agents: test agent writes answers, eval agent writes empty []
        out_dir = tmp_path / "output"
        out_dir.mkdir()
        answers = out_dir / "answers.md"
        answers.write_text("### Q-Q1\nsome answer\n", encoding="utf-8")
        results_file = out_dir / "results.json"
        results_file.write_text("[]", encoding="utf-8")

        fake_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch.object(rct, "_check_cache", return_value=False), \
             patch.object(rct, "_find_claude", return_value="/usr/bin/claude"), \
             patch.object(rct, "_run_agent", return_value=fake_result), \
             patch.object(rct, "REPO_ROOT", tmp_path):
            results, _ = rct.run_test(str(spec), output_dir=str(out_dir))

        assert results == []

    def test_empty_results_not_cached(self, tmp_path):
        """Empty results must NOT update the cache (would mask broken eval)."""
        from unittest.mock import MagicMock

        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({
            "files": [],
            "questions": [{"id": "Q1", "question": "test?", "expected": "yes"}],
        }), encoding="utf-8")

        out_dir = tmp_path / "output"
        out_dir.mkdir()
        (out_dir / "answers.md").write_text("### Q-Q1\nanswer\n", encoding="utf-8")
        (out_dir / "results.json").write_text("[]", encoding="utf-8")

        cache_dir = tmp_path / ".cache"
        fake_result = MagicMock(returncode=0, stdout="", stderr="")
        with patch.object(rct, "_check_cache", return_value=False), \
             patch.object(rct, "_find_claude", return_value="/usr/bin/claude"), \
             patch.object(rct, "_run_agent", return_value=fake_result), \
             patch.object(rct, "CACHE_DIR", cache_dir), \
             patch.object(rct, "REPO_ROOT", tmp_path):
            rct.run_test(str(spec), output_dir=str(out_dir))

        # Cache should NOT have been written
        assert not (cache_dir / "spec.hash").exists()

    def test_no_unused_tempfile_import(self):
        """#8568: tempfile import must be removed."""
        import inspect
        source = inspect.getsource(rct)
        assert "import tempfile" not in source
