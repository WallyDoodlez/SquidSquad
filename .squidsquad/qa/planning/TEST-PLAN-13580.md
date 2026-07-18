# TEST-PLAN-13580 — pr_merge state-scope gate: split-hint for self-exemption PRs

**Source**: GitHub issue #13580 body + Discussion triage (skill scoped this ticket to option (b): when the #13554 refusal fires AND the refused PR's own diff touches `_is_launcher_script`/`_is_state_file` (i.e. `references/scripts/git_ops.py`), extend the refusal message with the two-PR split hint).
**Derived without reading the diff.**

## Acceptance Criteria (derived from issue body + accepted triage scope)

- **AC1**: When `pr_merge` refuses a PR under the #13554 state/vault-scope guard, AND the refused PR's own declared files include `references/scripts/git_ops.py` (the classifier module), the printed error message contains a hint identifying #13580 and describing the two-PR split recipe (allow-list extension first, content fix as a follow-up PR).
- **AC2**: When the refused PR's declared files do NOT include `references/scripts/git_ops.py`, the message is unchanged — no split-hint noise for unrelated violations.
- **AC3 (non-regression)**: The main-tip evaluation design (`_pr_state_scope_violations` evaluates the CURRENTLY-CHECKED-OUT version of the classifier, not the PR branch's own version) is untouched — a PR still cannot exempt itself by editing the classifier on its own branch.
- **AC4 (fail-safe)**: If `_pr_declared_files` cannot determine the file set (returns `None`, e.g. a `gh` hiccup), the split-hint is silently skipped but the original refusal still fires — no crash, no false hint.

## Test Cases

### TC-1 (covers AC1): Live refusal + classifier touch produces the split-hint
- **Precondition**: A real open PR that declares `references/scripts/git_ops.py` in its changed files (PR #13586 for #13580 itself qualifies).
- **Steps**: Call the real `git_ops.pr_merge(13586)` with only `_pr_state_scope_violations` mocked to force a violation; leave `_pr_declared_files` REAL (hits live `gh pr view --json files` against PR #13586).
- **Expected**: `success=False`; stderr contains `#13580` and `Split it`.
- **Verification command**: ad-hoc Python script calling `git_ops.pr_merge(13586)` with only the violation mocked.

### TC-2 (covers AC2): Live refusal without classifier touch omits the hint
- **Precondition**: Same PR, but declared files patched to exclude `git_ops.py` (isolates the one variable).
- **Steps**: Call `git_ops.pr_merge(13586)` with `_pr_state_scope_violations` and `_pr_declared_files` both mocked (declared set has no `git_ops.py`).
- **Expected**: `success=False`; stderr does NOT contain `#13580`.
- **Verification command**: ad-hoc Python script, negative control.

### TC-3 (covers AC3): Classifier-evaluation site unchanged
- **Precondition**: n/a — diff review.
- **Steps**: Diff `references/scripts/git_ops.py` between `origin/main` and the branch; confirm `_pr_state_scope_violations`, `_is_launcher_script`, `_is_state_file` bodies are byte-identical (only the message-building block after the refusal is touched).
- **Expected**: No changes to the classifier functions themselves.
- **Verification command**: `git diff origin/main...squidsquad/task/13580 -- references/scripts/git_ops.py`

### TC-4 (covers AC4): Worker's own fail-open unit test
- **Precondition**: n/a.
- **Steps**: Run `test_split_hint_fail_open_when_declared_none` from the worker's suite as a sanity check (mocked `_pr_declared_files` returns `None`).
- **Expected**: PASS.
- **Verification command**: `python -m pytest tests/test_git_ops.py -k split_hint_fail_open`

### TC-5: No real-world side effect from verification
- **Precondition**: PR #13586 starts OPEN, not merged.
- **Steps**: After TC-1/TC-2, re-query PR #13586 state.
- **Expected**: Still OPEN, `mergedAt` null — verification calls never triggered a real merge (state-violation branch returns before any `gh pr merge` call).
- **Verification command**: `gh pr view 13586 --json state,mergedAt`

### TC-6: Full regression suite + static gate
- **Steps**: `python -m pytest tests/test_git_ops.py -k "13580 or split_hint or classifier_touch"` and `python tests/run_tests.py static` on the branch (merged with current main).
- **Expected**: All green; no new failures vs. current main baseline.

## Coverage matrix
- AC1 → TC-1
- AC2 → TC-2
- AC3 → TC-3
- AC4 → TC-4
- (non-AC) → TC-5, TC-6

No LLM-consumed instructions touched by this change (git_ops.py is code, not a CLAUDE.md/sub-skill fragment) — no Comprehension Questions section required.
