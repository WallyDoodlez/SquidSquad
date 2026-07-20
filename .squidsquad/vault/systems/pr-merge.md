---
type: system
tags: [git, pr, merge, workflow]
created: 2026-07-20
updated: 2026-07-20
status: active
owner: shared
---

# PR & Merge Flow

_Hub note (VAULT-ARCH 3.2): connective anchor for this subsystem. Keep it a
map, not an essay -- galaxy leaves carry the knowledge; this note carries
the links._

## What It Is

Branch-per-task + PR-only landing: git_ops.py owns task-begin/end, commit-code (state-guard), pr-create (closing-keyword neutralization), and the merge protocol (merge, never rebase; squash at ship).

## Key Files

`references/scripts/git_ops.py`, `references/sub-skills/common/pr-protocol.md`

## Knowledge Map

- Branch workflow: [[decision-branch-per-feature-workflow]]
- State-guard seams: [[learning-plan-in-pr-needs-state-guard-exemption]], [[learning-commit-code-state-exclusion]]
- Merge hazards: [[learning-git-merge-silently-drops-concurrent-large-edit-on-shared-markdown]], [[learning-config-merge-ours-drops-concurrent-changes]], [[learning-commit-before-merge-when-inheriting-dirty-behind-clone]]
- Verifier merge lane: [[learning-canonical-verifier-merge-is-harness-post-merge]], [[learning-confirm-merge-landed-before-pending-ship-transition]]
