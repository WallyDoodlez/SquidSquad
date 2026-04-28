"""QA test suite for #3735 — CQ test content-hash caching.

Test plan: .squidsquad/pm/planning/FEAT-PM-3735-TEST-PLAN.md
Implementation: references/scripts/run_comprehension_test.py
Dev unit tests:  tests/test_cq_cache.py
"""

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the scripts directory to sys.path so we can import the module under test.
REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPTS = REPO_ROOT / "references" / "scripts"
sys.path.insert(0, str(SCRIPTS))

import run_comprehension_test as cq


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_spec(tmp_path, files=None, questions=None):
    """Write a minimal spec JSON and return its path."""
    spec = tmp_path / "test_spec.json"
    spec.write_text(
        json.dumps({
            "files": files or [],
            "questions": questions or [
                {"id": "1", "question": "What is X?", "expected": "X is Y."}
            ],
        }),
        encoding="utf-8",
    )
    return spec


def _write_cache_for(spec, files, cache_dir):
    """Write a cache entry using cq._write_cache with patched CACHE_DIR."""
    with patch.object(cq, "CACHE_DIR", cache_dir):
        cq._write_cache(spec, [str(f) for f in files])


# ---------------------------------------------------------------------------
# TC-1: First run (no cache) — run_test detects cache miss and proceeds
# ---------------------------------------------------------------------------

def test_tc_01_first_run(tmp_path):
    """TC-1: When no cache file exists the script proceeds (not skip).
    We mock _find_claude to return None so it exits 1 (tried-to-run path),
    NOT exit 0 (skip path).  A cache file must NOT exist before the run.
    """
    cache_dir = tmp_path / ".cache"
    spec = _make_spec(tmp_path)

    # Precondition: no cache file
    cache_file = cache_dir / "test_spec.hash"
    assert not cache_file.exists(), "Cache file should not exist before first run"

    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch.object(cq, "_find_claude", return_value=None):
        # Without a cache hit the code will try to spawn Claude (not found) → exit 1
        with pytest.raises(SystemExit) as exc_info:
            cq.run_test(str(spec))
        # exit 1 means "tried to run but claude not found" — NOT the skip path (exit 0)
        assert exc_info.value.code == 1, (
            f"Expected exit code 1 (run attempted, claude not found), got {exc_info.value.code}"
        )


# ---------------------------------------------------------------------------
# TC-2: Second run (unchanged files) — skips
# ---------------------------------------------------------------------------

def test_tc_02_cache_skip(tmp_path):
    """TC-2: When cache matches, run_test returns (None, None) and exits 0."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    spec = _make_spec(tmp_path, files=[])

    _write_cache_for(spec, [], cache_dir)

    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path):
        results, out_dir = cq.run_test(str(spec))

    assert results is None, "run_test should return None on cache hit"
    assert out_dir is None, "run_test should return None out_dir on cache hit"


def test_tc_02_cache_skip_exit_code(tmp_path):
    """TC-2 (exit code): main() exits 0 on cache hit."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    spec = _make_spec(tmp_path, files=[])
    _write_cache_for(spec, [], cache_dir)

    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch("sys.argv", ["run_comprehension_test.py", str(spec)]):
        with pytest.raises(SystemExit) as exc_info:
            cq.main()
        assert exc_info.value.code == 0, (
            f"Cache-hit main() should exit 0, got {exc_info.value.code}"
        )


