## FEAT-SKILL-012 — PR-based approval flow for completed features

- **Priority**: High
- **Status**: Shipped
- **Owner**: skill-lead
- **Description**: **Optional, configurable at setup.** Instead of pushing completed work directly to main, dev agents should create a PR for each feature or bug fix when it reaches `Pending Test` status. The human reviews and approves by merging the PR in GitHub. Comments left on the PR are referenced back in the feature/bug tracker's Discussion section. This integrates SquidSquad into the standard GitHub code review workflow. This feature is opt-in — setup Step 1 should prompt: "Use PR-based approval flow? (requires `gh` CLI) [y/N]". The choice is stored in `config.md` as `PR Flow: enabled/disabled`. When disabled, agents push directly to main as before.

  **Flow (when enabled):**
  1. Dev agent completes a feature/bug fix → creates a branch (e.g. `squidsquad/feat-skill-008`) and opens a PR via `gh pr create`
  2. Status updates to `Pending Test` with the PR link in the Discussion
  3. PM/QA verifies the change and adds a review comment or approval
  4. Human reviews the PR on GitHub — can approve, request changes, or leave comments
  5. If human leaves PR comments: PM picks them up via `gh pr view` and appends them to the feature's Discussion section
  6. If human merges the PR: PM detects the merge and updates status to `Shipped`
  7. If human requests changes: PM updates status back to `In Progress` with the feedback

- **Acceptance Criteria**:
  - [ ] Dev agent Ralph Loop creates a feature branch and PR when marking work as `Pending Test`
  - [ ] PR title and body reference the feature/bug ID and include acceptance criteria
  - [ ] PR link is recorded in the tracker Discussion
  - [ ] PM/QA Ralph Loop checks for PR comments via `gh api` or `gh pr view` and appends new comments to the tracker Discussion
  - [ ] PM/QA detects merged PRs and updates feature status to `Shipped`
  - [ ] PM/QA detects PRs with requested changes and updates status back to `In Progress` with feedback
  - [ ] Both dev and PM/QA CLAUDE.md templates updated with the PR workflow
  - [ ] SKILL.md documents the PR-based approval flow
  - [ ] Git protocol section updated with branching convention (e.g. `squidsquad/feat-xxx`, `squidsquad/bug-xxx`)
  - [ ] Works with `gh` CLI (GitHub CLI) — documented as a prerequisite
  - [ ] Setup Step 1 includes a prompt: "Use PR-based approval flow? (requires `gh` CLI) [y/N]"
  - [ ] Choice stored in `config.md` as `PR Flow: enabled/disabled`
  - [ ] When disabled, agents push directly to main (current behavior unchanged)
  - [ ] Can be toggled post-setup by editing `config.md`

### Discussion

> [2026-03-28 03:40] **pm/qa**: Filed from human request. Integrates SquidSquad into GitHub's PR review flow — human approves by merging, comments flow back to tracker Discussion. Status: Pending — awaiting human approval.
> [2026-03-28 03:45] **pm/qa**: Human approved. Status → Approved.
> [2026-03-28 03:30] **skill-lead**: Picking up. Status → In Progress.
> [2026-03-28 03:45] **skill-lead**: Complete. Added PR flow prompt to Setup Step 1, PR Flow config to config.md template, branching convention and PR flow docs to Git Protocol in SKILL.md. Dev template Step 5 branches+PRs when enabled. PM template Step 6b monitors PRs via `gh`. Config toggleable. CHANGELOG updated. Status → Pending Test.
> [2026-03-28 03:55] **pm/qa**: Human feedback: this must be opt-in, not default. Setup Step 1 should prompt for it. Config stores the choice as `PR Flow: enabled/disabled`. When disabled, current push-to-main behavior is unchanged.
> [2026-03-28 04:10] **pm/qa**: QA verified — all criteria pass. Opt-in at setup, config toggle, branch+PR flow in dev template, PM monitors PRs. Status → Shipped.
> [2026-04-01 01:15] **migration**: Migrated from monolithic features.md to individual file (Schema 2 -> 3).
