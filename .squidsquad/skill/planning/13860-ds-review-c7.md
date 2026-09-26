### Finding 1

- **File**: references/scripts/git_ops.py
- **Line**: 1017-1019 (merge gate), 1689-1695 (`_is_capture_note`), 2681-2691 (`_guard_exempt`)
- **Severity**: error
- **Issue**: The capture-at-ship exemption is based only on the **final file content** containing `#<n>`. It never compares the PR head against the base, so a feature branch for issue N can ship destructive or unrelated edits to an existing vault note as long as `#N` appears somewhere in the resulting file (including a citation that already existed on `main`). This reopens the #13554 state-leak class: the merge gate will pass a squash that reverts/deletes teammate vault content, and the #11511 pre-commit guard will leave that same staged file on the branch.
- **Evidence**: `_pr_state_scope_violations` exempts `f` when `_is_capture_note_path(f) and _is_capture_note(f, issue, _pr_file_text(pr_number, f))`. `_pr_file_text` reads only the PR head blob, not `baseRefName`/`origin/<working>`. `_is_capture_note` requires only `text is not None` and `_cites_issue(text, issue)`. Likewise `_guard_exempt` reads only the staged blob via `git show :{path}`. A note on `main` that already cites `#13860` can therefore be edited on `squidsquad/task/13860` to delete arbitrary content while keeping the citation, and both guards pass it. This contradicts the guard's own claim that a branch "can neither carry an unrelated vault edit nor delete a note" (lines 1691-1693).
- **Suggested fix**: Make the exemption diff-aware. In the pre-commit guard, exempt a capture note only if the path is newly added or `git diff --cached origin/<working> -- <path>` shows no removed base lines. In the merge gate, fetch the base blob (`baseRefName`) as well as the head blob and exempt only when the file is newly added or the base text is a prefix/subset of the head text (additive-only). At minimum, require the `#<n>` citation to be introduced by lines added in the PR, not present in the base version.

### Finding 2

- **File**: references/scripts/git_ops.py
- **Line**: 1635-1641 (`_issue_from_branch`), used at 1644-1650 (`_pr_head_issue`) and 2735 (`guard_staged_state`)
- **Severity**: warning
- **Issue**: `_issue_from_branch` hardcodes the branch shape `squidsquad/task/<n>`. The supported configurable branch pattern `squidsquad/{role}/{number}` (implemented by `get_branch_name`, lines 2409-2423, and covered by `test_custom_pattern_with_role`) is not recognized, so `branch_issue`/`_pr_head_issue` return `None`. With such a configured pattern, every lineage file and capture-at-ship vault note is stripped by `guard_staged_state` and refused by `_pr_state_scope_violations`.
- **Evidence**: `get_branch_name` returns `squidsquad/skill/99` when `branch-pattern` is `squidsquad/{role}/{number}`. `_issue_from_branch("squidsquad/skill/99")` returns `None` because it only checks the prefix `squidsquad/task/`. Notably, `pr_merge` itself already parses the issue correctly from any `squidsquad/<...>/<n>` branch at lines 1505-1507 (`parts[-1].isdigit()`), so the pre-merge guard is inconsistent with the rest of the same file.
- **Suggested fix**: Replace the hardcoded prefix with the same last-segment parse used at lines 1505-1507, e.g. require `parts[0] == "squidsquad"`, `len(parts) >= 2`, and `parts[-1].isdigit()`, then return `int(parts[-1])`. That handles both `squidsquad/task/<n>` and `squidsquad/<role>/<n>`.

### Finding 3

- **File**: references/scripts/vault_consume.py
- **Line**: 369
- **Severity**: warning
- **Issue**: `select_merge_target` treats a result with a missing `direct` field as a direct hit: `not hit.get("direct", True)` evaluates to `False`, so the result is not skipped. The selector contract says a hit qualifies only if it is a DIRECT result, so an absent `direct` flag should fail closed, not pass.
- **Evidence**: The docstring at lines 362-365 states "(a) it is a DIRECT result" is a required qualification. The engine's public JSON currently always emits `direct`, but if a stale/malformed engine payload omits the field, this code will still consider filename/wikilink/tag-tier entries as valid merge targets, potentially selecting a `create` vs `update` action incorrectly.
- **Suggested fix**: Use `if hit.get("direct") is not True or hit.get("tier") not in MERGE_TIERS: continue` so only an explicit boolean `True` satisfies the direct-hit requirement.