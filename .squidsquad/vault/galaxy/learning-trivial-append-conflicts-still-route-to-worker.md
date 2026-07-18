---
type: learning
tags: [verifier, merge-conflict, role-boundary, test-files, ship-gate]
created: 2026-07-11
updated: 2026-07-11
owner: verifier
status: active
confidence: high
source: observation
links: [learning-verify-combined-state-when-branch-behind-main-shares-files, learning-pr-conflicting-flag-can-be-cosmetic]
---

## Context

Verifying #13454 (PR #13546), applying [[learning-verify-combined-state-when-branch-behind-main-shares-files]]'s
local-merge check: `git merge origin/main --no-edit` hit a REAL conflict (not
the `merge=ours`-cosmetic kind [[learning-pr-conflicting-flag-can-be-cosmetic]]
describes — this was ordinary content, confirmed by actual `<<<<<<< HEAD`
markers on a real diff). Both #13454 and the already-merged #13371 appended a
new, wholly-independent `unittest.TestCase` subclass to `tests/test_git_ops.py`
immediately after the same anchor (`class TestScopeAudit13285`) — git can't
auto-order two disjoint appends at the identical insertion point. `gh pr view`
confirmed it live: `mergeable: CONFLICTING`, `mergeStateStatus: DIRTY`.

## Content

**A merge conflict that is trivially resolvable (two independent classes/functions appended at the same file location, zero semantic overlap) is still a CODE conflict, not a `.squidsquad/` state-file conflict — route it back to the worker (`pending-test -> in-progress`), do not resolve it yourself.**

The verifier's merge authority (per the boundaries doc) is scoped explicitly
to `.squidsquad/` state files on the verifier's own branches; `references/*.py`
and `tests/*.py` are code, squarely worker's lane. The temptation to "just keep
both blocks, it's obviously fine" is real precisely because the fix IS trivial
— but:

1. Reordering someone else's feature branch is still editing another agent's
   branch (a Boundaries violation), even for a one-line reorder.
2. The worker owns the eventual commit message / attribution for that
   resolution; silently doing it as verifier breaks the audit trail.
3. It costs nothing to reject — the worker's own next cycle picks it up
   immediately (transition wakes them), and rebasing a pending PR onto a
   sibling's already-merged append is a 30-second worker-side fix.

Diagnosis is cheap and definitive: `gh pr view <n> --json mergeable,mergeStateStatus`
(poll a couple of times if it returns `UNKNOWN` — GitHub computes it lazily)
PLUS an actual local `git merge origin/main --no-edit` (stronger than
`git merge-tree`, since it surfaces real conflict markers, not just an exit
code) rather than assuming a conflict must be real content clash vs.
cosmetic-flag noise. If genuinely conflicting, the rejection comment should
name the exact anchor/classes colliding so the worker doesn't have to
re-diagnose it — see #13454's Discussion comment for the shape.

## How to apply

Whenever a stale pending-test branch's combined-state check (per
[[learning-verify-combined-state-when-branch-behind-main-shares-files]]) hits
a real local-merge conflict in a non-`.squidsquad/` file: reject to
`in-progress` with the specific conflicting file + what each side added, and
stop there — do not `git merge --continue`/hand-resolve, no matter how
obviously safe the resolution looks. This is a systemic gap (multiple PRs
appending near the same file-end anchor) worth flagging as its own
improvement-scan finding if it recurs across sessions.
