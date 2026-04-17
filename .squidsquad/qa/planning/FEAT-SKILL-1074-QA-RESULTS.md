# FEAT-SKILL-1074 QA Results — Auto-merge PRs after QA passes

## Test Cases

### TC-1: Happy path — task PR auto-merges after QA pass
- **Result**: PASS (code-level)
- **Notes**: `pr_merge()` in `git_ops.py` correctly calls `gh pr merge --squash --delete-branch`. Returns `(True, "merged")` on success. Unit test `test_successful_squash_merge` confirms squash strategy and `--delete-branch` flag. The delivery-fallback sub-skill source file correctly describes the full flow: check config, check labels, find PR, call `pr_merge`, handle results.

### TC-2: Bug fix PR — always manual merge
- **Result**: PASS (code-level)
- **Notes**: The delivery-fallback sub-skill source (`references/sub-skills/pm-specific/delivery-fallback.md`) explicitly states auto-merge only triggers when the item is a **task** (`type:task`), NOT a bug fix (`type:issue`). The eligibility check is clearly documented in Step 0.

### TC-3: merge:manual label — task skips auto-merge
- **Result**: PASS (code-level)
- **Notes**: Delivery-fallback Step 0 lists `merge:manual` label check as an eligibility gate: "The item does NOT have the `merge:manual` label." If present, auto-merge is skipped. The `merge:manual` label exists on the repo (verified via `gh label list`).

### TC-4: merge:manual label added mid-flight
- **Result**: PASS (code-level)
- **Notes**: The sub-skill checks labels at merge time (when the task reaches pending-ship), not at task creation. The label query runs during the delivery step, so a label added mid-flight will be detected. This is implicit in the flow design (labels are queried at the moment of the merge decision).

### TC-5: PR already merged by human before PM auto-merge
- **Result**: PASS
- **Notes**: `pr_merge()` checks PR state first via `gh pr view --json state`. If state is `MERGED`, it returns `(True, "already merged")` without attempting merge. Unit test `test_already_merged` confirms this -- only 1 API call is made (no merge attempt). Delivery-fallback handles this: "Success (already merged or just merged)" proceeds to delivery.

### TC-6: Merge conflict — rebase flow
- **Result**: PASS
- **Notes**: `pr_merge()` detects "merge conflict" or "not mergeable" in stderr and returns `(False, "merge conflict")`. Unit test `test_merge_conflict` confirms. Delivery-fallback Step 0 handles this: routes back to dev agent, transitions status to in-progress, appends Discussion entry with conflict details.

### TC-7: Auto Merge config off — no auto-merge attempted
- **Result**: PASS (code-level)
- **Notes**: Delivery-fallback Step 0 checks `python references/scripts/config.py get auto-merge` first. If `no`, the entire auto-merge block is skipped. The config.py FIELD_MAP has the `auto-merge` key mapped to `("Auto Merge", "Enabled")`.

### TC-8: Branch workflow off — silent no-op
- **Result**: PASS (code-level)
- **Notes**: Delivery-fallback Step 0 requires `Branch Workflow: yes` as an eligibility condition. If branch workflow is off, "no PR exists" so auto-merge is silently skipped. This is explicitly stated: "Branch Workflow: yes (otherwise no PR exists -- silent no-op)."

### TC-9: DM present — PM merges, DM ships
- **Result**: PASS (code-level)
- **Notes**: The pr-flow sub-skill source (`references/sub-skills/pm-specific/pr-flow.md`) adds an "Auto-merge for pending-ship tasks" section that runs "regardless of PR Flow setting." When DM is present, PM auto-merges the PR in pr-flow (Step 6b), then DM picks up delivery. The merge/ship separation is clearly documented.

### TC-10: DM absent — PM merges AND ships
- **Result**: PASS (code-level)
- **Notes**: Delivery-fallback (Step 6d) handles this case. When no DM is present, PM runs auto-merge in Step 0, then performs delivery packaging (Steps 1-5) and marks shipped. All within the same step.