def test_tc_02_no_claude_spawned_on_cache_hit(tmp_path):
    """TC-2 (no subprocess): _run_agent must not be called on a cache hit."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    spec = _make_spec(tmp_path, files=[])
    _write_cache_for(spec, [], cache_dir)

    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch.object(cq, "_run_agent") as mock_agent:
        cq.run_test(str(spec))
        mock_agent.assert_not_called()


# ---------------------------------------------------------------------------
# TC-3: File modified — re-runs
# ---------------------------------------------------------------------------

def test_tc_03_file_modified_reruns(tmp_path):
    """TC-3: Modifying a listed file invalidates cache → run_test proceeds."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    listed_file = tmp_path / "src.py"
    listed_file.write_text("version 1", encoding="utf-8")
    spec = _make_spec(tmp_path, files=[str(listed_file)])

    _write_cache_for(spec, [listed_file], cache_dir)

    # Verify cache hit before modification
    with patch.object(cq, "CACHE_DIR", cache_dir):
        assert cq._check_cache(spec, [str(listed_file)]) is True

    # Modify the file
    listed_file.write_text("version 2", encoding="utf-8")

    # Cache should now be a miss
    with patch.object(cq, "CACHE_DIR", cache_dir):
        assert cq._check_cache(spec, [str(listed_file)]) is False

    # run_test should try to run (not skip): it will hit "claude not found" → exit 1
    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch.object(cq, "_find_claude", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            cq.run_test(str(spec))
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# TC-4: Spec JSON modified — re-runs
# ---------------------------------------------------------------------------

def test_tc_04_spec_modified_reruns(tmp_path):
    """TC-4: Modifying the spec JSON itself invalidates the cache."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    spec = _make_spec(tmp_path, files=[], questions=[{"id": "1", "question": "Q1?", "expected": "A1"}])

    _write_cache_for(spec, [], cache_dir)

    # Verify cache hit before modification
    with patch.object(cq, "CACHE_DIR", cache_dir):
        assert cq._check_cache(spec, []) is True

    # Modify the spec (add a question)
    spec.write_text(
        json.dumps({
            "files": [],
            "questions": [
                {"id": "1", "question": "Q1?", "expected": "A1"},
                {"id": "2", "question": "Q2 — new question?", "expected": "A2"},
            ],
        }),
        encoding="utf-8",
    )

    # Cache should now be a miss
    with patch.object(cq, "CACHE_DIR", cache_dir):
        assert cq._check_cache(spec, []) is False

    # run_test should try to run (claude not found path → exit 1)
    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch.object(cq, "_find_claude", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            cq.run_test(str(spec))
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# TC-5: Force bypass — runs despite cache
# ---------------------------------------------------------------------------

def test_tc_05_force_flag_bypasses_cache(tmp_path):
    """TC-5: --force flag bypasses cache even when files unchanged."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    spec = _make_spec(tmp_path, files=[])
    _write_cache_for(spec, [], cache_dir)

    # Confirm cache hit without force
    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path):
        results, _ = cq.run_test(str(spec), force=False)
        assert results is None  # cache hit

    # With force=True, cache is ignored → tries to run → claude not found → exit 1
    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch.object(cq, "_find_claude", return_value=None):
        with pytest.raises(SystemExit) as exc_info:
            cq.run_test(str(spec), force=True)
        assert exc_info.value.code == 1, (
            "force=True should bypass cache and attempt to run (exit 1 = claude not found)"
        )


def test_tc_05_env_var_force_bypasses_cache(tmp_path):
    """TC-5: FORCE_CQ=1 env var bypasses cache."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    spec = _make_spec(tmp_path, files=[])
    _write_cache_for(spec, [], cache_dir)

    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch.object(cq, "_find_claude", return_value=None), \
         patch.dict(os.environ, {"FORCE_CQ": "1"}):
        with pytest.raises(SystemExit) as exc_info:
            cq.run_test(str(spec))
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# TC-6: Failed run — cache NOT updated
# ---------------------------------------------------------------------------

def test_tc_06_failed_run_does_not_update_cache(tmp_path):
    """TC-6: A failing run must NOT update the cache file."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    listed_file = tmp_path / "file.py"
    listed_file.write_text("original", encoding="utf-8")
    spec = _make_spec(tmp_path, files=[str(listed_file)])

    # Seed a cache from a "previous PASS"
    _write_cache_for(spec, [listed_file], cache_dir)
    cache_file = cache_dir / "test_spec.hash"
    original_mtime = cache_file.stat().st_mtime
    original_content = cache_file.read_text(encoding="utf-8").strip()

    # Modify file so hash changes — next run would produce a different hash
    listed_file.write_text("broken version", encoding="utf-8")

    # Simulate a run that fails (all_pass=False) — mock at the run_test level
    # by making _run_agent return a fake result and faking results.json content
    answers_path_holder = {}

    def fake_run_agent(claude_bin, prompt, workdir, allowed_tools="Read,Write"):
        """Fake agent: writes output files so run_test can proceed."""
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        # Determine output dir that run_test will use
        out_dir = spec.parent / f".comprehension-{spec.stem}"
        out_dir.mkdir(parents=True, exist_ok=True)
        answers = out_dir / "answers.md"
        results_json = out_dir / "results.json"
        if not answers.exists():
            answers.write_text("### Q-1\nSome answer", encoding="utf-8")
        if not results_json.exists():
            # Write a FAILING result
            results_json.write_text(
                json.dumps([{"id": "1", "pass": False, "reason": "wrong answer"}]),
                encoding="utf-8",
            )
        return result

    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch.object(cq, "_find_claude", return_value="/fake/claude"), \
         patch.object(cq, "_run_agent", side_effect=fake_run_agent):
        results, _ = cq.run_test(str(spec))

    assert results is not None
    assert not all(r.get("pass") for r in results), "Expected a failing result"

    # Cache file must be unchanged (same mtime and content as before the run)
    new_content = cache_file.read_text(encoding="utf-8").strip()
    assert new_content == original_content, (
        "Cache file content changed after a failed run — it must NOT be updated on failure"
    )


# ---------------------------------------------------------------------------
# TC-7: Missing file in spec — graceful re-run
# ---------------------------------------------------------------------------

