# FEAT-PM-3663 Test Plan — Dev agent PR conflict resolution

## Test Cases

### TC-1: Conflicting PR detected and rebased
- **Precondition**: PR Flow on, dev agent has an open PR with merge conflicts
- **Steps**: Agent runs cycle
- **Expected**: Agent detects conflict, rebases onto main, force-pushes, logs it
- **Verification**: PR shows mergeable on GitHub, iteration log mentions rebase

### TC-2: Clean PR — no action
- **Precondition**: PR Flow on, dev agent has an open PR with no conflicts
- **Steps**: Agent runs cycle
- **Expected**: No rebase attempted, no log entry for this PR
- **Verification**: PR unchanged, no rebase in iteration log

### TC-3: PR Flow off — skip entirely
- **Precondition**: PR Flow off, dev agent has open PRs
- **Steps**: Agent runs cycle
- **Expected**: No PR check at all
- **Verification**: No PR-related entries in iteration log

### TC-4: No open PRs — skip silently
- **Precondition**: PR Flow on, no open PRs for this agent
- **Steps**: Agent runs cycle
- **Expected**: Check runs, finds nothing, moves on
- **Verification**: No error, clean cycle

### TC-5: Only own PRs checked
- **Precondition**: PR Flow on, open PRs exist for skill AND qa
- **Steps**: Skill agent runs cycle
- **Expected**: Only checks squidsquad/skill/* branches, ignores squidsquad/qa/*
- **Verification**: No action on QA's PRs

### TC-6: Rebase failure — code conflict
- **Precondition**: PR has a real code conflict that can't auto-resolve
- **Steps**: Agent attempts rebase
- **Expected**: Rebase aborted, comment on PR: "Rebase failed — manual resolution needed", skip this PR
- **Verification**: PR still conflicting, comment posted, agent continues cycle

## Smoke Tests
- [ ] git-commit sub-skill contains PR conflict check step
- [ ] Step is gated on PR Flow config
- [ ] Step filters by own role branches only

## Regression Risks
- Force-push accidentally overwriting commits from other agents (mitigated by own-branch filter)
- Rebase loop if conflict can't be resolved

## Comprehension Questions
### CQ-1: When does a dev agent check for PR conflicts?
- **Files**: git-commit sub-skill
- **Expected**: Each cycle when PR Flow is on, before implementing new work. Only checks own branches (squidsquad/<role>/*).
