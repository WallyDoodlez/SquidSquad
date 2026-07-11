---
type: pattern
role: dm
created: 2026-06-27
tags: [delivery, merge-integrity, behind-clone, revert, recovery, worktree, ship-gate]
owner: dm-lead
status: active
confidence: high
source: incident
---

# Inspect the merge commit's FULL stat before shipping; recover a fleet-reverting merge with `git revert` in an isolated worktree

## The check (always, at delivery of a pending-ship item)
Before treating a merged PR as cleanly delivered, run `git show --stat --format='' <mergeCommit>` and confirm the file set matches the issue's declared scope. A PR squash-merged from a clone that is **far behind origin/main** (the 'merge origin/main first' step didn't take) records the stale tree as truth — its squash **reverts every file the branch lacks locally**, deleting/reverting committed work far outside the PR's scope.

**Red flags in the stat:** composed `.squidsquad/*/CLAUDE.md` touched by a non-template PR; `config.md` or `.claude/settings.json` deleted/modified by an unrelated feature; large deletion counts (e.g. 4000+ lines); QA-RESULTS / vault galaxy files deleted. Cross-check vs the merge's PARENT (`git show <parent>:<path>`) to PROVE the file existed before and the merge removed it — facts over assumption.

## The recovery (DM lane: merge-to-main + handle-failure + git-as-audit-trail)
`git revert <badMergeCommit>` via an **isolated worktree at origin/main** (PowerShell on Windows per [[learning-bash-cd-into-missing-worktree-runs-in-main-clone]]):
1. `git worktree add --detach <wt> origin/main`
2. `git -C <wt> revert --no-edit <badMergeCommit>` — non-destructive (new commit, no history rewrite), usually conflict-free.
3. Verify from facts: the reverted files are restored AND any legit commits that landed AFTER the bad merge are preserved (revert only inverts the one commit; files it didn't touch are untouched). Re-verify composed CLAUDE.md / config.md / settings.json / vault are back.
4. `git fetch` then merge origin/main into the worktree (plain `git merge` — NOT `git merge --no-rebase`, that flag is pull-only) to absorb commits that landed during recovery; push only when origin/main is an ancestor of HEAD (pull-first, never force).
5. Remove the worktree.

The revert also removes the legit feature the PR added → route that issue `pending-ship → in-progress` (handle-failure outcome c) for a clean re-land. Don't increment the ship counter (not delivered).

## Why this is DM's call, not PM's
A bad merge corrupting main is a delivery-integrity failure; PM does not touch branch management (human pref). The revert is reversible and restorative, so it does not need pre-confirmation as a 'hard-to-reverse' action — but file a SEV-1 incident with evidence and notify the operator, because it un-lands operator-requested work and signals a systemic gap.

## Root cause it exposes
This is the behind-clone merge class ([[learning-compose-engine-change-no-claudemd-recompose]] sibling; tracked #13263 / incident #13271). The durable prevention is **merge-side**: harness `/merge` should refuse a squash whose diff deletes files outside the PR's declared scope, or block merging a branch >N commits behind base. Note the irony: a more-robust deploy-pull (the #13212/#13215/#13211/#13261 cluster) makes clones MORE likely to pull a corrupted main, raising the stakes of the missing merge guard.

First seen: #13271 (PR #13269 / #12801 TUI reverted 194 files, ~155 commits; recovered to origin/main 8d41aa881), 2026-06-27.
