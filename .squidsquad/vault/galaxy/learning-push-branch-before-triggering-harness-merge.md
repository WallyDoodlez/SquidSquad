---
type: learning
tags: [qa, pr-merge, sequencing, comprehension-staleness]
created: 2026-07-20
updated: 2026-07-20
status: active
owner: verifier
confidence: high
source: observation
---

# Push a feature-branch commit before triggering the harness `/merge` — not after

## Context

Verifying #13858: authored `tests/comprehension/13858_spec.json` + its
`.staleness-baseline.json` entry, committed them on the feature branch
(`squidsquad/task/13858`) — a same-PR spec+file pair, correctly sequenced
per [[learning-cq-artifacts-commit-after-pr-merges-not-before]] (commit
in-branch, not to `main` early). Then posted the PR comment, ran
`gh pr ready`, and `POST /merge` to the harness — all without running
`git push` first. The commit existed only in my local clone.

## What Happened

The harness's squash-merge operates on the **remote** branch tip
(`origin/squidsquad/task/13858`), not my local one. `POST /merge` returned
`{"status":"accepted"}` and the `pr-merged` event confirmed `success: true`
— but the merge only picked up what was already pushed, which predated my
CQ-spec commit. I only discovered the gap afterward by comparing
`git hash-object` of the target file locally against
`git show origin/main:<path> | git hash-object --stdin` — the blob shas
matched (confirming the file *content* landed via the merge), but a direct
`git show origin/main:tests/comprehension/13858_spec.json` came back
"exists on disk, but not in main" — the spec file itself never reached
`main` at all. Pushing my local commit *after* the merge just recreated an
orphaned remote branch (GitHub offered to open a new PR against it, since
the old PR was already closed/merged) rather than retroactively including it.

## Generalizable Rule

**`git push` any local feature-branch commit before calling `POST /merge`
(or `gh pr ready`) — the harness merges what's on the remote, not what's on
disk.** If you catch the gap after the fact (a `pr-merged` event already
fired), do not try to re-push the now-orphaned branch expecting it to
retroactively join the merge — recover the file directly from the local
branch ref (`git show <branch>:<path>`) and land it as its own commit
directly on `main` instead, exactly as small state artifacts already do.
Verify recovery correctness with a blob-sha comparison
(`git hash-object <local>` vs `git show origin/main:<same-path-elsewhere> |
git hash-object --stdin`) rather than assuming content matches. Clean up the
accidentally-recreated remote branch afterward (`git push origin --delete
<branch>`) since it has no open PR and no further purpose.

## Related

- [[learning-cq-artifacts-commit-after-pr-merges-not-before]] — the
  adjacent axis: *when* (relative to merge state) a baseline entry is safe
  to commit at all. This note is about *push discipline* once you've
  already decided in-branch commit is correct — a prerequisite that axis
  silently assumes.
- [[pr-merge]] — the harness merge mechanism this gotcha lives inside.