### TC-11: gh pr merge fails unexpectedly
- **Result**: PASS
- **Notes**: `pr_merge()` returns `(False, "merge failed: [error]")` for non-conflict failures. Unit test `test_unexpected_failure` confirms with "permission denied" error. Delivery-fallback Step 0 handles this: logs error, comments on issue, falls back to manual merge, leaves task as pending-ship. Does not retry.

### TC-12: New install default
- **Result**: FAIL
- **Notes**: The `## Auto Merge` section with `- **Enabled**: yes` exists on the `main` branch but was **deleted** from `config.md` on this feature branch. The git diff shows the section was removed (lines deleted, not added). This means the config field is missing on the branch. `python references/scripts/config.py get auto-merge` exits with error: "Field 'auto-merge' not found in config.md". The test `test_has_auto_merge` correctly catches this and FAILS.

### TC-13: Upgrade default
- **Result**: FAIL
- **Notes**: No upgrade script (`squidsquad-upgrade`) exists in the repository. There is no mechanism to add the `Auto Merge: no` field to existing installs during upgrade. This is an unimplemented requirement. The test plan specifies upgrade should add `Auto Merge: no` to preserve existing behavior, but no code exists to do this.

## Regression

### Test Suite Result
- **Total**: 927 tests collected
- **Passed**: 926
- **Failed**: 1 (`test_has_auto_merge`)
- **Failure cause**: `## Auto Merge` section missing from config.md on this branch. The section exists on main but was deleted in the feature branch commit `fd3172d`. This appears to be a rebase/merge artifact where the config.md changes were lost.

### Composition Gap
- **Critical**: The sub-skill source files (`delivery-fallback.md`, `pr-flow.md`) were updated with auto-merge logic, but `compose.py deploy-all` was NOT run. The deployed PM CLAUDE.md (`.squidsquad/pm/CLAUDE.md`) does not contain the auto-merge Step 0 or the pr-flow auto-merge section. The diff shows zero changes to `.squidsquad/pm/CLAUDE.md` on this branch. Without recomposition, the PM agent will not execute the auto-merge flow at runtime.

### Other Regression Checks
- **Post-merge recompose (Step 6e)**: Logic unchanged, still detects merged branches and runs `compose.py deploy-all`. No regression risk.
- **DM delivery flow**: Unchanged. DM still picks up pending-ship tasks.
- **Tracker transitions**: `pending-ship -> shipped` still requires DM role. No authority changes.
- **PR Flow monitoring**: pr-flow sub-skill source adds auto-merge as additive logic (runs regardless of PR Flow setting). No double-merge risk because `pr_merge()` checks state first -- if already merged, returns success without re-merging.

## Summary

| TC | Result | Critical Issue |
|----|--------|----------------|
| TC-1 | PASS | |
| TC-2 | PASS | |
| TC-3 | PASS | |
| TC-4 | PASS | |
| TC-5 | PASS | |
| TC-6 | PASS | |
| TC-7 | PASS | |
| TC-8 | PASS | |
| TC-9 | PASS | |
| TC-10 | PASS | |
| TC-11 | PASS | |
| TC-12 | FAIL | Auto Merge section deleted from config.md (rebase artifact) |
| TC-13 | FAIL | No upgrade script exists |

**Blocking issues (must fix before ship)**:
1. **config.md missing `## Auto Merge` section** -- The feature branch deleted it instead of preserving it. Must restore: `## Auto Merge\n\n- **Enabled**: yes`
2. **Composition not deployed** -- `compose.py deploy-all` must be run to inject the updated sub-skills into the PM's CLAUDE.md. Without this, the auto-merge logic exists only in reference files and will never execute.

**Non-blocking (can be follow-up)**:
3. **No upgrade script** -- TC-13 requires an upgrade mechanism to add `Auto Merge: no` to existing installs. This can be tracked as a separate task if upgrade tooling doesn't exist yet.
