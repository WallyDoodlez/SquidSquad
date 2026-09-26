
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

## Distilled leaves (vault v2)

- [[learning-backtick-in-bash-doublequote-can-actually-execute]]
- [[learning-bundle-branch-reconciliation]]
- [[learning-closing-keyword-in-state-commit-autocloses-issue]]
- [[learning-commit-role-scoped-foreign-file-silent-drop]]
- [[learning-dm-local-merge-when-harness-down]]
- [[learning-gh-pr-edit-broken-use-gh-api-patch]]
- [[learning-git-ops-clean-tree-stash-pop-recovery]]
- [[learning-harness-merge-gate-caches-git-ops-module]]
- [[learning-l4-only-fix-skips-pr-flow]]
- [[learning-merge-driver-defeated-by-delete-not-modify]]
- [[learning-merge-mechanism-fix-cannot-protect-its-own-landing-commit]]
- [[learning-pr-conflicting-flag-can-be-cosmetic]]
- [[learning-pr-create-must-run-on-feature-branch-after-commit-code]]
- [[learning-push-branch-before-triggering-harness-merge]]
- [[learning-read-all-comments-before-merge-not-just-transition]]
- [[learning-ship-gate-squash-proof-window]]
- [[learning-sibling-pr-additive-test-conflict-keep-both]]
- [[learning-squash-drops-newest-commits-of-ahead-branch]]
- [[learning-stale-remote-tracking-ref-blocks-ship-gate]]
- [[learning-task-begin-does-not-auto-create-pr-for-bugs]]
- [[learning-test-pollution-real-clone-state]]
- [[learning-trivial-append-conflicts-still-route-to-worker]]
- [[learning-verify-combined-state-when-branch-behind-main-shares-files]]
- [[learning-verify-squash-diff-additions-only-behind-branch]]
- [[pattern-inspect-merge-stat-before-ship-revert-to-recover]]
- [[pattern-replay-fix-against-real-incident-not-just-mocks]]

## Changelog

- **2026-09-26** — migrated to vault v2 (#13862).
