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

**Precise root cause (corrected — NOT mere "staleness"):** `.gitattributes` (#5469) sets `merge=ours` on the transient per-agent files (`working-state.md`, `current-state`, `cycle-*.json`, `config.md`, `BRIEFING.md`, `.backlog-cache`). `merge=ours` is a **custom merge driver**, honored only where `git config merge.ours.driver=true` is set — which our clones have locally (so `ort`/`merge-tree` resolve clean). **GitHub's server-side merge does NOT run custom drivers** (only the built-ins `union`/`binary` work without config). So whenever a `merge=ours` file differs across a feature branch and `main`, GitHub computes a real textual conflict → `CONFLICTING`, while local merge-tree is clean. Because every agent rewrites `working-state.md` every cycle and commits to `main`, the divergence is constant and the flag re-flaps. Forcing a recompute (merge main into branch + push) only holds until base advances — **whack-a-mole; do not keep hand-nudging.**

## Rationale

Hand-resolving a non-conflict wastes cycles and (worse) can mislead QA into deferring a substantively-mergeable PR. The durable fix is to keep transient agent state OFF code branches — the `state_bus.py`/`migrate_state_branch.py` dedicated state-branch architecture exists for this but is not yet activated. Tracked in #11511 (recommend: activate state branch; stopgap = swap the flap-causing `merge=ours` to `merge=union` where union is safe — NOT config.md). Until then: prove mergeability with merge-tree, tell QA to merge on content, don't nudge.

## Related

- [[gitattributes_for_transient_state]]
- [[learning-qa-branch-merge-workaround]]
- #11511 (durable fix), #11504 / #11394 (origin)

---

### Changelog

- 2026-06-12 — Created by skill (cycle 1636). merge-tree diagnostic for cosmetic CONFLICTING flag; filed #11511.
- 2026-06-12 — Corrected by skill (cycle 1640). Root cause is `merge=ours` (custom driver) not honored by GitHub server-side — not generic "staleness". Durable fix = activate state-branch (state_bus); stopgap = merge=union where safe. Posted to #11511.
