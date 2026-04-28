# FEAT-QA-3735 QA Results — CQ test content-hash caching

**Feature**: #3735 — Skip CQ tests when spec files unchanged (content-hash caching)
**Date**: 2026-04-27
**QA agent**: qa-lead
**Test file**: `.squidsquad/qa/planning/FEAT-QA-3735-tests.py`

---

## Summary Table

| TC | Title | Result |
|----|-------|--------|
| TC-1 | First run (no cache) — runs normally | PASS |
| TC-2 | Second run (unchanged files) — skips | PASS |
| TC-2 | Cache hit exit code = 0 | PASS |
| TC-2 | No Claude subprocess spawned on cache hit | PASS |
| TC-3 | File modified — re-runs | PASS |
| TC-4 | Spec JSON modified — re-runs | PASS |
| TC-5 | Force bypass via `--force` flag — runs despite cache | PASS |
| TC-5 | Force bypass via `FORCE_CQ=1` env var — runs despite cache | PASS |
| TC-6 | Failed run — cache NOT updated | PASS |
| TC-7 | Missing file in spec — graceful re-run | PASS |
| TC-8 | Cache dir missing — graceful fallback, dir created on PASS | PASS |
| TC-8 | run_test creates cache file after simulated PASS | PASS |
| Smoke | .gitignore includes `tests/comprehension/.cache/` | PASS |

**Overall**: 13/13 PASS — zero failures, zero human-required items.

---

## Smoke Tests

| Smoke test | Result |
|------------|--------|
| `.gitignore` includes `tests/comprehension/.cache/` | PASS |
| Dev unit tests (`tests/test_cq_cache.py`) all pass | PASS — 14/14 |

---

## Full pytest output — QA tests

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\naaht\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: D:\Dev\Dev\SquidSquad-qa
plugins: anyio-4.12.1, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 13 items

.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_01_first_run PASSED [  7%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_02_cache_skip PASSED [ 15%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_02_cache_skip_exit_code PASSED [ 23%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_02_no_claude_spawned_on_cache_hit PASSED [ 30%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_03_file_modified_reruns PASSED [ 38%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_04_spec_modified_reruns PASSED [ 46%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_05_force_flag_bypasses_cache PASSED [ 53%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_05_env_var_force_bypasses_cache PASSED [ 61%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_06_failed_run_does_not_update_cache PASSED [ 69%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_07_missing_file_graceful_rerun PASSED [ 76%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_08_cache_dir_missing_created_on_pass PASSED [ 84%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_tc_08_run_test_creates_cache_on_simulated_pass PASSED [ 92%]
.squidsquad/qa/planning/FEAT-QA-3735-tests.py::test_smoke_gitignore_includes_cache PASSED [100%]

============================= 13 passed in 0.18s ==============================
```

---

## Full pytest output — Dev unit tests (`tests/test_cq_cache.py`)

```
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.0.2, pluggy-1.6.0 -- C:\Users\naaht\AppData\Local\Programs\Python\Python312\python.exe
cachedir: .pytest_cache
rootdir: D:\Dev\Dev\SquidSquad-qa
plugins: anyio-4.12.1, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.STRICT, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 14 items

tests/test_cq_cache.py::TestComputeHash::test_hashes_spec_and_files PASSED [  7%]
tests/test_cq_cache.py::TestComputeHash::test_different_content_different_hash PASSED [ 14%]
tests/test_cq_cache.py::TestComputeHash::test_missing_file_returns_none PASSED [ 21%]
tests/test_cq_cache.py::TestComputeHash::test_missing_spec_returns_none PASSED [ 28%]
tests/test_cq_cache.py::TestComputeHash::test_spec_change_changes_hash PASSED [ 35%]
tests/test_cq_cache.py::TestCachePath::test_uses_spec_stem PASSED        [ 42%]
tests/test_cq_cache.py::TestCheckCache::test_no_cache_file_returns_false PASSED [ 50%]
tests/test_cq_cache.py::TestCheckCache::test_matching_cache_returns_true PASSED [ 57%]
tests/test_cq_cache.py::TestCheckCache::test_stale_cache_returns_false PASSED [ 64%]
tests/test_cq_cache.py::TestWriteCache::test_creates_cache_dir_and_file PASSED [ 71%]
tests/test_cq_cache.py::TestWriteCache::test_does_not_write_on_missing_file PASSED [ 78%]
tests/test_cq_cache.py::TestRunTestCacheIntegration::test_cache_hit_returns_none PASSED [ 85%]
tests/test_cq_cache.py::TestRunTestCacheIntegration::test_force_bypasses_cache PASSED [ 92%]
tests/test_cq_cache.py::TestRunTestCacheIntegration::test_env_var_force_bypasses_cache PASSED [ 100%]

============================= 14 passed in 0.11s ==============================
```

---

## Notes

- All Claude CLI calls are mocked (`patch.object(cq, "_find_claude", ...)` and `patch.object(cq, "_run_agent", ...)`). No real Claude subprocess is needed.
- TC-6 uses a fake `_run_agent` side-effect that writes a failing `results.json` to verify the cache is left untouched after a failed run.
- TC-7 and TC-8 verify the two graceful-handling paths: missing file → `_compute_hash` returns `None` (not exception), and missing cache dir → `_write_cache` creates it.
- Smoke test verifies `.gitignore` contains `tests/comprehension/.cache/` as a literal string match.
- No HUMAN-REQUIRED items. All 8 test cases and both smoke tests are fully automatable.
