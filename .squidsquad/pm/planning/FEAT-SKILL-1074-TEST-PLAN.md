# FEAT-SKILL-1074 Test Plan — Auto-merge PRs after QA passes

## Test Cases

### TC-1: Happy path — task PR auto-merges after QA pass
- **Precondition**: Branch workflow on, Auto Merge: yes, task has a PR open, QA verified zero gaps
- **Steps**: PM marks task pending-ship. PM delivery step detects open PR. PM calls `gh pr merge --squash`.
- **Expected**: PR is squash-merged. Branch is deleted. PM proceeds to delivery/shipping.
- **Verification**: `gh pr view [N] --json state` returns MERGED. Branch no longer exists on remote.

### TC-2: Bug fix PR — always manual merge
- **Precondition**: Auto Merge: yes, issue (type:issue) has a PR open, QA verified
- **Steps**: PM marks issue pending-ship.
- **Expected**: PM does NOT attempt auto-merge. PR stays open for human to merge.
- **Verification**: `gh pr view [N] --json state` returns OPEN. Discussion comment says "Bug fix — manual merge required."

### TC-3: merge:manual label — task skips auto-merge
- **Precondition**: Auto Merge: yes, task has `merge:manual` label, PR open
- **Steps**: PM marks task pending-ship.
- **Expected**: PM detects `merge:manual` label, skips auto-merge. PR stays open.
- **Verification**: `gh pr view [N] --json state` returns OPEN. Discussion notes manual merge required.

### TC-4: merge:manual label added mid-flight
- **Precondition**: Task in-progress, no merge:manual label initially. Human adds label while task is being worked on.
- **Steps**: QA passes, PM marks pending-ship, PM checks labels at merge time.
- **Expected**: PM sees merge:manual, skips auto-merge.
- **Verification**: Same as TC-3. Confirms label is checked at merge time, not creation time.

### TC-5: PR already merged by human before PM auto-merge
- **Precondition**: Auto Merge: yes, task PR exists, human merges it before PM cycle runs
- **Steps**: PM marks pending-ship, attempts auto-merge, detects PR already merged.
- **Expected**: PM skips merge (already done), proceeds to delivery/shipping. No error.
- **Verification**: Discussion comment says "PR already merged. Proceeding to delivery."

### TC-6: Merge conflict — rebase flow
- **Precondition**: Auto Merge: yes, task PR has merge conflicts with main
- **Steps**: PM attempts `gh pr merge --squash`. Merge fails.
- **Expected**: PM detects failure, comments on issue with conflict details, routes back to skill to rebase. Task status returns to in-progress.
- **Verification**: Issue has discussion comment about merge conflict. Status is in-progress. Skill agent's next cycle picks up the rebase.

### TC-7: Auto Merge config off — no auto-merge attempted
- **Precondition**: Auto Merge: no, task has PR open, QA passes
- **Steps**: PM marks pending-ship.
- **Expected**: PM skips auto-merge entirely. PR stays open for human.
- **Verification**: No `gh pr merge` call made. PR state is OPEN.

### TC-8: Branch workflow off — silent no-op
- **Precondition**: Branch Workflow: no, Auto Merge: yes
- **Steps**: Task completes, QA passes, PM marks pending-ship.
- **Expected**: No PR exists. Auto-merge is silently skipped. Delivery proceeds normally.
- **Verification**: No merge-related discussion comments. Task ships normally.

### TC-9: DM present — PM merges, DM ships
- **Precondition**: DM agent installed, Auto Merge: yes, task PR open
- **Steps**: QA passes, PM marks pending-ship, PM auto-merges PR. DM picks up delivery.
- **Expected**: PM merges the PR. DM handles delivery packaging and `pending-ship → shipped` transition.
- **Verification**: PR is MERGED (by PM). Shipped transition comment is from DM. Clean separation.

### TC-10: DM absent — PM merges AND ships
- **Precondition**: No DM agent, Auto Merge: yes, task PR open
- **Steps**: QA passes, PM marks pending-ship, PM auto-merges PR, PM does delivery fallback.
- **Expected**: PM merges PR, then performs delivery packaging and marks shipped.
- **Verification**: PR is MERGED. Shipped transition and delivery comments are from PM.

### TC-11: gh pr merge fails unexpectedly
- **Precondition**: Auto Merge: yes, PR open, `gh pr merge` returns non-zero for unexpected reason (network, permissions)
- **Steps**: PM attempts merge.
- **Expected**: PM logs error, comments on issue, falls back to manual merge. Does NOT retry automatically this cycle.
- **Verification**: Issue has error comment. PR stays OPEN. Task remains pending-ship.

### TC-12: New install default
- **Precondition**: Fresh SquidSquad setup
- **Steps**: Run setup, check config.md
- **Expected**: `Auto Merge: yes` is present in config.md
- **Verification**: Read config.md, confirm setting exists with value `yes`.

### TC-13: Upgrade default
- **Precondition**: Existing install without Auto Merge setting
- **Steps**: Run squidsquad-upgrade
- **Expected**: `Auto Merge: no` is added to config.md (preserves existing behavior)
- **Verification**: Read config.md, confirm setting exists with value `no`.

## Verification Method

**Primary: Comprehension test** — Spawn a fresh agent with no prior context. Point it at the modified delivery-fallback sub-skill, git_ops.py, and config.md. Ask the comprehension questions below. If the agent answers all correctly, logic is clear and implemented right. If it gets any wrong, the implementation is buggy or ambiguous.

**Secondary: Happy path smoke test** — One real end-to-end run of TC-1 (create a test branch/PR, let PM auto-merge it). Confirms runtime behavior, not just logic.

### Comprehension Questions (derived from TCs)

1. "What happens when a task PR is ready to ship and Auto Merge is yes?" (TC-1)
2. "A bug fix just passed QA and Auto Merge is yes. Does the PR auto-merge?" (TC-2)
3. "A task has the merge:manual label. What happens at ship time?" (TC-3)
4. "Someone adds merge:manual to a task that's already in-progress. Does it take effect?" (TC-4)
5. "The human already merged the PR before PM's cycle ran. What does PM do?" (TC-5)
6. "The PR has merge conflicts. Walk me through what happens." (TC-6)
7. "Auto Merge is set to no. What happens to task PRs?" (TC-7)
8. "Branch workflow is off but Auto Merge is yes. What happens?" (TC-8)
9. "DM is present. Who merges the PR and who marks it shipped?" (TC-9)
10. "DM is absent. Who does what?" (TC-10)
11. "gh pr merge fails with an unexpected error. What's the fallback?" (TC-11)
12. "What's the default Auto Merge value for new installs vs upgrades?" (TC-12, TC-13)

**Pass criteria**: Agent answers all 12 correctly without hints. Any wrong answer = implementation gap.

## Smoke Tests

- [ ] Config field `Auto Merge` exists and is readable by `config.py get auto-merge`
- [ ] `merge:manual` label can be created on repo via `gh label create`
- [ ] `gh pr merge --squash` works on a test PR (manual dry run)
- [ ] Post-merge recompose still fires correctly after auto-merged PR

## Regression Risks

- **Post-merge recompose**: Verify Step 6e still detects merged branches regardless of who merged (human vs PM)
- **DM delivery flow**: Verify DM still picks up pending-ship tasks and ships them even when PR was auto-merged by PM
- **Tracker transitions**: Verify `pending-ship → shipped` still requires DM role (no unintended authority changes)
- **PR Flow monitoring**: If PR Flow is later enabled, verify it doesn't conflict with auto-merge (double-merge risk)
