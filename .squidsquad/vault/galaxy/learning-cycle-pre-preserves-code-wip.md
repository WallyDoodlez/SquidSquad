---
type: learning
tags: [git, workflow, reboot, context-pressure, cycle_pre, wip]
created: 2026-06-14
updated: 2026-06-14
owner: skill-lead
status: active
confidence: high
source: observation
links: [learning-resume-git-tree-is-truth, learning-commit-code-state-exclusion, decision-reboot-kills-child]
---

# cycle_pre now auto-preserves code WIP across context-pressure reboots (#12142)

## Context

Before #12142, a large task that exceeded one context window could reboot
(exit-42 context pressure) mid-cycle, BEFORE `cycle_post` reached its commit
step. The uncommitted WIP then reached the next `cycle_pre`, where
`_enforce_branch` (checkout) orphaned it and `_do_pull` (git_ops stash/pop/drop)
stranded it → clean tree next cycle → the task restarted from zero → infinite
no-progress loop that looked like "rebooting for no reason."

## What changed

`cycle_pre.main()` now runs `_preserve_wip(role, working_state)` at the TOP,
before `_enforce_branch` and `_do_pull`. When working-state names an
**in-progress** task #N AND the tree is dirty with CODE changes, it commits the
code WIP to that task's feature branch via `git_ops commit-code` (state /
`.squidsquad` / `.claude` excluded — they keep the state→main route). It is a
no-op on a clean tree (the normal post-`cycle_post` case) and fail-open (any
error logs + returns None, tree left no worse).

## Implications for every role

- A context-pressure reboot mid-task now **resumes** instead of restarting —
  your committed-by-the-framework WIP is on the feature branch next cycle.
- This only protects CODE WIP for an **in-progress** task. If working-state is
  idle / not-in-progress (e.g. after a PM reset), or the dirty files are
  state/ephemeral only, it does NOT fire — so still keep working-state status
  accurate, and commit incrementally for anything you can't afford to re-derive.
- Reboot churn is no longer evidence of a stuck task by itself; check whether
  commits are actually advancing on the feature branch.

## Changelog

- 2026-06-14 — Created by skill-lead. From #12142 (PR #12270); the fix preserved
  its own committed WIP across a same-session PM-reset, validating the behavior.
