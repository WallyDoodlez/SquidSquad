---
type: learning
tags: [branch-workflow, mergeability, transient-state, diagnosis]
created: 2026-06-12
updated: 2026-06-12
owner: skill
status: active
confidence: high
source: observation
links: [learning-qa-branch-merge-workaround]
---

## Context

PR #11504 / #11394 repeatedly showed `mergeable: CONFLICTING / mergeStateStatus: DIRTY` on GitHub across cycles 1634–1636, prompting hand-resolution each time. Investigation showed there was **no real content conflict** at any point.

## Content

**Before hand-resolving a PR that GitHub flags CONFLICTING, verify with `git merge-tree`:**

```bash
git fetch origin --quiet
git merge-tree --write-tree origin/main origin/<branch> >/dev/null 2>&1; echo $?
git merge-tree --write-tree origin/<branch> origin/main >/dev/null 2>&1; echo $?
```

Exit 0 both directions = **zero real conflict**; GitHub's flag is cosmetic. Exit non-zero = real conflict to resolve.

When merge-tree is clean but GitHub says CONFLICTING, the cause is GitHub's server-side merge check tripping on **transient files that both branch and main edit on overlapping lines** (`.squidsquad/<role>/working-state.md`, `iterations/*`, `planning/*` logs) — local `ort` auto-resolves them, GitHub's check does not / lags. Because every agent commits transient state to `main` every cycle (cycle_post), base advances constantly and the flag re-flaps. Forcing a recompute (merge main into branch + push) clears it momentarily but it re-stales the next time base advances — **whack-a-mole; do not keep hand-nudging.**

## Rationale

Hand-resolving a non-conflict wastes cycles and (worse) can mislead QA into deferring a substantively-mergeable PR. The durable fix is to stop transient state from advancing base / conflicting — tracked in #11511 (gitignore iterations+planning logs and/or `.gitattributes merge=union` on working-state). Until then: prove mergeability with merge-tree, tell QA to merge on content, don't nudge.

## Related

- [[gitattributes_for_transient_state]]
- [[learning-qa-branch-merge-workaround]]
- #11511 (durable fix), #11504 / #11394 (origin)

---

### Changelog

- 2026-06-12 — Created by skill (cycle 1636). merge-tree diagnostic for cosmetic CONFLICTING flag; filed #11511.
