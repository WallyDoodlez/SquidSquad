"""Tests for #3735 — CQ test content-hash caching in run_comprehension_test.py."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_comprehension_test as cq


class TestComputeHash:
    def test_hashes_spec_and_files(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{"questions": []}')
        f1 = tmp_path / "a.py"
        f1.write_text("print('hello')")
        h = cq._compute_hash(spec, [str(f1)])
        assert h is not None
        assert len(h) == 64  # SHA256 hex

    def test_different_content_different_hash(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{"questions": []}')
        f1 = tmp_path / "a.py"
        f1.write_text("v1")
        h1 = cq._compute_hash(spec, [str(f1)])
        f1.write_text("v2")
        h2 = cq._compute_hash(spec, [str(f1)])
        assert h1 != h2

    def test_missing_file_returns_none(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{}')
        h = cq._compute_hash(spec, [str(tmp_path / "missing.py")])
        assert h is None

    def test_missing_spec_returns_none(self, tmp_path):
        h = cq._compute_hash(tmp_path / "nope.json", [])
        assert h is None

    def test_spec_change_changes_hash(self, tmp_path):
        spec = tmp_path / "spec.json"
        f1 = tmp_path / "a.py"
        f1.write_text("stable")
        spec.write_text('{"questions": [{"id": 1}]}')
        h1 = cq._compute_hash(spec, [str(f1)])
        spec.write_text('{"questions": [{"id": 1}, {"id": 2}]}')
        h2 = cq._compute_hash(spec, [str(f1)])
        assert h1 != h2


class TestCachePath:
    def test_uses_spec_stem(self, tmp_path):
        with patch.object(cq, "CACHE_DIR", tmp_path / ".cache"):
            p = cq._cache_path(tmp_path / "2195_spec.json")
        assert p.name == "2195_spec.hash"


class TestCheckCache:
    def test_no_cache_file_returns_false(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{}')
        with patch.object(cq, "CACHE_DIR", tmp_path / ".cache"):
            assert cq._check_cache(spec, []) is False

    def test_matching_cache_returns_true(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{"q": 1}')
        f1 = tmp_path / "a.py"
        f1.write_text("code")
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        with patch.object(cq, "CACHE_DIR", cache_dir):
            # Write cache first
            cq._write_cache(spec, [str(f1)])
            # Should hit
            assert cq._check_cache(spec, [str(f1)]) is True

    def test_stale_cache_returns_false(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{"q": 1}')
        f1 = tmp_path / "a.py"
        f1.write_text("v1")
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        with patch.object(cq, "CACHE_DIR", cache_dir):
            cq._write_cache(spec, [str(f1)])
            # Modify file
            f1.write_text("v2")
            assert cq._check_cache(spec, [str(f1)]) is False


class TestWriteCache:
    def test_creates_cache_dir_and_file(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{}')
        cache_dir = tmp_path / ".cache"
        with patch.object(cq, "CACHE_DIR", cache_dir):
            cq._write_cache(spec, [])
        assert cache_dir.exists()
        assert (cache_dir / "spec.hash").exists()

    def test_does_not_write_on_missing_file(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text('{}')
        cache_dir = tmp_path / ".cache"
        with patch.object(cq, "CACHE_DIR", cache_dir):
            cq._write_cache(spec, [str(tmp_path / "missing.py")])
        assert not (cache_dir / "spec.hash").exists()


class TestRunTestCacheIntegration:
    """Test that run_test() skips on cache hit and runs on miss."""

    def test_cache_hit_returns_none(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({
            "files": [],
            "questions": [{"id": "1", "question": "q", "expected": "a"}]
        }))
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        with patch.object(cq, "CACHE_DIR", cache_dir), \
             patch.object(cq, "REPO_ROOT", tmp_path):
            # Write a matching cache
            cq._write_cache(spec, [])
            # run_test should skip
            results, out_dir = cq.run_test(str(spec))
            assert results is None
            assert out_dir is None

    def test_force_bypasses_cache(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({
            "files": [],
            "questions": [{"id": "1", "question": "q", "expected": "a"}]
        }))
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        with patch.object(cq, "CACHE_DIR", cache_dir), \
             patch.object(cq, "REPO_ROOT", tmp_path), \
             patch.object(cq, "_find_claude", return_value=None):
            cq._write_cache(spec, [])
            # force=True should not skip — will hit "claude not found" instead
            with pytest.raises(SystemExit) as exc_info:
                cq.run_test(str(spec), force=True)
            # Exit 1 = tried to run (claude not found), not exit 0 (skip)
            assert exc_info.value.code == 1

    def test_env_var_force_bypasses_cache(self, tmp_path):
        spec = tmp_path / "spec.json"
        spec.write_text(json.dumps({
            "files": [],
            "questions": [{"id": "1", "question": "q", "expected": "a"}]
        }))
        cache_dir = tmp_path / ".cache"
        cache_dir.mkdir()
        with patch.object(cq, "CACHE_DIR", cache_dir), \
             patch.object(cq, "REPO_ROOT", tmp_path), \
             patch.object(cq, "_find_claude", return_value=None), \
             patch.dict(os.environ, {"FORCE_CQ": "1"}):
            cq._write_cache(spec, [])
            with pytest.raises(SystemExit) as exc_info:
                cq.run_test(str(spec))
            assert exc_info.value.code == 1
