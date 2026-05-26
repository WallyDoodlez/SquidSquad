Now I have all the context needed. Let me compile my findings.

---

```
### Finding 1

- **File**: references/sub-skills/roles/dm/delivery-packaging.md
- **Line**: 48
- **Severity**: warning
- **Issue**: `gh pr view` failure is not handled — if the command fails (network error, rate limiting, PR deleted), `PR_BASE` will be an empty string. The comparison `"" != "$WORKING_BRANCH"` (e.g. `"" != "main"`) will evaluate to true, causing a false-positive route-back to `in-progress` even when the PR's base branch is correct.
- **Evidence**: The `WORKING_BRANCH` assignment on line 47 has a fallback (`|| echo "main"`), but `PR_BASE` on line 48 has no fallback or error check. If `gh pr view` exits non-zero or produces no output, `PR_BASE` is empty and the inequality on line 51 fires incorrectly. The existing protocol elsewhere already has a pattern for handling `gh` command failures (e.g., the merge-failure path on lines 76-80 explicitly checks `success: false`), but this new gate omits any error guard.
- **Suggested fix**: Add an empty-guard before the comparison. Either:
  ```bash
  if [ -z "$PR_BASE" ]; then
    # gh pr view failed — skip the base check, proceed to citation gate
  elif [ "$PR_BASE" != "$WORKING_BRANCH" ]; then
    # route back
  fi
  ```
  Or check the exit code of `gh pr view` directly:
  ```bash
  PR_BASE=$(gh pr view [PR_NUMBER] --json baseRefName -q .baseRefName) || PR_BASE=""
  ```
  and then gate on `[ -z "$PR_BASE" ]` to skip the check on failure.
```

### Finding 2

- **File**: references/sub-skills/roles/dm/delivery-packaging.md
- **Line**: 51-56
- **Severity**: warning
- **Issue**: The route-back remediation tells the worker to "Rebase onto `$WORKING_BRANCH`" but never instructs the worker to change the PR's target base branch on GitHub. A git rebase only rewrites local history; the GitHub PR's `baseRefName` is metadata that remains pointing at the old parent branch. When the worker re-routes to `pending-ship` and DM picks it up again, `gh pr view --json baseRefName` will still return the old parent branch, causing an infinite loop of route-backs.
- **Evidence**: The comment on line 54 says "Rebase onto `$WORKING_BRANCH` (or wait for the parent to merge first) and re-route to pending-ship." But rebasing the git branch does not change the PR's base on GitHub — that requires `gh pr edit --base <branch>` or closing and opening a new PR. No existing worker protocol (worker/implement-tasks.md, worker/triage-issues.md) contains instructions for retargeting a PR. A grep for `gh pr edit` and `retarget` across `references/` returns zero matches. The "wait for the parent to merge first" alternative is valid, but the "rebase" path as written will not resolve the trap.
- **Suggested fix**: Update the route-back comment to include the PR-retarget step:
  ```
  Rebase onto `$WORKING_BRANCH`, edit the PR base (`gh pr edit [PR_NUMBER] --base $WORKING_BRANCH`), and re-route to pending-ship.
  ```
  Or alternatively instruct the worker to close the stacked PR and open a new one targeting `$WORKING_BRANCH`.

### Finding 3

- **File**: tests/test_feat_6126_harness_merge.py
- **Line**: 353-376 (`test_dm_delivery_routes_back_on_stacked_pr`)
- **Severity**: warning
- **Issue**: The test verifies that the route-back block contains `pending-ship in-progress` and `rebase`, but does not verify that the block contains a "skip this item" instruction. Without that instruction, the DM agent would execute the route-back transition but then continue falling through to the citation gate and merge request on the same stacked PR, defeating the gate's purpose.
- **Evidence**: The protocol on line 56 ends the stacked-PR block with "Skip this item and move to the next." The test extracts `block = content[base_check_idx:citation_idx]` (line 370) and asserts `pending-ship in-progress` and `rebase` are present, but never asserts that `Skip this item` or `move to the next` is in the block. If someone edits the protocol and accidentally drops the skip instruction, this test would still pass.
- **Suggested fix**: Add an assertion for the skip instruction:
  ```python
  assert "Skip this item" in block or "move to the next" in block, (
      "the stacked-PR route-back must include a skip/move-to-next "
      "instruction so the DM does not proceed to the citation gate"
  )
  ```

### Finding 4

