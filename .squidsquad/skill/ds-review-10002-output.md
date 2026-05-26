I now have a thorough understanding of both files. Let me compile the findings.

---

### Finding 1

- **File**: references/scripts/cycle_post.py
- **Line**: 613
- **Severity**: warning
- **Issue**: `tag_check = _run(["git", "tag", "-l", f"v{new_version}"])` — the returncode is never examined. Only `tag_check.stdout.strip()` is checked at line 614. Every other git subcommand in the same function (commit at line 603, tag-create at line 616, push at line 626, push --tags at line 637) has its returncode checked, but `tag -l` is the lone exception. If `git tag -l` itself fails (rc != 0), `stdout` would likely be empty, and the code would proceed to `git tag v{new_version}` as if the tag didn't exist. If the tag actually does exist (masked by the listing failure), the subsequent tag-creation error message will blame `git tag v{new_version}` rather than the real root cause (`git tag -l` failed).
- **Evidence**: Line 614: `if not tag_check.stdout.strip():` — only stdout, no `tag_check.returncode` check. Contrast with lines 603, 616, 626, 637 which all check `*.returncode != 0`.
- **Suggested fix**: Add a returncode check before consuming stdout:

```python
tag_check = _run(["git", "tag", "-l", f"v{new_version}"])
if tag_check.returncode != 0:
    print(
        f"  ERROR: git tag -l failed (rc={tag_check.returncode}): "
        f"{tag_check.stderr.strip() or '(no stderr)'} — "
        f"cannot determine if tag v{new_version} exists; aborting",
        file=sys.stderr,
    )
    return
if not tag_check.stdout.strip():
    ...
```

---

### Finding 2

- **File**: tests/test_cycle_post.py
- **Line**: 997
- **Severity**: warning
- **Issue**: The `_fake_run_factory` helper uses prefix matching (`cmd[:len(failing_cmd_prefix)] == failing_cmd_prefix`) to decide which command fails. In `test_push_failure`, `failing_cmd_prefix = ["git", "push"]` would also match `["git", "push", "--tags"]` because `["git", "push", "--tags"][:2] == ["git", "push"]`. The test passes only because `_do_version_bump` returns at line 634 before `git push --tags` is ever reached. If the function were ever refactored to reverse the push order (tags first, then commit push), this test would silently fail `git push --tags` instead of only `git push`, producing a confusing false positive or false negative.
- **Evidence**: Line 1015-1016: `self._fake_run_factory(["git", "push"], run_calls)`. At line 997, `["git", "push", "--tags"][:2]` equals `["git", "push"]`, which matches the prefix. The only thing saving this test is the early return at line 634.
- **Suggested fix**: Use exact equality instead of prefix matching:

```python
elif failing_cmd is not None and cmd == failing_cmd:
```

And update call sites to pass the exact command list (e.g., `["git", "push"]` instead of `["git", "push"]` — no change needed for that caller, but `["git", "commit"]` would need to become the full command or the factory would need to match only the exact prefix intentionally). Alternatively, document that the factory is prefix-based and add a comment warning about the ordering dependency.

---

### Finding 3

- **File**: tests/test_cycle_post.py
- **Line**: 977–1133 (class `TestVersionBumpPushFailure`)
- **Severity**: warning
- **Issue**: No test covers the scenario where `git tag -l` itself returns a non-zero exit code. Every test in the class sets `tag -l` returncode to 0 (see `_fake_run_factory` line 996, and the custom `fake_run` at lines 1108–1110). Since the production code at line 613–614 doesn't check the returncode (Finding 1), this gap means the unchecked-error-path has zero test coverage.
- **Evidence**: The `_fake_run_factory` at line 994–996 always sets `r.returncode = 0` for the `tag -l` branch. The custom `fake_run` in `test_tag_create_failure` (lines 1108–1110) also returns rc=0 for `tag -l`. No test ever sets rc != 0 for the listing command.
- **Suggested fix**: Add a test (e.g., `test_tag_list_failure_aborts`) that has `["git", "tag", "-l", "vX.Y.Z"]` return rc=1 and asserts that the function returns before attempting tag creation, push, or counter reset. This test should be paired with the production fix from Finding 1.

---

### Finding 4

- **File**: references/scripts/cycle_post.py
- **Line**: 636–645 (push --tags failure path) and 597–600 (diff guard)
- **Severity**: warning
- **Issue**: Recovery gap — when `git push` succeeds but `git push --tags` fails, the commit lands on origin without its version tag. The function correctly returns without resetting `shipped-since-bump`. However, on the next cycle invocation the diff guard at line 597–600 will see no staged changes (the version files already match the bumped version), returncode 0, and print "no staged changes — skipping commit/tag/push" — the orphaned tag is never retried. Manual intervention is required to `git push --tags`.
- **Evidence**: Trace the retry scenario: (1) `config.md` already has the bumped version from line 579, (2) `git add` stages the same file content, (3) `git diff --cached --quiet` returns 0 because nothing changed, (4) guard at line 598–600 triggers and the function returns without attempting `git push --tags`. The error message at line 641 correctly identifies the state ("commit pushed but tag v{new_version} did NOT reach origin") but no code path ever recovers from it.
- **Suggested fix**: In the diff-guard early-return path (lines 598–600), or as a separate pre-push check, verify whether a local tag `v{new_version}` exists and whether it exists on origin. If the local tag exists but the remote doesn't, attempt `git push --tags` even when there are no staged changes. This turns the unrecoverable orphaned-tag state into a self-healing one.