---
type: learning
tags: [branch-workflow, mergeability, transient-state, diagnosis]
created: 2026-06-12
updated: 2026-06-13
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

Hand-resolving a non-conflict wastes cycles and (worse) can mislead QA into deferring a substantively-mergeable PR. The durable fix is to keep transient agent state OFF code branches — the `state_bus.py`/`migrate_state_branch.py` dedicated state-branch architecture exists for this but is not yet activated. Tracked in #11511.

**CORRECTION (iter-468, 2026-06-13): the "swap `merge=ours` → `merge=union`" stopgap does NOT work.** GitHub does not honor ANY user-defined `.gitattributes` merge driver for PR mergeability — not just custom drivers, but built-in `union` too. `merge=union` for PR-conflict resolution is an open GitHub feature request since 2021 with no implementation ([community discussion #9288](https://github.com/orgs/community/discussions/9288); GitHub support: "GitHub doesn't consider user-defined .gitattributes files"). libgit2/GitLab honor union; GitHub does not. So the entire existing `.gitattributes` merge block is a **local-merge-only** aid and a server-side no-op — adding/changing merge= entries will never fix the GitHub flap. The only real fixes are (a) keep transient files out of the PR diff (gitignore — already done for current-state/cycle-*.json/.backlog-cache; working-state.md can't be gitignored without breaking cross-agent visibility) and (b) guarantee working-state.md never lands on a feature branch (it flaps only when both branch and main change it; `cycle_post` already routes state→main, so leaks come from harness-down manual commits / branch races).

Until the durable fix lands: prove mergeability with merge-tree, tell QA to merge on content, don't nudge.

## Related

- [[gitattributes_for_transient_state]]
- [[learning-qa-branch-merge-workaround]]
- #11511 (durable fix), #11504 / #11394 (origin)

---

### Changelog

- 2026-06-12 — Created by skill (cycle 1636). merge-tree diagnostic for cosmetic CONFLICTING flag; filed #11511.
- 2026-06-12 — Corrected by skill (cycle 1640). Root cause is `merge=ours` (custom driver) not honored by GitHub server-side — not generic "staleness". Durable fix = activate state-branch (state_bus); stopgap = merge=union where safe. Posted to #11511.
- 2026-06-13 — Corrected by skill (iter-468). The merge=union stopgap is ALSO ineffective: GitHub honors NO user .gitattributes merge driver (incl. built-in union) for PR mergeability (community discussion #9288). `.gitattributes` merge block is local-merge-only. Real fixes = gitignore transient files / keep working-state off feature branches. Reposted on #11511.
