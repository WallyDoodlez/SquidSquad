Now I have a thorough understanding of the entire change. Let me compile my findings.

---

### Finding 1

- **File**: tests/test_cycle_post.py
- **Line**: 1204 (parameter definition) and 1219 (usage)
- **Severity**: warning
- **Issue**: The `tag_l_succeeds` parameter in `_build_fake_run` exists to simulate `git tag -l` returning a non-zero exit code, but no test in `TestOrphanedTagRecovery` ever sets it to `False`. The error path `if local_check.returncode != 0: return False` at line 583 in `_recover_orphaned_tag` is never exercised by any test.
- **Evidence**: `grep` confirms `tag_l_succeeds=False` appears nowhere in the file. Five tests call `_build_fake_run` — all rely on the default `tag_l_succeeds=True`. If a future refactoring accidentally removes or changes the `returncode != 0` guard, the `_recover_orphaned_tag` function could proceed to `ls-remote` with a mis-parsed local tag state, or crash on `.stdout.strip()` if `_run` returns an object with `stdout=None` on error. The infrastructure to test this path already exists (the parameter) but is dead code.
- **Suggested fix**: Add a test like `test_tag_l_failure_aborts_recovery_safely` that sets `tag_l_succeeds=False`, and asserts that no `ls-remote` call, no push, and no counter reset occur, and that the "skipping commit/tag/push" message is printed.

---

### Finding 2

- **File**: tests/test_cycle_post.py
- **Line**: 1349–1370 (`test_ls_remote_failure_aborts_recovery_safely`)
- **Severity**: warning
- **Issue**: The test docstring states "fall through to skip message" but the test body never asserts that the skip message appears in `captured.out`. The test only asserts that no push was attempted and no counter reset occurred. This leaves the "skip message" behavior for the `ls-remote` failure path unverified.
- **Evidence**: At lines 1367–1370, the assertions are:
  ```python
  assert not any(c[:3] == ["git", "push", "origin"] for c in run_calls)
  reset_calls = [c for c in script_calls
                 if c[0] == "config.py" and "shipped-since-bump" in c[1]]
  assert reset_calls == []
  ```
  There is no `capsys.readouterr()` call or assertion on `captured.out`. Compare with the sibling test `test_no_recovery_when_local_tag_missing` at line 1294 which correctly asserts `assert "skipping commit/tag/push" in captured.out`. If the production code were changed to `return` without printing the skip message after a failed `ls-remote`, this test would not catch it.
- **Suggested fix**: Add `captured = capsys.readouterr()` and `assert "skipping commit/tag/push" in captured.out` at the end of `test_ls_remote_failure_aborts_recovery_safely`, matching the pattern used in `test_no_recovery_when_local_tag_missing`.

---

### Finding 3

- **File**: tests/test_cycle_post.py
- **Line**: 1320–1347 (`test_recovery_push_failure_skips_counter_reset`)
- **Severity**: warning
- **Issue**: Same pattern as Finding 2 — when the recovery push fails, the production code at line 651 in `cycle_post.py` prints "skipping commit/tag/push" after the ERROR message. The test verifies the ERROR appears on stderr but never asserts the skip message appears on stdout. If a future change accidentally removes the fall-through print, this test would not catch it.
- **Evidence**: At lines 1344–1347, only `captured.err` is checked:
  ```python
  captured = capsys.readouterr()
  assert "ERROR" in captured.err
  assert "recovery push failed" in captured.err
  assert "v6.3.0" in captured.err
  ```
  No assertion on `captured.out`. All other "no-recovery" tests (`test_no_recovery_when_local_tag_missing`, `test_no_recovery_when_remote_already_has_tag`) do assert the skip message.
- **Suggested fix**: Add `assert "skipping commit/tag/push" in captured.out` after the stderr assertions, confirming the function still falls through to the normal skip message after a failed recovery push.

---

*Note: The production code in `_recover_orphaned_tag` (lines 567–610 of `cycle_post.py`) is correct. The recovery probe is strictly opportunistic — every non-zero return code or unexpected state causes a safe `return False`. The diff-guard gating at line 647 ensures the recovery path is only entered when there are genuinely no staged changes. The change to the existing `test_staged_diff_guard_skips_empty_commit` (lines 826–835) correctly distinguishes between read-only `tag -l` probes and destructive `tag v2.0.0` creation, preventing a false positive in that test.*