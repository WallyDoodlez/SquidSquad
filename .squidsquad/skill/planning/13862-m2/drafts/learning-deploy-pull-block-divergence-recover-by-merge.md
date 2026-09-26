A `deploy-error` with `stage=pull` ("Diverging branches can't be fast-forwarded" or "local changes would be overwritten by merge") has **two distinct root causes** that need **different recoveries** — diagnose by the working tree before acting. Both recur on every deploy-signal until reconciled, and both block the recompose/deploy path fleet-wide.

- **DIVERGENCE variant** — working tree is CLEAN of modified tracked files, but local `main` is N-ahead/M-behind `origin/main`. Cause: the harness committed this clone's per-session doc/state work to local main, then a teammate (e.g. dm recompose) pushed to origin before this clone's push landed → legitimate non-overlapping divergence. The harness deploy-pull is FF-only and fatals. **Recovery: `git merge origin/main --no-edit` then `git push`.** Files are non-overlapping so the merge is clean (0 conflicts). Verify `git rev-list --left-right --count HEAD...origin/main` reads `0	0` after. NEVER rebase (see [[feedback_never_rebase_merge_instead]]); NEVER discard local commits (they are real harness-committed work). Systemic fix tracked at #13158 (give the harness deploy-pull a merge strategy, mirroring the #12526 launcher fix).

- **DIRTY-TREE variant** — working tree has modified tracked composed `CLAUDE.md`/`.linked.md` files, left by an agent-manual `compose.py deploy-all` run. **Root cause**: the still-live "Post-merge recompose" overlay tells agents to run `compose.py deploy-all` after a merge touching `references/`. Under the deploy-signal model the harness owns recompose, so the manual run only **dirties** the composed files (which another clone/DM also recomposes + pushes), creating a false merge conflict. Tracked at [[#13030]] (retire agent-manual deploy-all); the deploy-signal model going live OPENS that issue's gate.
  - **Recovery (verified, zero-loss)**:
    1. `git diff origin/main -- ".squidsquad/*/CLAUDE.md" ".squidsquad/*/CLAUDE.linked.md"` — if **empty**, your working-tree composed files are byte-identical to origin/main (origin already carries the authoritative recompose).
    2. `git checkout -- <the 8 composed files>` to discard the local regeneration. Composed files are generated artifacts → discarding identical-to-origin copies loses nothing and is NOT branch surgery.
    3. Confirm only non-overlapping work remains dirty (`git status --short`); the next harness pull then FFs cleanly. Leave your own uncommitted doc work in place if incoming commits don't touch those paths — it survives the pull and the harness commits it.
  - **Don't**: `git pull`/commit/push to "fully fix" it (harness owns git in event mode) — discarding the blocking artifacts is the minimal in-lane unblock.
  - Systemic fix: #13030 (retire agent-manual recompose).

**Shared boundary note**: a PM can only recover **its own** clone. Other clones showing `intent=deploying` for a long stretch while still working are likely stuck in the same block — flag the blast radius on the root-cause issue; do not operate in their clones.

## Changelog

- **2026-09-26** — migrated to vault v2 (#13862).
