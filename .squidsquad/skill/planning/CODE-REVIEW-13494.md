NO_FINDINGS

The change is straightforward and correct:

1. **`_git_in_clone`** (line ~2990) now passes `env={**os.environ, "LC_ALL": "C"}` to `subprocess.run`. This is a correct superset pattern — it preserves the full existing environment (PATH, HOME, SSH credentials, etc.) while overriding only `LC_ALL` to `"C"`, which forces git to emit stable English messages on all platforms.

2. **All deploy-path git calls flow through `_git_in_clone`**: `_safe_pull_in_clone`, `_safe_stash_pop_in_clone`, `_stage_composed_outputs`, and `_run_deploy_sequence` all route their git invocations exclusively through `_git_in_clone`. There are no bypasses.

3. **The English-substring checks in the deploy-pull helpers are now locale-robust**: `"untracked files from stash"` (`.lower()` match in `_safe_stash_pop_in_clone`), `"already up to date"` and `"up to date"` (`.lower()` match in `_safe_pull_in_clone`) will now match reliably regardless of the operator's `LANG`/`LC_MESSAGES`.

4. **The regression tests correctly assert**:
   - `LC_ALL` is forced to `"C"` in the passed environment (`test_git_in_clone_forces_lc_all_c`)
   - Existing environment variables are preserved, not replaced (`test_git_in_clone_preserves_existing_environment`)

5. **No disturbance to real-git deploy-pull tests**: The `env` parameter is a pure addition to an existing `subprocess.run` call; all other parameters (`capture_output`, `text`, `encoding`, `errors`, `check`, `cwd`, `timeout`) are unchanged. Real git behavior under `LC_ALL=C` is identical to the prior behavior for English-locale operators, and now correct for non-English operators (where it was previously silently broken).