- **File**: tests/test_feat_6126_harness_merge.py
- **Line**: 333-376 (both new tests)
- **Severity**: warning
- **Issue**: Both tests are purely static "string in file" checks. Neither test validates the actual comparison logic (`$PR_BASE != $WORKING_BRANCH`) is present in the protocol. A future edit could change the comparison to `$PR_BASE == $WORKING_BRANCH` (inverting the logic) and the tests would still pass because `PR_BASE` and `baseRefName` would still appear in the file.
- **Evidence**: `test_dm_delivery_has_stacked_pr_base_check` (line 333) checks for presence of strings `baseRefName`, `PR_BASE`, and `10287` but not the inequality operator. `test_dm_delivery_routes_back_on_stacked_pr` (line 353) checks ordering and route-back strings but not the comparison. The actual gate logic `$PR_BASE != $WORKING_BRANCH` is untested.
- **Suggested fix**: Add a test that verifies the comparison syntax appears in the base-check block:
  ```python
  def test_dm_delivery_has_correct_comparison(self):
      path = REPO_ROOT / "references" / "sub-skills" / "roles" / "dm" / "delivery-packaging.md"
      content = path.read_text(encoding="utf-8")
      # Must compare PR_BASE against WORKING_BRANCH with inequality
      assert "$PR_BASE" in content and "$WORKING_BRANCH" in content
      # The inequality must exist in proximity to the variables
      assert "!=" in content or "-ne" in content
  ```
  Or stronger: extract the block and assert the specific bash comparison pattern is present.

### Finding 5

- **File**: tests/test_feat_6126_harness_merge.py
- **Line**: 333-376 (both new tests)
- **Severity**: warning
- **Issue**: No test covers the "base check passes" (happy path) scenario — when `PR_BASE == WORKING_BRANCH`, the protocol should proceed to the citation gate. The current tests only verify detection and route-back exist. If the protocol were edited to always route back (regardless of the comparison outcome), no test would catch it.
- **Evidence**: `test_dm_delivery_has_stacked_pr_base_check` checks for string presence. `test_dm_delivery_routes_back_on_stacked_pr` checks ordering of `baseRefName` before `Gate #4` and the route-back semantics within the block. Neither test verifies that the pass case ("If the base check passes, apply the contract-citation soft gate") is gated on the comparison result rather than being unconditional. The protocol line 58 says "If the base check passes, apply the contract-citation soft gate" — but nothing in the tests verifies this is structurally dependent on the `$PR_BASE != $WORKING_BRANCH` check rather than just being sequentially after it.
- **Suggested fix**: Add a test that verifies the "If the base check passes" text appears *after* the route-back block and *before* the citation gate, confirming the pass case is a distinct branch:
  ```python
  def test_dm_delivery_base_check_has_pass_branch(self):
      path = REPO_ROOT / "references" / "sub-skills" / "roles" / "dm" / "delivery-packaging.md"
      content = path.read_text(encoding="utf-8")
      base_pass_idx = content.find("If the base check passes")
      route_back_idx = content.find("pending-ship in-progress")
      assert base_pass_idx > route_back_idx, (
          "the pass branch must appear after the route-back, confirming "
          "it is the alternative path, not unconditional fallthrough"
      )
  ```
```

### Finding 6

- **File**: references/sub-skills/roles/dm/delivery-packaging.md
- **Line**: 42, 48
- **Severity**: warning
- **Issue**: The `gh pr list` command on line 42 now requests `baseRefName` in its JSON output, but the protocol never uses that field from the list response. Instead, a second `gh pr view` call on line 48 retrieves `baseRefName` separately. This means the `baseRefName` field added to the list command is dead data — the protocol makes an extra, unnecessary GitHub API call while the data is already available. More importantly, this creates a subtle risk: if the `gh pr view` call on line 48 fails (see Finding 1), the protocol has no fallback to use the `baseRefName` already retrieved by the `gh pr list` command.
- **Evidence**: Line 42 adds `baseRefName` to `--json number,headRefName,baseRefName,body`. Line 48 makes a completely independent `gh pr view [PR_NUMBER] --json baseRefName -q .baseRefName` call. The list output is never parsed for `baseRefName`. This is both redundant (extra API call) and misses an opportunity to have a fallback when `gh pr view` fails.
- **Suggested fix**: Either (a) remove `baseRefName` from the `gh pr list` command if it's not going to be used, or (b) prefer extracting `baseRefName` from the list output directly (removing the separate `gh pr view` call), or (c) use the list's `baseRefName` as a fallback when `gh pr view` fails. Option (a) is simplest and avoids confusion about why the field is requested but unused.