def test_tc_07_missing_file_graceful_rerun(tmp_path):
    """TC-7: If a file listed in the spec is missing, hash returns None → cache miss → re-run."""
    cache_dir = tmp_path / ".cache"
    cache_dir.mkdir()
    existing_file = tmp_path / "present.py"
    existing_file.write_text("here", encoding="utf-8")
    missing_file = tmp_path / "gone.py"
    # Write the spec referencing BOTH files
    spec = _make_spec(tmp_path, files=[str(existing_file), str(missing_file)])

    # Write cache while both files exist
    missing_file.write_text("exists briefly", encoding="utf-8")
    _write_cache_for(spec, [existing_file, missing_file], cache_dir)
    # Now delete one file
    missing_file.unlink()

    # _compute_hash must return None (not raise)
    h = cq._compute_hash(spec, [str(existing_file), str(missing_file)])
    assert h is None, "_compute_hash should return None when a listed file is missing"

    # _check_cache must return False (not raise)
    with patch.object(cq, "CACHE_DIR", cache_dir):
        hit = cq._check_cache(spec, [str(existing_file), str(missing_file)])
    assert hit is False, "_check_cache should return False when hash is None"

    # run_test should proceed (try to run, not skip) — exits 1 (claude not found)
    # The spec references missing_file but run_test reads files list from the JSON,
    # and hash computation returns None → forces re-run with no unhandled exception.
    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch.object(cq, "_find_claude", return_value=None):
        try:
            cq.run_test(str(spec))
            pytest.fail("Expected SystemExit from claude-not-found, got normal return")
        except SystemExit as exc:
            assert exc.code == 1, f"Expected exit 1 (claude not found), got {exc.code}"
        except Exception as exc:
            pytest.fail(f"Unexpected exception (should be graceful): {exc}")


# ---------------------------------------------------------------------------
# TC-8: Cache dir missing — graceful fallback, dir and file created on PASS
# ---------------------------------------------------------------------------

def test_tc_08_cache_dir_missing_created_on_pass(tmp_path):
    """TC-8: If cache dir does not exist, _write_cache creates it."""
    cache_dir = tmp_path / ".cache"
    assert not cache_dir.exists(), "Precondition: cache dir must not exist"

    spec = _make_spec(tmp_path, files=[])

    with patch.object(cq, "CACHE_DIR", cache_dir):
        # _check_cache returns False (no dir → no cache file)
        assert cq._check_cache(spec, []) is False

        # _write_cache creates the dir and writes the file
        cq._write_cache(spec, [])

    assert cache_dir.exists(), "Cache directory should be created by _write_cache"
    expected_file = cache_dir / "test_spec.hash"
    assert expected_file.exists(), "Cache file should be written after _write_cache"
    content = expected_file.read_text(encoding="utf-8").strip()
    assert len(content) == 64, f"Cache file should contain a SHA256 hex digest (64 chars), got {len(content)}"


def test_tc_08_run_test_creates_cache_on_simulated_pass(tmp_path):
    """TC-8 (integration): run_test writes cache file when all questions pass."""
    cache_dir = tmp_path / ".cache"
    assert not cache_dir.exists()

    listed_file = tmp_path / "src.py"
    listed_file.write_text("code", encoding="utf-8")
    spec = _make_spec(tmp_path, files=[str(listed_file)])

    def fake_run_agent(claude_bin, prompt, workdir, allowed_tools="Read,Write"):
        result = MagicMock()
        result.returncode = 0
        result.stderr = ""
        out_dir = spec.parent / f".comprehension-{spec.stem}"
        out_dir.mkdir(parents=True, exist_ok=True)
        answers = out_dir / "answers.md"
        results_json = out_dir / "results.json"
        if not answers.exists():
            answers.write_text("### Q-1\nCorrect answer", encoding="utf-8")
        if not results_json.exists():
            results_json.write_text(
                json.dumps([{"id": "1", "pass": True, "reason": "correct"}]),
                encoding="utf-8",
            )
        return result

    with patch.object(cq, "CACHE_DIR", cache_dir), \
         patch.object(cq, "REPO_ROOT", tmp_path), \
         patch.object(cq, "_find_claude", return_value="/fake/claude"), \
         patch.object(cq, "_run_agent", side_effect=fake_run_agent):
        results, out_dir = cq.run_test(str(spec))

    assert results is not None
    assert all(r.get("pass") for r in results)
    assert cache_dir.exists(), "Cache dir should be created after a PASS"
    cache_file = cache_dir / "test_spec.hash"
    assert cache_file.exists(), "Cache file should be written after a PASS"
    content = cache_file.read_text(encoding="utf-8").strip()
    assert len(content) == 64


# ---------------------------------------------------------------------------
# Smoke test: .gitignore includes tests/comprehension/.cache/
# ---------------------------------------------------------------------------

def test_smoke_gitignore_includes_cache():
    """Smoke: .gitignore must contain the cache directory entry."""
    gitignore = REPO_ROOT / ".gitignore"
    assert gitignore.exists(), f".gitignore not found at {gitignore}"
    content = gitignore.read_text(encoding="utf-8")
    assert "tests/comprehension/.cache/" in content, (
        "'.gitignore' should contain 'tests/comprehension/.cache/' but does not.\n"
        f"Current .gitignore content excerpt:\n{content[:500]}"
    )
