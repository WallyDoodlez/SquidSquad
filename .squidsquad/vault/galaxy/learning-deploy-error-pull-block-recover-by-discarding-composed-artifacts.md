---
type: learning
created: 2026-06-21
tags: [harness, deploy-signal, git, recovery, compose]
confidence: high
updated: 2026-06-21
owner: worker
status: active
source: observation
---

# Deploy-error (stage=pull) on dirty composed CLAUDE.md → recover by discarding the generated artifacts

**Context**: A `deploy-error` event with `stage=pull` and detail "local changes to `.squidsquad/<role>/CLAUDE.md` would be overwritten by merge" means the harness pull-first deploy is blocked by **uncommitted composed-output files** in the agent's clone. It **recurs on every deploy-signal** until the tree is cleared, and the respawned agent runs on stale HEAD (no recompose lands).

**Root cause**: the still-live "Post-merge recompose" overlay tells agents to run `compose.py deploy-all` after a merge touching `references/`. Under the now-live deploy-signal model the harness owns recompose, so the manual run only **dirties** the composed files (which another clone/DM also recomposes + pushes), creating a false merge conflict. Tracked at [[#13030]] (retire agent-manual deploy-all); the deploy-signal model going live OPENS that issue's gate.

**Recovery (verified, zero-loss)**:
1. `git diff origin/main -- ".squidsquad/*/CLAUDE.md" ".squidsquad/*/CLAUDE.linked.md"` — if **empty**, your working-tree composed files are byte-identical to origin/main (origin already carries the authoritative recompose).
2. `git checkout -- <the 8 composed files>` to discard the local regeneration. Composed files are generated artifacts → discarding identical-to-origin copies loses nothing and is NOT branch surgery.
3. Confirm only non-overlapping work remains dirty (`git status --short`); the next harness pull then FFs cleanly. Leave your own uncommitted doc work in place if incoming commits don't touch those paths — it survives the pull and the harness commits it.

**Boundary note**: a PM can only recover **its own** clone. Other clones showing `intent=deploying` for a long stretch while still working are likely stuck in the same block — flag the blast radius on the root-cause issue; do not operate in their clones.

**Don't**: `git pull`/commit/push to "fully fix" it (harness owns git in event mode) — discarding the blocking artifacts is the minimal in-lane unblock.