# FEAT-PM-3735 Test Plan — Skip CQ tests when spec files unchanged

## Test Cases

### TC-1: First run (no cache) — runs normally
- **Precondition**: Delete `tests/comprehension/.cache/` if it exists
- **Steps**: Run `python references/scripts/run_comprehension_test.py tests/comprehension/2195_spec.json --output-dir <tmp>`
- **Expected**: Test runs normally (spawns Claude agents), writes results, creates cache file on PASS
- **Verification**: Cache file exists at `tests/comprehension/.cache/2195_spec.hash` (or similar)

### TC-2: Second run (unchanged files) — skips
- **Precondition**: TC-1 passed, cache file exists, no files in 2195_spec.json modified
- **Steps**: Run the same command again
- **Expected**: Test skips without spawning Claude, outputs "Skipped — files unchanged since last PASS", exits 0
- **Verification**: No Claude subprocess spawned, exit code 0

### TC-3: File modified — re-runs
- **Precondition**: Cache file exists from a prior PASS
- **Steps**: Touch/modify one of the files listed in the spec, then run the test
- **Expected**: Test detects hash mismatch and runs normally
- **Verification**: Claude subprocess spawned, new cache written on PASS

### TC-4: Spec JSON modified — re-runs
- **Precondition**: Cache file exists from a prior PASS
- **Steps**: Modify the spec JSON (e.g. change a question), then run
- **Expected**: Test detects spec hash mismatch and runs normally
- **Verification**: Claude subprocess spawned

### TC-5: Force bypass — runs despite cache
- **Precondition**: Cache file exists, no files modified
- **Steps**: Run with `--force` flag or `FORCE_CQ=1` env var
- **Expected**: Test runs normally, ignoring the cache
- **Verification**: Claude subprocess spawned despite unchanged files

### TC-6: Failed run — cache NOT updated
- **Precondition**: Existing cache from a prior PASS
- **Steps**: Temporarily break a spec file to cause failure, run
- **Expected**: Test runs, fails, does NOT update cache file
- **Verification**: Cache file timestamp unchanged after the failed run

### TC-7: Missing file in spec — graceful re-run
- **Precondition**: Cache exists, one file in spec's `files` list is deleted/renamed
- **Steps**: Run the test
- **Expected**: Hash computation fails gracefully, test re-runs (does not crash)
- **Verification**: No unhandled exception, test proceeds to run

### TC-8: Cache dir missing — graceful fallback
- **Precondition**: `tests/comprehension/.cache/` does not exist
- **Steps**: Run the test
- **Expected**: Test runs normally, creates cache dir and cache file on PASS
- **Verification**: Directory and cache file created

## Smoke Tests

- [ ] `python tests/run_tests.py` still passes (existing CQ tests unaffected)
- [ ] `.gitignore` includes `tests/comprehension/.cache/`
- [ ] New CQ spec added in future would auto-inherit caching (no extra wiring)

## Regression Risks

- CQ tests silently skipping when they should run (hash logic bug) — mitigated by hashing spec + files
- Cache corruption causing permanent skip — mitigated by PASS-only writes and `--force` bypass
