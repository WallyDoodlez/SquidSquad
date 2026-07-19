---
type: learning
tags: [worker, pr-flow, git-ops, process-gap]
created: 2026-07-19
updated: 2026-07-19
owner: skill
status: active
confidence: high
source: observation
links: []
---

## Context

`git_ops.py task-begin <role> <number>` checks out (or creates)
`squidsquad/task/<number>` and switches to it. It does **not** create a PR.
For PM-originated tasks, a PR already exists by the time worker picks it up
(Plan-in-PR — PM's commit 1 on the branch opens a draft PR). For a
self-filed bug/issue picked up directly via `task-begin` (no PM plan
commit), nothing opens a PR — `task-begin` + `commit-code` alone leave the
branch pushed but PR-less.

## Content

Shipped #13709/#13710/#13711 to pending-test with fully-correct code (11/11
regression tests, verifier's own spot-read confirmed correctness) but no PR
existed for either branch. Verifier rejected all three for the identical
reason: this install's PR Flow is `yes`, `git-commit.md` Step 5.3 requires a
PR before marking pending-test, and none of the three shipping comments
mentioned a PR number. Confirmed via `gh pr list --search "squidsquad/task/
<n>" --state all` returning empty for both branches. Fix was mechanical —
`git_ops.py pr-create <title> <body>` (while checked out on the branch) +
`git_ops.py pr-ready <pr-number>` — no code changes needed, both branches
were already correct.

**Rule going forward**: for any bug/issue picked up via `task-begin` (no
pre-existing PM plan-in-PR draft), run `git_ops.py pr-create` immediately
after the first `commit-code` on that branch — before marking pending-test,
not after a verifier rejection surfaces the gap. Check `gh pr list --search
"squidsquad/task/<n>"` before transitioning to pending-test if unsure
whether a PR already exists.

## Rationale

PR Flow is load-bearing beyond code review — DM/verifier's own ship
mechanics (auto-merge via the harness `/merge` endpoint) operate on PR
numbers, not raw branches. A PR-less "pending-test" branch is invisible to
that mechanism even when the code itself is perfect.

## Related

(none yet)

---

### Changelog

- 2026-07-19 — Created by skill after all three same-tick issues were rejected for the identical process gap.
