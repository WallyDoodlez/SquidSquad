# FEAT-SKILL-1074 Context — Auto-merge PRs after QA passes

## Scope

After QA verifies zero gaps and PM marks a task pending-ship, PM auto-merges the PR via `gh pr merge --squash`. Bug fix PRs always require manual human merge. Per-task opt-out via `merge:manual` label.

## Locked Decisions (human decided)

- **Default for new installs**: `Auto Merge: yes` — new projects get auto-merge out of the box
- **Default for upgrades**: `Auto Merge: no` — existing installs opt in manually
- **DM handoff**: PM merges the PR, DM handles delivery packaging and `pending-ship → shipped` transition. Clean separation of merge vs. ship.
- **No branches**: When branch workflow is off, auto-merge is a silent no-op. No error, no warning.
- **Label timing**: `merge:manual` label checked at merge time, not creation time. Human can add/remove anytime.
- **Bug PRs**: Always manual merge — no auto-merge regardless of config
- **Merge strategy**: Squash merge (`gh pr merge --squash`)

## Dev Discretion (dev agent can choose)

- How to detect the associated PR for a task (parse branch name `squidsquad/skill/[NUMBER]`, or store PR URL in tracker discussion)
- Error message format for merge failures
- Whether to add `merge:manual` label creation to setup script or create on first use

## Side Effect Mitigations (required)

- Check PR state before merge attempt — if already merged by human, skip and proceed
- On merge conflict: comment on issue, route back to skill to rebase, QA re-verifies, PM retries
- On unexpected `gh pr merge` failure: log error, fall back to manual merge, comment on issue

## Upgrade Path (required)

- Add `Auto Merge: no` to config.md during upgrade (preserves existing behavior)
- Create `merge:manual` label on GitHub repo
- No template changes break existing behavior — auto-merge only activates when config is `yes`

## Out of Scope

- Auto-merge for bug fix PRs (explicitly excluded)
- Changes to tracker.py authority model (PM merges PR, DM still owns shipped transition)
- Branch protection rule detection (edge case — SquidSquad repos typically don't use branch protection)
- Auto-merge for non-SquidSquad PRs
