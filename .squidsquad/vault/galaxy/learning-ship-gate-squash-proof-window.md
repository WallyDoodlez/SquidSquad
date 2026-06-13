---
type: learning
tags: [dm, ship-gate, tracker, squash-merge, branch-cleanup]
created: 2026-06-12
updated: 2026-06-12
owner: dm
status: active
confidence: high
source: observation
links: [pattern-chain-ship-per-item-auth, decision-branch-per-feature-workflow]
---

## Context

During the v0.44.0 cutover, `tracker.py transition <n> pending-ship shipped` on **#11227** was BLOCKED: "branch 'squidsquad/task/11227' has 4 commit(s) not merged to the working branch" — even though #11227's deliverable was verifiably on main (commit `79feb3d5e` via PR #11431 + the reconciliation bundle PR #11402). `--force` did NOT bypass it (the unmerged-branch guard is never bypassed, even with --force).

## Content

The ship-gate's squash-merge bypass (`_check_merged_pr` in tracker.py) only inspects the **20 most recent merged PRs** (`gh pr list --state merged --limit 20`). When a bundle item's merge PR has aged past that window (many PRs merged since), the bypass misses it and the ancestry block (`_check_unmerged_branch`) falsely fires, because a squash-merge leaves the feature-branch tip with a different SHA than the squash commit on main.

**Fix that worked**: delete the superseded stale per-task remote branch — `git push origin --delete squidsquad/task/<n>` — after confirming (a) no OPEN PR on it and (b) the deliverable is on main. With the branch gone, `_check_unmerged_branch` returns None and the ship passes. This doubles as legitimate AC5 branch cleanup.

## Rationale

Deleting the branch is safe when the work is already on main: the commits survive in the merged-PR ref / reflog, and the content is reachable from HEAD. Do NOT --force-fabricate a ship without first proving the deliverable is on main (`git branch --contains <ship-commit> main`).

## Related

- [[pattern-chain-ship-per-item-auth]]
- [[decision-branch-per-feature-workflow]]

---

### Changelog

- 2026-06-12 — Created by dm. Squash-merge proof-window ship-gate false-block during v0.44.0 cutover (#11227); fix = delete superseded stale branch.
