# FEAT-SKILL-246 Context — PR-Driven Workflow Mode

## Scope

When PR Flow is enabled, dev agents create PRs instead of merging directly. Human reviews and merges. QA approves formally on the PR. All discussion moves to PR comments once a PR is open. Agents monitor PR comments and react to feedback.

## Locked Decisions (human decided)

- **New status**: `pending-review` between pending-test and pending-ship. QA verified, human has not reviewed.
- **QA formal review**: QA uses `gh pr review --approve` (enables branch protection rules).
- **Auto-close**: PR body includes `Closes #N` — issue auto-closes on merge. PM catches up within one cycle.
- **Everything through PRs**: bugs and tasks both go through PR review. Simplify later if too heavy.
- **Branch protection**: not auto-set. Document as recommended step. Human controls repo settings.
- **Opt-in mandatory human approval**: new config toggle. When enabled, QA skips the approval step during planning — human approves via PR review instead of the planning gate.
- **Discussion moves to PR**: once a PR is open, all discussion happens on PR comments (not just the issue). Agents post and monitor comments on the PR.
- **Code review summary**: agent posts a structured summary comment on the PR — what changed, why, key decisions, files touched.
- **Agents monitor PR comments**: dev agent watches for human feedback, requested changes, questions. Reacts accordingly (fix requested changes, answer questions, update code).

## Dev Discretion (dev agent can choose)

- PR body template details (beyond required sections)
- Code review summary format
- How frequently to poll PR comments (every cycle vs on-demand)
- Whether to re-request review after pushing fixes

## Side Effect Mitigations (required)

- PR Flow requires Branch Workflow (#375) — config.py should enforce this dependency
- When PR Flow is off, current direct-merge behavior unchanged
- PM Step 6b already monitors PRs — enhance, don't replace
- Issue discussion continues for non-PR items (planning, pre-branch work)

## Upgrade Path (required)

- New label: `status:pending-review`
- New config: `Mandatory Human Approval: yes/no` (default: no)
- PR Flow toggle: `yes` activates the full flow
- Existing installs: PR Flow: no by default, opt-in
- Backward compatible — no change unless toggled on

## Out of Scope

- CI/GitHub Actions integration (future enhancement)
- Auto-merge after approval (human merges manually)
- Branch protection setup automation
