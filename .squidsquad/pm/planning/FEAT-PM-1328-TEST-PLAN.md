# FEAT-PM-1328 Test Plan — Skip blocked:human-action in verification

## Test Cases

### TC-1: PM skips blocked item in Step 5 (issue verification)
- **Precondition**: Issue at pending-test with `blocked:human-action` label
- **Steps**: Run PM verification step (Step 5)
- **Expected**: Item skipped with log note, no status change, no verification attempted
- **Verification**: Check iteration log for skip message, verify issue status unchanged

### TC-2: PM skips blocked item in Step 6 (task verification)
- **Precondition**: Task at pending-test with `blocked:human-action` label
- **Steps**: Run PM verification step (Step 6)
- **Expected**: Same as TC-1
- **Verification**: Same as TC-1

### TC-3: QA skips blocked item
- **Precondition**: Item at pending-test with `blocked:human-action` label
- **Steps**: QA verification cycle runs
- **Expected**: Item skipped, no bounce to in-progress
- **Verification**: Check QA iteration log

### TC-4: Normal item still verified
- **Precondition**: Item at pending-test WITHOUT blocked label
- **Steps**: PM/QA verification runs
- **Expected**: Normal verification proceeds
- **Verification**: Item processed normally

### TC-5: Label removed — item gets verified next cycle
- **Precondition**: Item was blocked, human removes label
- **Steps**: Next verification cycle
- **Expected**: Item now processed normally
- **Verification**: Verification runs, item progresses

## Smoke Tests
- [ ] Sub-skill text contains `blocked:human-action` check
- [ ] grep for label check in both PM and QA verification sub-skills

## Regression Risks
- Verification accidentally skipping non-blocked items
- Label name mismatch (typo in the check)

## Comprehension Questions
### CQ-1: What should a PM agent do when it encounters a pending-test item with blocked:human-action?
- **Files**: PM verification sub-skill
- **Expected**: Skip it with a one-line log note, no status change, move to next item
